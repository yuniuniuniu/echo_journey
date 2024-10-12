from echo_journey.audio.speech_to_text.azure import Azure
from echo_journey.audio.speech_to_text.kanyun import Kanyun
from echo_journey.common.utils import parse_pinyin


class ASR:
    def __init__(self):
        self.asr = Kanyun.get_instance()
        self.asr_back = Azure.get_instance()

    def transcribe(self, audio_bytes, platform="web", prompt="", language="zh-cn", suppress_tokens=[-1]) -> str:
        asr_result = self.asr.transcribe(audio_bytes, platform, prompt, language, suppress_tokens)
        try:
            parse_pinyin(asr_result) 
        except Exception as e:
            asr_result = self.asr_back.transcribe(audio_bytes, platform, prompt, language, suppress_tokens)
        return asr_result
        