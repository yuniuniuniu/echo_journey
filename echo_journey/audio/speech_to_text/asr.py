import io
import logging
from echo_journey.audio.pronunciation_assessment.azure import AzureAssessment
from echo_journey.audio.speech_to_text.azure import Azure
from echo_journey.audio.speech_to_text.kanyun import Kanyun
from echo_journey.common.utils import parse_pinyin, device_id_var, session_id_var
import speech_recognition as sr
from pydub import AudioSegment

from echo_journey.data.practise_progress import PractiseStatus

logger = logging.getLogger(__name__)
class ASR:
    def __init__(self):
        self.asr = Kanyun.get_instance()
        self.asr_back = Azure.get_instance()
        self.pronunciator = AzureAssessment.get_instance()
        
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

    async def transcribe(self, audio_bytes, platform="web", expected_text=None, status=None) -> str:
        device_id = device_id_var.get()
        session_id = session_id_var.get()
        try:
            if platform == "web" or platform == "web-android":
                audio = self._convert_webm_to_wav(audio_bytes, False)
            elif platform == "ios" or platform == "android" or platform == "web-ios":
                audio = self._convert_m4a_to_wav(audio_bytes, False)
            else:
                raise ValueError(f"Unsupported platform: {platform}")
            wav_data = audio.get_wav_data()
            audio_segment = AudioSegment.from_wav(io.BytesIO(wav_data))

            export_wav_dir_path = f"user_info/{device_id}/asr_data"
            import os
            if not os.path.exists(export_wav_dir_path):
                os.makedirs(export_wav_dir_path)
            if expected_text and status==PractiseStatus.SENTENCE:
                import asyncio
                asr_result, pron_result = await asyncio.gather(self.do_asr(wav_data), self.do_pronunciation_asses(wav_data, expected_text))
                name = f"{export_wav_dir_path}/SpeechRecognition_audio_{session_id}_{asr_result}_{expected_text}.wav" if asr_result else f"{export_wav_dir_path}/SpeechRecognition_audio_{session_id}_null_{expected_text}.wav"
                audio_segment.export(name, format="wav")
                return asr_result, pron_result  
            else:
                asr_result = await self.do_asr(wav_data)
                name = f"{export_wav_dir_path}/SpeechRecognition_audio_{session_id}_{asr_result}.wav" if asr_result else f"{export_wav_dir_path}/SpeechRecognition_audio_{session_id}_null.wav"
                audio_segment.export(name, format="wav")
                return asr_result, None
        except Exception as e:
            logger.error(f"Error occur when ASR.transcribe : {e}")
            return None, None
        
    async def do_asr(self, wav_data):
        asr_result = self.asr.transcribe(wav_data)
        try:
            parse_pinyin(asr_result) 
        except Exception as e:
            try:
                asr_result = self.asr_back.transcribe(wav_data)
            except Exception as e:
                logger.error(f"Error occur when ASR.do_asr : {e}")
                return None
        return asr_result

    async def do_pronunciation_asses(self, wav_data, expected_text):
        try:
            return await self.pronunciator.begin(wav_data, expected_text)
        except Exception as e:
            logger.error(f"Error occur when ASR.do_pronunciation_asses : {e}")
            return None
        