import copy
import json
import logging
from echo_journey.api.downward_protocol_handler import DownwardProtocolHandler
from echo_journey.api.proto.downward_pb2 import WordCorrectMessage
from echo_journey.api.proto.upward_pb2 import AudioMessage, StudentMessage
from echo_journey.audio.speech_to_text.asr import ASR
from echo_journey.common.utils import parse_pinyin

from echo_journey.services.bots.exercise_bot import ExerciseBot
from echo_journey.services.bots.exercise_correct_bot import CorrectBot
from echo_journey.services.bots.history_learn_situation_bot import HistoryLearnSituationBot

logger = logging.getLogger(__name__)


class ExerciseService:
    def __init__(self, ws_msg_handler):
        self.ws_msg_handler: DownwardProtocolHandler = ws_msg_handler
        self.asr: ASR = ASR()
        self.correct_bot = CorrectBot()
        self.exercise_bot = ExerciseBot(ws_msg_handler=self.ws_msg_handler)
        self.history_situation_bot = HistoryLearnSituationBot()
        
    async def initialize(self, platform):
        treating_msg = await self.history_situation_bot.generate_treating_msg()
        await self.exercise_bot.send_treating_msg(treating_msg, platform)
                        
    async def _on_message_at_practise(self, student_text, platform):
        await self.exercise_bot.send_practise_msg(student_text, platform)
            
    async def process_student_message(self, student_message: StudentMessage, platfoem):
        student_text = student_message.text
        await self._on_message_at_practise(student_text, platform=platfoem)

    async def _on_asr_reg_error(self):
        await self.ws_msg_handler.send_tutor_message(text="对不起，我没有听清楚，请再说一遍")
            
    def replace_pinyin_if_same(self, messages: list[WordCorrectMessage], expected_messages: list[WordCorrectMessage]):
        if len(messages) != len(expected_messages):
            return messages, expected_messages
        else:
            for i in range(len(messages)):
                if messages[i].pinyin == expected_messages[i].pinyin:
                    messages[i] = copy.deepcopy(expected_messages[i])
            return messages, expected_messages
            
    async def _on_audio_at_practise(self, audio_message: AudioMessage, platform):
        asr_result, pron_result = await self.asr.transcribe(audio_message.audio_data, platform, self.exercise_bot.current_exercise)
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
        if not self.exercise_bot.current_exercise:
            await self.exercise_bot.send_practise_msg(student_text=asr_result, platform=platform)
            return
        expected_messages = parse_pinyin(self.exercise_bot.current_exercise)
        messages, expected_messages = self.replace_pinyin_if_same(messages, expected_messages)
        suggestions, score, name_2_mp4_url = await self.correct_bot.get_correct_result(expected_messages, messages)
        
        if score <= self.correct_bot.success_score:
            await self.ws_msg_handler.send_correct_message(suggestions=suggestions, expected_messages=expected_messages, msgs=messages, pron=pron_result, name_2_mp4_url=name_2_mp4_url)
            await self.ws_msg_handler.send_tutor_message(text="来，我们再试一次")
            self.exercise_bot.add_suggestion_to_context(suggestions)
        else:
            passed_practise = self.exercise_bot.current_exercise
            await self.exercise_bot.send_practise_msg(student_text=f"学生已经会读{passed_practise}了", platform=platform)

    async def process_audio_message(self, audio_message: AudioMessage, platform):
        await self._on_audio_at_practise(audio_message, platform)