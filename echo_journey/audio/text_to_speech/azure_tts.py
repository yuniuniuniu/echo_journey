import asyncio
import logging

from pydub import AudioSegment
from echo_journey.audio.text_to_speech.base import (
    TextToSpeech,
)
import io
from echo_journey.common.utils import Singleton, timed, get_timer
from dotenv import find_dotenv, load_dotenv
_ = load_dotenv(find_dotenv())

logger = logging.getLogger(__name__)

timer = get_timer()

class AzureTTS(Singleton, TextToSpeech):
    def __init__(self):
        super().__init__()
        logger.info("Initializing [AZURE Text To Speech] voices...")

    @timed
    async def generate_audio(self, text, speaker="podcast-16", platform="web"):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.tts_sync, text, speaker, platform)

    def tts_sync(self, text, speaker, platform):
        timer.start("AZURE_TTS")
        import azure.cognitiveservices.speech as speechsdk

        # Creates an instance of a speech config with specified subscription key and service region.
        speech_key = "9960d920f5744797919b9396c4213c17"
        service_region = "eastus2"
        speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
        # Note: the voice setting will not overwrite the voice element in input SSML.
        speech_config.speech_synthesis_voice_name = "zh-CN-YunyangNeural"
        speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)

        result = speech_synthesizer.speak_text_async(text).get()
        # Check result
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            logger.info("Speech synthesized for text [{}]".format(text))
        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = result.cancellation_details
            logger.info("Speech synthesis canceled: {}".format(cancellation_details.reason))
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                logger.info("Error details: {}".format(cancellation_details.error_details))
            return None

        audio_segment = AudioSegment.from_file(io.BytesIO(result.audio_data), format="wav")
        audio_segment = audio_segment.set_frame_rate(16000)
        audio_segment = audio_segment.set_sample_width(2)   # 16 bits -> 2 bytes
        audio_segment = audio_segment.set_channels(1)       # Mono

        output_io = io.BytesIO()
        if platform == "ios" or platform == "android":
            audio_segment.export(output_io, format="ipod")
        elif platform == "web" or platform == "web-android":
            audio_segment.export(output_io, format="webm")
        elif platform == "web-ios":
            audio_segment.export(output_io, format="wav")
        else:
            raise ValueError(f"Unsupported platform: {platform}")
        return output_io.getvalue()
