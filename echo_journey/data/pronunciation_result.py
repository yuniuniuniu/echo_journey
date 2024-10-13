from dataclasses import dataclass


@dataclass
class PronumciationResult:
    paragraph_pronunciation_score: float = 0.0
    accuracy_score: float = 0.0
    completeness_score: float = 0.0
    fluency_score: float = 0.0
    prosody_score: float = 0.0    
        