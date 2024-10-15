import copy
import json
import logging
from echo_journey.api.downward_protocol_handler import DownwardProtocolHandler
from echo_journey.api.proto.downward_pb2 import WordCorrectMessage
from echo_journey.api.proto.upward_pb2 import AudioMessage, StudentMessage
from echo_journey.audio.speech_to_text.asr import ASR
from echo_journey.common.utils import parse_pinyin
from enum import Enum

from echo_journey.data.learn_situation import LearnSituation
from echo_journey.services.bots.correct_bot import CorrectBot
from echo_journey.data.practise_progress import PractiseProgress
from echo_journey.services.bots.scene_generate_bot import SceneGenerateBot
from echo_journey.services.bots.talk_practise_bot import TalkPractiseBot

logger = logging.getLogger(__name__)

class ClassStatus(Enum):
    NOTSTART = 1
    SCENE_GEN = 2
    ING = 3

class TalkPractiseService:
    def __init__(self, ws_msg_handler):
        self.ws_msg_handler: DownwardProtocolHandler = ws_msg_handler
        self.learn_situation = LearnSituation()
        self.scene_generate_bot = SceneGenerateBot()
        self.status = ClassStatus.NOTSTART
        self.asr: ASR = ASR()
        self.practise_progress = PractiseProgress()
        self.correct_bot = CorrectBot(learn_situation=self.learn_situation, practise_progress=self.practise_progress)
        self.talk_practise_bot = TalkPractiseBot(practise_progress=self.practise_progress, ws_msg_handler=self.ws_msg_handler)
        
    async def initialize(self):
        await self.talk_practise_bot.send_treating_msg()
        self.status = ClassStatus.SCENE_GEN
    
    def on_ws_disconnect(self):
        self.correct_bot.learn_situation.save()

    async def _on_message_at_scene_gen(self, student_text, platform):
        logger.info(f"student_text: {student_text}")
        last_teacher_msg = json.loads(self.talk_practise_bot.context.get_last_msg_of("assistant"))["teacher"]
        scene_info = await self.scene_generate_bot.generate_scene_by(last_teacher_msg, student_text)
        logger.info(f"scene_info: {scene_info}")
        if scene_info.get("当前场景", None):
            self.status = ClassStatus.ING
            self.practise_progress.init_by_content(scene_info)
            await self.talk_practise_bot.send_practise_msg("刚开始练习", "无", platform=platform)
        else:
            await self.talk_practise_bot.send_practise_msg("学生当前说话内容未包含场景", student_text, platform=platform)
                        
    async def _on_message_at_practise(self, student_text, platform):
        teacher_info = await self.talk_practise_bot.generate_practise_reply(student_status="练习中", student_text=student_text)
        if teacher_info.get("change_scene", False):
            self.status = ClassStatus.SCENE_GEN
            self.practise_progress.reset()
            await self.talk_practise_bot.send_practise_msg(student_status="学生请求更换场景", student_text=student_text, platform=platform)
            return 

        if teacher_info.get("skip", False):
            skip_practise = self.practise_progress.get_current_practise()
            expected_practise = self.practise_progress.get_next_practise()
            if expected_practise:
                await self.talk_practise_bot.send_practise_msg(student_status=f"学生跳过练习{skip_practise},现在开始练习{expected_practise}", student_text="无", platform=platform)
            else:
                await self.talk_practise_bot.send_end_class_msg()
                self.status = ClassStatus.SCENE_GEN
                self.practise_progress.reset()
        else:
            await self.ws_msg_handler.send_tutor_message(text=teacher_info["teacher"])
            
    async def process_student_message(self, student_message: StudentMessage, platfoem):
        student_text = student_message.text
        if self.status == ClassStatus.SCENE_GEN:
            await self._on_message_at_scene_gen(student_text, platform=platfoem)
        elif self.status == ClassStatus.ING:
            await self._on_message_at_practise(student_text, platform=platfoem)
        else:
            raise ValueError(f"Unknown status: {self.status}")

    async def _on_asr_reg_error(self):
        await self.ws_msg_handler.send_tutor_message(text="对不起，我没有听清楚，请再说一遍")
    
    async def _on_audio_at_scene_gen(self, audio_message: AudioMessage, platform):
        asr_result, _ = await self.asr.transcribe(audio_message.audio_data, platform)
        if not asr_result:
            await self._on_asr_reg_error()
        else:
            await self._on_message_at_scene_gen(asr_result, platform) 
            
    def replace_pinyin_if_same(self, messages: list[WordCorrectMessage], expected_messages: list[WordCorrectMessage]):
        if len(messages) != len(expected_messages):
            return messages, expected_messages
        else:
            for i in range(len(messages)):
                if messages[i].pinyin == expected_messages[i].pinyin:
                    messages[i] = copy.deepcopy(expected_messages[i])
            return messages, expected_messages
            
    async def _on_audio_at_practise(self, audio_message: AudioMessage, platform):
        asr_result, pron_result = await self.asr.transcribe(audio_message.audio_data, platform, expected_text=self.practise_progress.get_current_practise())
        logger.info(f"asr_result: {asr_result}, pron_result: {pron_result}")
        if not asr_result:
            await self._on_asr_reg_error()
            return
        try:
            messages = parse_pinyin(asr_result)
        except Exception as e:
            logger.exception(f"parse pinyin error: {e} with asr_result: {asr_result}")
            await self._on_asr_reg_error()
            return
        expected_practise = self.practise_progress.get_current_practise()
        expected_messages = parse_pinyin(expected_practise)
        messages, expected_messages = self.replace_pinyin_if_same(messages, expected_messages)
        suggestions, score, change_scene, name_2_mp4_url = await self.correct_bot.get_correct_result(expected_messages, messages)
        if change_scene:
            self.status = ClassStatus.SCENE_GEN
            self.practise_progress.reset()
            await self.talk_practise_bot.send_practise_msg(student_status="学生请求更换场景", student_text=asr_result, platform=platform)
            return
        if score <= self.correct_bot.success_score:
            await self.ws_msg_handler.send_correct_message(suggestions=suggestions, expected_messages=expected_messages, msgs=messages, pron=pron_result, name_2_mp4_url=name_2_mp4_url)
            await self.ws_msg_handler.send_tutor_message(text="来，我们再试一次")
            self.talk_practise_bot.add_suggestion_to_context(suggestions)
        else:
            passed_practise = self.practise_progress.get_current_practise()
            expected_practise = self.practise_progress.get_next_practise()
            if expected_practise:
                await self.talk_practise_bot.send_practise_msg(student_status=f"学生通过练习{passed_practise},现在开始练习{expected_practise}", student_text="无", platform=platform)
            else:
                await self.talk_practise_bot.send_end_class_msg()
                self.status = ClassStatus.SCENE_GEN
                self.practise_progress.reset()

    async def process_audio_message(self, audio_message: AudioMessage, platform):
        if self.status == ClassStatus.SCENE_GEN:
            await self._on_audio_at_scene_gen(audio_message, platform)
        elif self.status == ClassStatus.ING:
            await self._on_audio_at_practise(audio_message, platform)
        else:
            raise ValueError(f"Unknown status: {self.status}")