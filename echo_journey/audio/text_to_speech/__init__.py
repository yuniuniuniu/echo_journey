import os

from echo_journey.audio.text_to_speech.base import TextToSpeech


def get_text_to_speech(tts: str = None) -> TextToSpeech:
    if not tts:
        tts = os.getenv("TEXT_TO_SPEECH_USE", "ELEVEN_LABS")
    if tts == "KANYUN_TTS":
        from echo_journey.audio.text_to_speech.kanyun_tts import KanyunTTS

        KanyunTTS.initialize()
        return KanyunTTS.get_instance()
    elif tts == "HUOSHAN_TTS":
        from echo_journey.audio.text_to_speech.huoshan_tts import HuoshanTTS

        HuoshanTTS.initialize()
        return HuoshanTTS.get_instance()
    else:
        raise NotImplementedError(f"Unknown text to speech engine: {tts}")
