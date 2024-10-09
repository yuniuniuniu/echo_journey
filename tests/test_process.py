from fastapi.testclient import TestClient

import sys
sys.path.append("/home/trader/echo_journey")
from echo_journey.api.proto.downward_message_wrapper import (
    unwrap_downward_message_from_bytes,
)

from echo_journey.api.proto.downward_pb2 import SentenceCorrectMessage, TutorMessage
from echo_journey.api.proto.upward_message_wrapper import wrap_upward_message

from echo_journey.api.proto.upward_pb2 import AudioMessage, StudentMessage
from echo_journey.main import app


def test_websocket():
    client = TestClient(app)  # app is fastapi instance
    fake_session_id = "fake_session_id"
    with client.websocket_connect(
        f"/ws/talk/{fake_session_id}"
    ) as websocket:
        response_data_bytes = websocket.receive_bytes()
        downward_message = unwrap_downward_message_from_bytes(response_data_bytes)
        assert isinstance(downward_message, TutorMessage)

        student_text_message = StudentMessage()  # send student message
        student_text_message.text = "咖啡"
        websocket.send_bytes(
            wrap_upward_message(student_text_message).SerializeToString()
        )

        response_data_bytes = websocket.receive_bytes()
        downward_message = unwrap_downward_message_from_bytes(response_data_bytes)
        assert isinstance(downward_message, TutorMessage)
        
        
        audio_message = AudioMessage()
        audio_message.expected_sentence = "我不知道啊"
        websocket.send_bytes(
            wrap_upward_message(audio_message).SerializeToString()
        )

        response_data_bytes = websocket.receive_bytes()
        downward_message = unwrap_downward_message_from_bytes(response_data_bytes)
        assert isinstance(downward_message, SentenceCorrectMessage)
