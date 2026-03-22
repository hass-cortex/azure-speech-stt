"""STT post-recognition text correction library."""

from .corrector import SpeechCorrector
from .fuzzy_matcher import FuzzyMatcher
from .matchers import DefaultMatcher, PhoneticMatcher, PinyinMatcher
from .types import (
    CorrectionCandidate,
    CorrectionChange,
    CorrectionMethod,
    CorrectionResult,
    DiagnosticResult,
)

__all__ = [
    "CorrectionCandidate",
    "CorrectionChange",
    "CorrectionMethod",
    "CorrectionResult",
    "DiagnosticResult",
    "DefaultMatcher",
    "FuzzyMatcher",
    "PhoneticMatcher",
    "PinyinMatcher",
    "SpeechCorrector",
]
