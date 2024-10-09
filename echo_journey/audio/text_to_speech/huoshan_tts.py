import asyncio
import base64
import json
import logging
import os
import types
import uuid

import requests

from echo_journey.audio.text_to_speech.base import (
    TextToSpeech,
    TextAudioTimeline,
)
from echo_journey.common.utils import Singleton, timed, get_timer

logger = logging.getLogger(__name__)

timer = get_timer()

config = types.SimpleNamespace(
    **{
        "app_id": os.getenv("HUOSHAN_TTS_APP_ID"),
        "access_token": os.getenv("HUOSHAN_TTS_ACCESS_TOKEN"),
        "cluster": "volcano_tts",
        "voice_type": "BV406_streaming",
        "api_url": "https://openspeech.bytedance.com/api/v1/tts",
    }
)


class HuoshanTTS(Singleton, TextToSpeech):
    def __init__(self):
        super().__init__()
        logger.info("Initializing [HUOSHAN Text To Speech] voices...")

    @timed
    async def generate_audio(
        self, text, language="zh-CN", speaker=None
    ):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.tts_sync, text)

    def tts_sync(self, text):
        timer.start("HUOSHAN_TTS")
        header = {"Authorization": f"Bearer;{config.access_token}"}

        request_json = {
            "app": {
                "appid": config.app_id,
                "token": config.access_token,
                "cluster": config.cluster,
            },
            "user": {"uid": "388808087185088"},
            "audio": {
                "voice_type": config.voice_type,
                "encoding": "mp3",
                "speed_ratio": 1.2,
                "volume_ratio": 1.0,
                "pitch_ratio": 0.9,
                "language": "cn",
            },
            "request": {
                "reqid": str(uuid.uuid4()),
                "text": text,
                "text_type": "plain",
                "operation": "query",
                "silence_duration": 700,
                "with_frontend": 1,
                "frontend_type": "unitTson",
                "split_sentence": 1,
            },
        }

        try:
            resp = requests.post(
                config.api_url, json.dumps(request_json), headers=header
            )
            timer.log("HUOSHAN_TTS")

            json_data = resp.json()
            if "data" in json_data:
                return base64.b64decode(
                    json_data["data"]
                ), _get_text_audio_timeline_list(json_data)
            else:
                logger.error(f"resp body: \n{resp.text}")
        except Exception as e:
            e.with_traceback()

        return b"", []


def _get_text_audio_timeline_list(json_data):
    # TextAudioTimeline
    time_audio_timeline_list = []
    if "addition" in json_data:
        if "frontend" in json_data["addition"]:
            json_frontend_data = json.loads(json_data["addition"]["frontend"])
            if "words" in json_frontend_data:
                for item in json_frontend_data["words"]:
                    time_audio_timeline_list.append(
                        TextAudioTimeline(
                            text=item["word"],
                            start_time=item["start_time"],
                            end_time=item["end_time"],
                        )
                    )
    return time_audio_timeline_list
