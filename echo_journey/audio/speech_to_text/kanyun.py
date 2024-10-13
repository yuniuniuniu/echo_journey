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
from dotenv import find_dotenv, load_dotenv
_ = load_dotenv(find_dotenv())

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
        wav_data,
    ) -> str:
        import requests
        wav_data_in_io = io.BytesIO(wav_data)
        wav_data_in_io.name = "SpeechRecognition_audio.wav"

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
            return None

        json = response.json()
        ret = json["result"]
        logger.info(f"Kanyun transcript is: {ret}")
        return ret
