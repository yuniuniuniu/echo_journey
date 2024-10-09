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
        expected_messages,
    ):
        if not expected_messages:
            expected_message = WordCorrectMessage()
            expected_message.word = "null"
            expected_message.initial_consonant = "null"
            expected_message.vowels = "null"
            expected_message.tone = -1
            expected_messages = [expected_message, expected_message]
        teacher_message = TutorMessage()
        teacher_message.text = text
        teacher_message.expected_messages.extend(expected_messages)
        return teacher_message

    async def send_tutor_message(self, text, expected_messages = None):
        tutor_msg = self.build_tutor_message(text, expected_messages)
        await self.send_websocket_downward_message(
            wrap_downward_message(tutor_msg)
        )
        
    @staticmethod
    def build_sentence_correct_message(
        suggestions,
        expected_msgs,
        msgs,
    ):
        sentence_correct_message = SentenceCorrectMessage()
        sentence_correct_message.expected_messages.extend(expected_msgs)
        sentence_correct_message.messages.extend(msgs)
        sentence_correct_message.suggestions = suggestions
        return sentence_correct_message

    async def send_correct_message(self, suggestions, expected_messages, msgs):
        correct_msg = self.build_sentence_correct_message(suggestions, expected_messages, msgs)
        await self.send_websocket_downward_message(
            wrap_downward_message(correct_msg)
        )

    async def send_websocket_downward_message(self, downward_message):
        await self.websocket.send_bytes(downward_message.SerializeToString())

    async def send_websocket_message(self, message):
        await self.send_websocket_downward_message(wrap_downward_message(message))