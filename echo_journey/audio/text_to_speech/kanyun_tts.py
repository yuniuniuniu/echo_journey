import asyncio
import logging

from py_yuntts_client import NacosClient, TtsRequest
from pydub import AudioSegment
from echo_journey.audio.text_to_speech.base import (
    TextToSpeech,
)
import io
from echo_journey.common.utils import Singleton, timed, get_timer

logger = logging.getLogger(__name__)

timer = get_timer()

class KanyunTTS(Singleton, TextToSpeech):
    def __init__(self):
        super().__init__()
        logger.info("Initializing [KANYUN Text To Speech] voices...")
        self.client = NacosClient(service_name="apeman-yuntts")

    @timed
    async def generate_audio(self, text, speaker="podcast-16", platform="web"):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.tts_sync, text, speaker, platform)

    def tts_sync(self, text, speaker, platform):
        timer.start("KANYUN_TTS")
        tts_request = TtsRequest(
            text=text,
            encoding="wav",
            speaker=speaker,
            app_id="math-tutor",
            user_id="math-tutor-lab",
            language="zh-CN",
            speed_ratio=0.7,
        )
        tts_response = self.client.tts(tts_request)
        audio_bytes = bytes.fromhex(tts_response.audio.audio_bytes)
        audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes), format="wav")
        audio_segment = audio_segment.set_frame_rate(16000)
        audio_segment = audio_segment.set_sample_width(2)   # 16 bits -> 2 bytes
        audio_segment = audio_segment.set_channels(1)       # Mono

        output_io = io.BytesIO()
        if platform == "web" or platform == "android":
            audio_segment.export(output_io, format="webm")
        elif platform == "ios":
            audio_segment.export(output_io, format="ipod")
        else:
            raise ValueError(f"Unsupported platform: {platform}")
        return output_io.getvalue()
