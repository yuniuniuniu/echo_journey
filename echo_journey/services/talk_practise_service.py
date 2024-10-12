import logging
from echo_journey.api.downward_protocol_handler import DownwardProtocolHandler
from echo_journey.api.proto.upward_pb2 import AudioMessage, StudentMessage
from echo_journey.audio.speech_to_text.asr import ASR
from echo_journey.common.utils import parse_pinyin
from enum import Enum

from echo_journey.services.bots.correct_bot import CorrectBot
from echo_journey.services.bots.practise_progress import PractiseProgress
from echo_journey.services.bots.scene_generate_bot import SceneGenerateBot
from echo_journey.services.bots.talk_practise_bot import TalkPractiseBot

logger = logging.getLogger(__name__)

class ClassStatus(Enum):
    NOTSTART = 1
    SCENE_GEN = 2
    ING = 3

class TalkPractiseService:
    def __init__(self, session_id, ws_msg_handler):
        self.session_id = session_id
        self.ws_msg_handler: DownwardProtocolHandler = ws_msg_handler
        self.scene_generate_bot = SceneGenerateBot()
        self.correct_bot = CorrectBot()
        self.status = ClassStatus.NOTSTART
        self.asr: ASR = ASR()
        self.practise_progress = PractiseProgress()
        self.talk_practise_bot = TalkPractiseBot(practise_progress=self.practise_progress, ws_msg_handler=self.ws_msg_handler)
        
    async def initialize(self):
        await self.talk_practise_bot.send_treating_msg()
        self.status = ClassStatus.SCENE_GEN

    async def _on_message_at_scene_gen(self, student_text):
        scene_info = await self.scene_generate_bot.generate_scene_by(student_text)
        if scene_info.get("当前场景", None):
            self.status = ClassStatus.ING
            self.practise_progress.init_by_content(scene_info)
            await self.talk_practise_bot.send_practise_msg("刚开始练习", "无")
        else:
            user_msg = "学生当前说话内容未包含场景，让他说个练习的场景"
            self.talk_practise_bot.send_chat_msg(user_msg)
            
    async def _on_message_at_practise(self, student_text):
        teacher_info = self.talk_practise_bot.generate_practise_reply(student_status="练习中", student_text=student_text)
        if teacher_info.get("skip", False):
            skip_practise = self.practise_progress.get_current_practise()
            expected_practise = self.practise_progress.get_next_practise()
            self.talk_practise_bot.send_practise_msg(student_status=f"学生跳过练习{skip_practise},现在开始练习{expected_practise}", student_text="无")
        else:
            await self.ws_msg_handler.send_tutor_message(text=teacher_info["teacher"])
            
    async def process_student_message(self, student_message: StudentMessage):
        student_text = student_message.text
        if self.status == ClassStatus.SCENE_GEN:
            await self._on_message_at_scene_gen(student_text)
        elif self.status == ClassStatus.ING:
            await self._on_message_at_practise(student_text)
        else:
            raise ValueError(f"Unknown status: {self.status}")

    async def _on_asr_reg_error(self):
        await self.ws_msg_handler.send_tutor_message(text="对不起，我没有听清楚，请再说一遍")
    
    async def _on_audio_at_scene_gen(self, audio_message: AudioMessage, platform):
        asr_result = self.asr.transcribe(audio_message.audio_data, platform)
        if not asr_result:
            await self._on_asr_reg_error()
        else:
            await self._on_message_at_scene_gen(asr_result) 
            
    async def _on_audio_at_practise(self, audio_message: AudioMessage, platform):
        asr_result = self.asr.transcribe(audio_message.audio_data, platform)
        if not asr_result:
            await self._on_asr_reg_error()
            return
        try:
            messages = parse_pinyin(asr_result)
        except Exception as e:
            logger.exception(f"parse pinyin error: {e} with asr_result: {asr_result}")
            await self._on_asr_reg_error()
        expected_practise = self.practise_progress.get_current_practise()
        expected_messages = parse_pinyin(expected_practise)
        suggestions, score = await self.correct_bot.get_correct_result(expected_messages, messages)
        if score <= 80:
            await self.ws_msg_handler.send_correct_message(suggestions=suggestions, expected_messages=expected_messages, msgs=messages)
            await self.ws_msg_handler.send_tutor_message(text="来，我们再试一次")
        else:
            passed_practise = self.practise_progress.get_current_practise()
            expected_practise = self.practise_progress.get_next_practise()
            if expected_practise:
                await self.talk_practise_bot.send_practise_msg(student_status=f"学生通过练习{passed_practise},现在开始练习{expected_practise}", student_text="无")
            else:
                await self.talk_practise_bot.send_end_class_msg()

    async def process_audio_message(self, audio_message: AudioMessage, platform):
        if self.status == ClassStatus.SCENE_GEN:
            await self._on_audio_at_scene_gen(audio_message, platform)
        elif self.status == ClassStatus.ING:
            await self._on_audio_at_practise(audio_message, platform)
        else:
            raise ValueError(f"Unknown status: {self.status}")