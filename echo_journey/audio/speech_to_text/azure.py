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
        "url": os.getenv("AZURE_ASR_URL"),
        "app_key": os.getenv("AZURE_ASR_APP_KEY"),
    }
)


class Azure(SpeechToText, Singleton):
    def __init__(self):
        super().__init__()
        logger.info("Setting up [Azure Speech to Text]...")
        self.recognizer = sr.Recognizer()

    @timed
    def transcribe(
        self,
        wav_data,
    ) -> str:
        import requests

        response = requests.post(
            config.url,
            headers={
                "Ocp-Apim-Subscription-Key": config.app_key,
                'Accept': 'application/json'
            },
            files = {
                'audio': wav_data,
                'definition': (None, '{"locales":["zh-CN"], "profanityFilterMode": "Masked", "channels": [0,1]}', 'application/json')
            }
        )

        if response.status_code != 200:
            err_msg = f"Error occur when Azure.transcribing audio, statusCode: {response.status_code}, responseContent: {response.text}"
            logger.error(err_msg)
            return None

        json = response.json()
        logger.info("Azure transcript is: ", json)
        return json["combinedPhrases"][0]["text"]
