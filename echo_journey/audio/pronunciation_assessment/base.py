from abc import ABC, abstractmethod

from echo_journey.common.utils import timed


class PronunciationAssseement(ABC):
    @abstractmethod
    @timed
    def begin(
        self,
        audio_bytes,
        platform="web",
    ) -> str:
        # platform: 'web' | 'mobile' | 'terminal'
        pass