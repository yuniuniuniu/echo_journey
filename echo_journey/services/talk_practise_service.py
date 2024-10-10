import yaml
from echo_journey.api.downward_protocol_handler import DownwardProtocolHandler
from echo_journey.api.proto.upward_pb2 import AudioMessage, StudentMessage
from echo_journey.audio.speech_to_text.kanyun import Kanyun
from echo_journey.common.utils import parse_pinyin
from echo_journey.data.assistant_content import AssistantContent
from echo_journey.data.assistant_meta import AssistantMeta
from echo_journey.data.whole_context import WholeContext
from enum import Enum

class ClassStatus(Enum):
    NOTSTART = 1
    SCENE_GEN = 2
    ING = 3
 
class PractiseProgress:
    # 需要修改生成next的逻辑
    def __init__(self, content: dict):
        self.current_sentence_round = 0
        self.current_word_round = 0
        self.scene = content.get("当前场景", None)
        self.sentences_list = [content.get("短句1", []), content.get("短句2", []), content.get("短句3", [])]
        if self.scene:
            self.current_practise = self.sentences_list[self.current_sentence_round][self.current_word_round]
            
    def get_next_practise(self):
        if self.current_word_round < len(self.sentences_list[self.current_sentence_round]) - 1:
            self.current_word_round += 1
        else:
            self.current_sentence_round += 1
            self.current_word_round = 0
        self.current_practise = self.sentences_list[self.current_sentence_round][self.current_word_round]
        return self.current_practise
    
    def get_current_practise(self):
        return self.current_practise
    
    def get_cur_practise_word(self):
        return self.sentences_list[self.current_sentence_round][self.current_word_round]
    
    def get_cur_practise_sentence(self):
        return self.sentences_list[self.current_sentence]
    
    def is_end_of_sentence(self):
        return self.current_word_round >= len(self.sentences_list[self.current_sentence_round])
            
    def is_end(self):
        return self.current_sentence_round >= len(self.sentences_list)

class TalkPractiseService:
    def __init__(self, session_id, ws_msg_handler):
        self.session_id = session_id
        self.ws_msg_handler: DownwardProtocolHandler = ws_msg_handler
        self.main_chat_context = None
        self.scene_generator = None
        self.correct_assistant = None
        self.status = ClassStatus.NOTSTART
        self.asr: Kanyun = Kanyun.get_instance()
        self.practise_progress = None
        
    async def initialize(self):
        self.main_chat_context = self.generate_context_by_yaml("echo_journey/services/meta/talk_practise.yaml", "talk_assistant")
        self.scene_generator = self.generate_context_by_yaml("echo_journey/services/meta/scene_generation.yaml", "scene_assistant")
        self.correct_assistant = self.generate_context_by_yaml("echo_journey/services/meta/correct.yaml", "correct_assistant")
        treating_message = "那你今天有什么想聊的话题呢？可以跟我说说，如果没什么的想法的话我就给你推荐几个日常的"
        self.main_chat_context.add_assistant_msg_to_cur({"role": "assistant", "content": treating_message})
        await self.ws_msg_handler.send_tutor_message(text=treating_message)
        self.status = ClassStatus.SCENE_GEN
        
    def generate_context_by_yaml(self, path, name):
        content = yaml.safe_load(open(path, "r"))
        assistant = AssistantMeta(assistant_name=name, content=AssistantContent(content=content))
        return WholeContext.build_from(assistant_meta=assistant)
    
    async def process_student_message(self, student_message: StudentMessage):
        student_text = student_message.text
        if self.status == ClassStatus.SCENE_GEN:
            self.scene_generator.add_user_msg_to_cur({"role": "user", "content": student_text})
            scene_info = await self.scene_generator.execute()
            if scene_info.get("当前场景", None):
                self.status = ClassStatus.ING
                self.practise_progress = PractiseProgress(scene_info)
                student_text = self.practise_progress.get_current_practise()
            self.main_chat_context.add_user_msg_to_cur({"role": "user", "content": student_text})
            teacher_info = await self.main_chat_context.execute()
            await self.ws_msg_handler.send_tutor_message(text=teacher_info["teacher"])
        elif self.status == ClassStatus.ING:
            self.main_chat_context.add_user_msg_to_cur({"role": "user", "content": student_text})
            teacher_info = await self.main_chat_context.execute()
            if teacher_info.get("skip", False):
                self.practise_progress.get_next_practise()
                self.main_chat_context.add_assistant_msg_to_cur({"role": "user", "content": self.practise_progress.get_current_practise()})
                teacher_info = await self.main_chat_context.execute()
            await self.ws_msg_handler.send_tutor_message(text=teacher_info["teacher"])
        else:
            raise ValueError(f"Unknown status: {self.status}")
        
    def format_correct_assistant_input(self, expected_messages, messages):
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
            expected_messages = parse_pinyin(audio_message.expected_sentence)  
            asr_result = self.asr.transcribe(audio_message.audio_data, platform)
            messages = parse_pinyin(asr_result)
            format_dict = self.format_correct_assistant_input(expected_messages, messages)
            user_msg = self.correct_assistant.content.get("user_prompt_prefix", "").format(**format_dict)
            self.correct_assistant.add_user_msg_to_cur({"role": "user", "content": user_msg})
            result = await self.correct_assistant.execute()
            suggestions = result["suggestion_list"]
            suggestions = ""
            for suggestion in suggestions:
                if not suggestion or suggestion == "null":
                    continue
                else:
                    suggestions += suggestion
            await self.ws_msg_handler.send_correct_message(suggestions=suggestions, expected_messages=expected_messages, msgs=messages)
        elif self.status == ClassStatus.ING:
            pass
        else:
            raise ValueError(f"Unknown status: {self.status}")