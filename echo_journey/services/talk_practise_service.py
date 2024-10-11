import logging
import yaml
from echo_journey.api.downward_protocol_handler import DownwardProtocolHandler
from echo_journey.api.proto.upward_pb2 import AudioMessage, StudentMessage
from echo_journey.audio.speech_to_text.kanyun import Kanyun
from echo_journey.common.utils import parse_pinyin
from echo_journey.data.assistant_content import AssistantContent
from echo_journey.data.assistant_meta import AssistantMeta
from echo_journey.data.whole_context import WholeContext
from enum import Enum

logger = logging.getLogger(__name__)

class ClassStatus(Enum):
    NOTSTART = 1
    SCENE_GEN = 2
    ING = 3
 
class PractiseStatus(Enum):
    NOTSTART = 1
    WORD = 2
    SENTENCE = 3

class PractiseProgress:
    def __init__(self, content: dict):
        self.current_sentence_round = 0
        self.current_word_round = 0
        self.scene = content.get("当前场景", None)
        logger.info(f"current scene: {self.scene}")
        self.sentences_list = [content.get("短句1", []), content.get("短句2", []), content.get("短句3", [])]
        logger.info(f"sentences list: {self.sentences_list}")
        if self.scene:
            self.current_status = PractiseStatus.WORD
            self.current_practise = self.sentences_list[self.current_sentence_round][self.current_word_round]
        else:
            self.current_status = PractiseStatus.NOTSTART
            self.current_practise = None
            
    def get_next_practise(self):
        if self.current_status == PractiseStatus.SENTENCE:
            self.current_sentence_round += 1
            self.current_word_round = 0
        elif self.current_status == PractiseStatus.WORD:
            if self.current_word_round < len(self.sentences_list[self.current_sentence_round]) - 1:
                self.current_word_round += 1
            else:
                self.current_status = PractiseStatus.SENTENCE
                self.current_practise = ",".join(self.sentences_list[self.current_sentence_round])
                return self.current_practise

        if not self.is_end():
            self.current_practise = self.sentences_list[self.current_sentence_round][self.current_word_round]
        else:
            self.current_practise = None
        return self.current_practise
    
    def get_current_practise(self):
        return self.current_practise
    
    def get_history_student_practise(self):
        result = []
        sentences =  self.sentences_list[:self.current_sentence_round]
        for sentence in sentences:
            result.extend(sentence)
        result.extend(self.sentences_list[self.current_sentence_round][:self.current_word_round])
        return ",".join(result)
    
    def get_cur_practise_word(self):
        return self.sentences_list[self.current_sentence_round][self.current_word_round]
    
    def get_cur_practise_sentence(self):
        return ",".join(self.sentences_list[self.current_sentence_round])
            
    def is_end(self):
        return self.current_sentence_round >= len(self.sentences_list)

class TalkPractiseService:
    def __init__(self, session_id, ws_msg_handler):
        self.session_id = session_id
        self.ws_msg_handler: DownwardProtocolHandler = ws_msg_handler
        self.main_chat_context = None
        self.scene_generator = None
        self.correct_context = None
        self.status = ClassStatus.NOTSTART
        self.asr: Kanyun = Kanyun.get_instance()
        self.practise_progress = None
        
    async def initialize(self):
        self.main_chat_context = self.generate_context_by_yaml("echo_journey/services/meta/talk_practise.yaml", "talk_assistant")
        self.scene_generator = self.generate_context_by_yaml("echo_journey/services/meta/scene_generation.yaml", "scene_assistant")
        self.correct_context = self.generate_context_by_yaml("echo_journey/services/meta/correct.yaml", "correct_context")
        treating_message = "那你今天有什么想聊的话题呢？可以跟我说说，如果没什么的想法的话我就给你推荐几个日常的呀"
        self.main_chat_context.add_assistant_msg_to_cur({"role": "assistant", "content": treating_message})
        await self.ws_msg_handler.send_tutor_message(text=treating_message)
        self.status = ClassStatus.SCENE_GEN
        
    def generate_context_by_yaml(self, path, name):
        content = yaml.safe_load(open(path, "r"))
        assistant = AssistantMeta(assistant_name=name, content=AssistantContent(content=content))
        return WholeContext.build_from(assistant_meta=assistant)
    
    async def process_message_at_scene_gen(self, student_text):
        self.scene_generator.add_user_msg_to_cur({"role": "user", "content": self.scene_generator.cur_visible_assistant.content.user_prompt_prefix + student_text})
        scene_info = await self.scene_generator.execute()
        if scene_info.get("当前场景", None):
            self.status = ClassStatus.ING
            self.practise_progress = PractiseProgress(scene_info)
            expected_practise = self.practise_progress.get_current_practise()
            format_dict = {}
            format_dict["PLAN"] = self.practise_progress.get_cur_practise_sentence()
            format_dict["HISTORY_PRACTISE"] = self.practise_progress.get_history_student_practise()
            format_dict["CURRENT_PRACTISE"] = self.practise_progress.get_current_practise()
            format_dict["STUDENT_STATUS"] = "刚开始练习"
            format_dict["STUDENT"] = "无"
            user_msg = self.main_chat_context.cur_visible_assistant.content.user_prompt_prefix.format(**format_dict)
            self.main_chat_context.add_user_msg_to_cur({"role": "user", "content": user_msg})
            teacher_info = await self.main_chat_context.execute()
            expected_messages = parse_pinyin(expected_practise)
            await self.ws_msg_handler.send_tutor_message(text=teacher_info["teacher"], expected_messages=expected_messages)
        else:
            user_msg = "学生当前说话内容未包含场景，让他说个练习的场景"
            self.main_chat_context.add_user_msg_to_cur({"role": "user", "content": user_msg})
            teacher_info = await self.main_chat_context.execute()
            await self.ws_msg_handler.send_tutor_message(text=teacher_info["teacher"])
            
    async def process_student_message(self, student_message: StudentMessage):
        student_text = student_message.text
        if self.status == ClassStatus.SCENE_GEN:
            await self.process_message_at_scene_gen(student_text)
        elif self.status == ClassStatus.ING:
            format_dict = {}
            format_dict["PLAN"] = self.practise_progress.get_cur_practise_sentence()
            format_dict["HISTORY_PRACTISE"] = self.practise_progress.get_history_student_practise()
            format_dict["CURRENT_PRACTISE"] = self.practise_progress.get_current_practise()
            format_dict["STUDENT_STATUS"] = "练习中"
            format_dict["STUDENT"] = student_text
            user_msg = self.main_chat_context.cur_visible_assistant.content.user_prompt_prefix.format(**format_dict)
            self.main_chat_context.add_user_msg_to_cur({"role": "user", "content": user_msg})
            teacher_info = await self.main_chat_context.execute()
            if teacher_info.get("skip", False):
                skip_practise = self.practise_progress.get_current_practise()
                self.practise_progress.get_next_practise()
                expected_practise = self.practise_progress.get_current_practise()
                format_dict = {}
                format_dict["PLAN"] = self.practise_progress.get_cur_practise_sentence()
                format_dict["HISTORY_PRACTISE"] = self.practise_progress.get_history_student_practise()
                format_dict["CURRENT_PRACTISE"] = self.practise_progress.get_current_practise()
                format_dict["STUDENT_STATUS"] = f"学生跳过练习{skip_practise},现在开始练习{expected_practise}"
                format_dict["STUDENT"] = "无"
                user_msg = self.main_chat_context.cur_visible_assistant.content.user_prompt_prefix.format(**format_dict)
                self.main_chat_context.add_user_msg_to_cur({"role": "user", "content": user_msg})
                teacher_info = await self.main_chat_context.execute()
                expected_messages = parse_pinyin(expected_practise)
                await self.ws_msg_handler.send_tutor_message(text=teacher_info["teacher"], expected_messages=expected_messages)
            else:
                await self.ws_msg_handler.send_tutor_message(text=teacher_info["teacher"])
        else:
            raise ValueError(f"Unknown status: {self.status}")
        
    def format_correct_context_input(self, expected_messages, messages):
        format_dict = {}
        expected_sentence = ""
        for expected_message in expected_messages:
            expected_sentence += expected_message.word
            expected_sentence += expected_message.initial_consonant
            expected_sentence += expected_message.vowels
            expected_sentence += str(expected_message.tone)
            
        sentence = ""
        for message in messages:
            sentence += message.word
            sentence += message.initial_consonant
            sentence += message.vowels
            sentence += str(message.tone)
        format_dict["expected_sentence"] = expected_sentence
        format_dict["sentence"] = sentence
        return format_dict

    async def process_audio_message(self, audio_message: AudioMessage, platform):
        if self.status == ClassStatus.SCENE_GEN:
            asr_result = self.asr.transcribe(audio_message.audio_data, platform)
            await self.process_message_at_scene_gen(asr_result) 
        elif self.status == ClassStatus.ING:
            expected_messages = parse_pinyin(self.practise_progress.get_current_practise())  
            asr_result = self.asr.transcribe(audio_message.audio_data, platform)
            try:
                messages = parse_pinyin(asr_result)
            except Exception as e:
                logger.exception(f"parse pinyin error: {e} with asr_result: {asr_result}")
                await self.ws_msg_handler.send_tutor_message(text="对不起，我没有听清楚，请再说一遍")
                return
            format_dict = self.format_correct_context_input(expected_messages, messages)
            user_msg = self.correct_context.cur_visible_assistant.content.user_prompt_prefix.format(**format_dict)
            self.correct_context.add_user_msg_to_cur({"role": "user", "content": user_msg})
            result = await self.correct_context.execute()
            suggestion_list = result["suggestion_list"]
            suggestions = ""
            try:
                for suggestion in suggestion_list:
                    if not suggestion or suggestion == "null":
                        continue
                    else:
                        suggestions += suggestion
            except Exception as e:
                logger.exception(f"parse suggestion error: {e} with suggestion_list: {suggestion_list}")
                suggestions = "对不起，我没有听清楚，请再说一遍"
            score = int(result["score"])
            if score <= 80:
                await self.ws_msg_handler.send_correct_message(suggestions=suggestions, expected_messages=expected_messages, msgs=messages)
                await self.ws_msg_handler.send_tutor_message(text="来，我们再试一次")
            else:
                passed_practise = self.practise_progress.get_current_practise()
                self.practise_progress.get_next_practise()
                expected_practise = self.practise_progress.get_current_practise()
                format_dict = {}

                if expected_practise:
                    format_dict["PLAN"] = self.practise_progress.get_cur_practise_sentence()
                    format_dict["HISTORY_PRACTISE"] = self.practise_progress.get_history_student_practise()
                    format_dict["CURRENT_PRACTISE"] = self.practise_progress.get_current_practise()
                    format_dict["STUDENT_STATUS"] = f"学生通过练习{passed_practise},现在开始练习{expected_practise}"
                    format_dict["STUDENT"] = "无"
                    user_msg = self.main_chat_context.cur_visible_assistant.content.user_prompt_prefix.format(**format_dict)
                    self.main_chat_context.add_user_msg_to_cur({"role": "user", "content": user_msg})
                    teacher_info = await self.main_chat_context.execute()
                    expected_messages = parse_pinyin(expected_practise)
                    await self.ws_msg_handler.send_tutor_message(text=teacher_info["teacher"], expected_messages=expected_messages)
                else:
                    self.main_chat_context.add_user_msg_to_cur({"role": "user", "content": "这个场景的练习结束"})
                    teacher_info = await self.main_chat_context.execute()
                    expected_messages = parse_pinyin(expected_practise)
                    await self.ws_msg_handler.send_tutor_message(text=teacher_info["teacher"])
        else:
            raise ValueError(f"Unknown status: {self.status}")