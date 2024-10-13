from abc import ABC, abstractmethod

from echo_journey.common.utils import timed


class SpeechToText(ABC):
    @abstractmethod
    @timed
    def transcribe(
        self,
        wav_data,
    ) -> str:
        pass
