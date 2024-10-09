import io
import logging
import os
import types
from io import BytesIO

import speech_recognition as sr
from pydub import AudioSegment

from echo_journey.audio.speech_to_text.base import SpeechToText
from echo_journey.common.utils import Singleton, timed

logger = logging.getLogger(__name__)

config = types.SimpleNamespace(
    **{
        "url": os.getenv("KANYUN_ASR_URL"),
        "app_key": os.getenv("KANYUN_ASR_APP_KEY"),
    }
)


class Kanyun(SpeechToText, Singleton):
    def __init__(self):
        super().__init__()
        logger.info("Setting up [Kanyun Speech to Text]...")
        self.recognizer = sr.Recognizer()

    @timed
    def transcribe(
        self,
        audio_bytes,
        platform="web",
        prompt="",
        language="en-US",
        suppress_tokens=[-1],
    ) -> str:
        import requests

        if platform == "web":
            audio = self._convert_webm_to_wav(audio_bytes, False)
        elif platform == "mobile":
            pass
        else:
            audio = self._convert_bytes_to_wav(audio_bytes, False)

        wav_data = BytesIO(audio.get_wav_data())
        wav_data.name = "SpeechRecognition_audio.wav"

        response = requests.post(
            config.url,
            params={
                "appKey": config.app_key,
            },
            files={
                "audio": wav_data,
            },
        )

        if response.status_code != 200:
            err_msg = f"Error occur when Kanyun.transcribing audio, statusCode: {response.status_code}, responseContent: {response.text}"
            logger.error(err_msg)
            raise Exception(err_msg)

        json = response.json()
        print("Kanyun transcript is: ", json)
        return json["result"]

    def _convert_webm_to_wav(self, webm_data, local=True):
        webm_audio = AudioSegment.from_file(io.BytesIO(webm_data), format="webm")
        webm_audio = webm_audio.set_channels(1)
        webm_audio = webm_audio.set_frame_rate(16000)
        wav_data = io.BytesIO()
        webm_audio.export(wav_data, format="s16le", codec="pcm_s16le")
        return self._convert_bytes_to_wav(wav_data.getvalue(), local=local)

    def _convert_bytes_to_wav(self, audio_bytes, local=True):
        return sr.AudioData(audio_bytes, 16000, 2)
