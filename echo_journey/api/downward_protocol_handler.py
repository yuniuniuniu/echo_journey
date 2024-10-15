import logging

from echo_journey.api.proto.downward_message_wrapper import (
    wrap_downward_message,
)
from echo_journey.api.proto.downward_pb2 import SentenceCorrectMessage, TutorMessage, WordCorrectMessage

logger = logging.getLogger(__name__)


class DownwardProtocolHandler:

    def __init__(self, websocket, manager):
        self.websocket = websocket
        self.manager = manager


    @staticmethod
    def build_tutor_message(
        text,
        expected_messages = None,
        audio_bytes = None,
    ):
        teacher_message = TutorMessage()
        teacher_message.text = text
        if expected_messages:
            teacher_message.expected_messages.extend(expected_messages)
        if audio_bytes:
            teacher_message.audio = audio_bytes
        return teacher_message

    async def send_tutor_message(self, text, expected_messages = None, audio_bytes = None):
        tutor_msg = self.build_tutor_message(text, expected_messages, audio_bytes)
        await self.send_websocket_downward_message(
            wrap_downward_message(tutor_msg)
        )
        
    @staticmethod
    def build_sentence_correct_message(
        suggestions,
        expected_msgs = None,
        msgs = None,
        pron = None,
    ):
        sentence_correct_message = SentenceCorrectMessage()
        if expected_msgs:
            sentence_correct_message.expected_messages.extend(expected_msgs)
        if msgs:
            sentence_correct_message.messages.extend(msgs)
        if pron:
            sentence_correct_message.accuracy_score = pron.accuracy_score
            sentence_correct_message.fluency_score = pron.fluency_score
        sentence_correct_message.suggestions = suggestions
        return sentence_correct_message

    async def send_correct_message(self, suggestions, expected_messages, msgs, pron):
        correct_msg = self.build_sentence_correct_message(suggestions, expected_messages, msgs, pron)
        await self.send_websocket_downward_message(
            wrap_downward_message(correct_msg)
        )

    async def send_websocket_downward_message(self, downward_message):
        await self.websocket.send_bytes(downward_message.SerializeToString())

    async def send_websocket_message(self, message):
        await self.send_websocket_downward_message(wrap_downward_message(message))