from abc import ABC, abstractmethod

from echo_journey.common.utils import timed


class TextToSpeech(ABC):
    @abstractmethod
    @timed
    async def generate_audio(self, *args, **kwargs):
        pass


class TextAudioTimeline:
    def __init__(self, text, start_time, end_time):
        self.text = text
        self.start_time = start_time
        self.end_time = end_time
