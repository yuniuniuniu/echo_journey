import io
import logging
import os
import types

import speech_recognition as sr
from pydub import AudioSegment

from echo_journey.audio.pronunciation_assessment.base import PronunciationAssseement
from echo_journey.common.utils import Singleton, timed
import azure.cognitiveservices.speech as speechsdk
import time

from echo_journey.data.pronunciation_result import PronumciationResult
from dotenv import find_dotenv, load_dotenv
_ = load_dotenv(find_dotenv())


logger = logging.getLogger(__name__)

config = types.SimpleNamespace(
    **{
        "speech_key": os.getenv("AZURE_ASR_APP_KEY"),
        "region": os.getenv("AZURE_REGION"),
    }
)

class AzureAssessment(PronunciationAssseement, Singleton):
    def __init__(self):
        super().__init__()
        logger.info("Setting up [Azure Speech to Text]...")
        self.recognizer = sr.Recognizer()
        
    async def pronunciation_assessment_continuous_from_bytes(self, wav_bytes, reference_text):
        result = PronumciationResult()
        import difflib
        import json
        speech_config = speechsdk.SpeechConfig(subscription=config.speech_key, region=config.region)
        audio_stream = speechsdk.audio.PushAudioInputStream()
        audio_config = speechsdk.audio.AudioConfig(stream=audio_stream)
        audio_stream.write(wav_bytes)
        audio_stream.close()        
        enable_miscue = True
        enable_prosody_assessment = True
        pronunciation_config = speechsdk.PronunciationAssessmentConfig(
            reference_text=reference_text,
            grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
            granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
            enable_miscue=enable_miscue)
        if enable_prosody_assessment:
            pronunciation_config.enable_prosody_assessment()
        language = 'zh-CN'
        speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, language=language, audio_config=audio_config)
        pronunciation_config.apply_to(speech_recognizer)
        done = False

        def stop_cb(evt: speechsdk.SessionEventArgs):
            """callback that signals to stop continuous recognition upon receiving an event `evt`"""
            logger.info('CLOSING on {}'.format(evt))
            nonlocal done
            done = True

        def recognized(evt: speechsdk.SpeechRecognitionEventArgs):
            nonlocal result
            logger.info('pronunciation assessment for: {}'.format(evt.result.text))
            pronunciation_result = speechsdk.PronunciationAssessmentResult(evt.result)
            result.paragraph_pronunciation_score = pronunciation_result.pronunciation_score
            result.accuracy_score = pronunciation_result.accuracy_score
            result.completeness_score = pronunciation_result.completeness_score
            result.fluency_score = pronunciation_result.fluency_score
            result.prosody_score = pronunciation_result.prosody_score
        speech_recognizer.recognized.connect(recognized)
        speech_recognizer.session_started.connect(lambda evt: logger.info('SESSION STARTED: {}'.format(evt)))
        speech_recognizer.session_stopped.connect(lambda evt: logger.info('SESSION STOPPED {}'.format(evt)))
        speech_recognizer.canceled.connect(lambda evt: logger.info('CANCELED {}'.format(evt)))
        speech_recognizer.session_stopped.connect(stop_cb)
        speech_recognizer.canceled.connect(stop_cb)

        speech_recognizer.start_continuous_recognition()
        while not done:
            time.sleep(.5)

        speech_recognizer.stop_continuous_recognition()
        return result

    @timed
    async def begin(
        self,
        wav_data,
        expected_text
    ) -> str:
        try:
            return await self.pronunciation_assessment_continuous_from_bytes(wav_data, expected_text)    
        except Exception as e:
            logger.error(f"Error occur when Azure.assessment : {e}")
            return None

    def _convert_webm_to_wav(self, webm_data, local=True):
        webm_audio = AudioSegment.from_file(io.BytesIO(webm_data), format="webm")
        webm_audio = webm_audio.set_channels(1)
        webm_audio = webm_audio.set_frame_rate(16000)
        wav_data = io.BytesIO()
        webm_audio.export(wav_data, format="s16le", codec="pcm_s16le")
        return self._convert_bytes_to_wav(wav_data.getvalue(), local=local)
    
    def _convert_m4a_to_wav(self, m4a_data, local=True):
        m4a_audio = AudioSegment.from_file(io.BytesIO(m4a_data), format="m4a")
        m4a_audio = m4a_audio.set_channels(1)
        m4a_audio = m4a_audio.set_frame_rate(16000)
        wav_data = io.BytesIO()
        m4a_audio.export(wav_data, format="wav", codec="pcm_s16le")
        return self._convert_bytes_to_wav(wav_data.getvalue(), local=local)

    def _convert_bytes_to_wav(self, audio_bytes, local=True):
        return sr.AudioData(audio_bytes, 16000, 2)
