from fastapi.testclient import TestClient

import sys
sys.path.append("/root/echo_journey")
from echo_journey.api.proto.downward_message_wrapper import (
    unwrap_downward_message_from_bytes,
)

from echo_journey.api.proto.downward_pb2 import SentenceCorrectMessage, TutorMessage
from echo_journey.api.proto.upward_message_wrapper import wrap_upward_message

from echo_journey.api.proto.upward_pb2 import AudioMessage, StudentMessage
from echo_journey.main import app
from pydub import AudioSegment
import io
import speech_recognition as sr

def convert_wav_file_to_pcm_bytes(audio_file_path):
    wav_audio = AudioSegment.from_file(audio_file_path, format="wav")
    webm_io = io.BytesIO()
    wav_audio.export(webm_io, format="webm")
    webm_data = webm_io.getvalue()
    return webm_data

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
        student_text_message.text = "去喝咖啡"
        websocket.send_bytes(
            wrap_upward_message(student_text_message).SerializeToString()
        )

        response_data_bytes = websocket.receive_bytes()
        downward_message = unwrap_downward_message_from_bytes(response_data_bytes)
        assert isinstance(downward_message, TutorMessage)
        
        
        audio_message = AudioMessage()
        audio_message.expected_sentence = "啊微"
        audio_message.audio_data = convert_wav_file_to_pcm_bytes("tests/data/test.wav")
        websocket.send_bytes(
            wrap_upward_message(audio_message).SerializeToString()
        )

        response_data_bytes = websocket.receive_bytes()
        downward_message = unwrap_downward_message_from_bytes(response_data_bytes)
        assert isinstance(downward_message, SentenceCorrectMessage)

        response_data_bytes = websocket.receive_bytes()
        downward_message = unwrap_downward_message_from_bytes(response_data_bytes)
        assert isinstance(downward_message, TutorMessage)