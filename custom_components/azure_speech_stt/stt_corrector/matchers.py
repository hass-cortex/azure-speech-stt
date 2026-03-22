"""Extensible phonetic matcher architecture for language-specific matching.

Each PhoneticMatcher defines how to compare text phonetically and how to
generate sliding windows for a specific language family. The FuzzyMatcher
tries matchers in order and uses the first one that supports the input text.

To add a new language:
    1. Subclass PhoneticMatcher
    2. Implement supports(), similarity(), and windows()
    3. Pass the matcher to FuzzyMatcher or SpeechCorrector via the matchers parameter
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from difflib import SequenceMatcher


class PhoneticMatcher(ABC):
    """Base class for language-specific phonetic matching."""

    @abstractmethod
    def supports(self, text: str) -> bool:
        """Check if this matcher can handle the given text."""

    @abstractmethod
    def similarity(self, text_a: str, text_b: str) -> float:
        """Compute phonetic similarity between two strings.

        Returns:
            Similarity ratio between 0.0 and 1.0.
        """

    @abstractmethod
    def windows(self, text: str, phrase: str) -> list[tuple[int, int]]:
        """Generate sliding windows for matching phrase in text.

        Returns:
            List of (start, end) character index tuples.
        """


_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")


class PinyinMatcher(PhoneticMatcher):
    """Chinese phonetic matching using pypinyin.

    Handles CJK text with character-level sliding windows and
    pinyin-based similarity comparison. Only activates for text
    containing CJK characters.

    Note: Locale-based matcher selection at the entity level controls
    whether PinyinMatcher is included at all. The supports() check
    provides a second guard for mixed-language text.
    """

    def supports(self, text: str) -> bool:
        return bool(_CJK_RE.search(text))

    def similarity(self, text_a: str, text_b: str) -> float:
        from .pinyin_matcher import pinyin_similarity

        return pinyin_similarity(text_a, text_b)

    def windows(self, text: str, phrase: str) -> list[tuple[int, int]]:
        phrase_len = len(phrase)
        result: list[tuple[int, int]] = []
        for window_size in range(max(1, phrase_len - 1), phrase_len + 2):
            for start in range(max(0, len(text) - window_size + 1)):
                end = start + window_size
                if end <= len(text):
                    result.append((start, end))
        return result


class DefaultMatcher(PhoneticMatcher):
    """Default matcher using difflib.SequenceMatcher.

    Handles non-CJK text with word-boundary-aware sliding windows.
    Always returns True for supports() — used as the fallback matcher.
    """

    def supports(self, text: str) -> bool:
        return True

    def similarity(self, text_a: str, text_b: str) -> float:
        return SequenceMatcher(None, text_a, text_b).ratio()

    def windows(self, text: str, phrase: str) -> list[tuple[int, int]]:
        word_spans: list[tuple[int, int]] = [
            (m.start(), m.end()) for m in re.finditer(r"\S+", text)
        ]
        if not word_spans:
            return []

        phrase_word_count = len(phrase.split())
        result: list[tuple[int, int]] = []

        for num_words in range(max(1, phrase_word_count - 1), phrase_word_count + 2):
            for start_idx in range(len(word_spans) - num_words + 1):
                end_idx = start_idx + num_words
                char_start = word_spans[start_idx][0]
                char_end = word_spans[end_idx - 1][1]
                result.append((char_start, char_end))

        return result
