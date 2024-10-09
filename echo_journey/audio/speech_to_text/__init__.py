import os

from echo_journey.audio.speech_to_text.base import SpeechToText


def get_speech_to_text() -> SpeechToText:
    use = os.getenv('SPEECH_TO_TEXT_USE', 'LOCAL_WHISPER')
    if use == 'KANYUN':
        from echo_journey.audio.speech_to_text.kanyun import Kanyun
        Kanyun.initialize()
        return Kanyun.get_instance()
    else:
        raise NotImplementedError(f'Unknown speech to text engine: {use}')
