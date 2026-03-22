"""Two-stage STT text correction pipeline."""

from __future__ import annotations

from .fuzzy_matcher import FuzzyMatcher
from .matchers import PhoneticMatcher
from .types import (
    CorrectionChange,
    CorrectionMethod,
    CorrectionResult,
    DiagnosticResult,
)


class SpeechCorrector:
    """Two-stage text correction pipeline for STT output.

    Pipeline stages (executed in order):
    1. Custom replacements - user-defined string substitutions
    2. Fuzzy/Pinyin matching - pinyin for Chinese, SequenceMatcher for others
    """

    def __init__(
        self,
        known_phrases: list[str] | None = None,
        custom_replacements: dict[str, str] | None = None,
        fuzzy_threshold: float = 0.80,
        enable_custom_replacements: bool = True,
        enable_fuzzy_matching: bool = True,
        matchers: list[PhoneticMatcher] | None = None,
        exclusions: list[str] | None = None,
    ) -> None:
        """Initialize the two-stage corrector.

        Args:
            known_phrases: Correct phrases for fuzzy/pinyin matching.
            custom_replacements: Custom string replacement rules.
            fuzzy_threshold: Minimum similarity for fuzzy matching (0.0-1.0).
            enable_custom_replacements: Toggle custom replacement stage.
            enable_fuzzy_matching: Toggle fuzzy/pinyin matching stage.
            matchers: Ordered list of phonetic matchers for fuzzy matching.
                      Defaults to [PinyinMatcher(), DefaultMatcher()].
            exclusions: Segments to never correct via fuzzy matching.
        """
        # Stage flags
        self._enable_custom_replacements = enable_custom_replacements
        self._enable_fuzzy_matching = enable_fuzzy_matching

        # Stage 1: Custom replacements
        self._custom_replacements = custom_replacements or {}

        # Stage 2: Fuzzy matching with pluggable phonetic matchers
        self._fuzzy = FuzzyMatcher(
            known_phrases=known_phrases or [],
            threshold=fuzzy_threshold,
            matchers=matchers,
            exclusions=exclusions,
        )

    def correct(self, text: str) -> CorrectionResult:
        """Run the two-stage correction pipeline.

        Args:
            text: Input text to correct.

        Returns:
            CorrectionResult with original text, corrected text, and changes.
        """
        if not text:
            return CorrectionResult(original=text, corrected=text)

        all_changes: list[CorrectionChange] = []
        current = text

        # Stage 1: Custom replacements
        if self._enable_custom_replacements:
            current, custom_changes = self._apply_custom_replacements(current)
            all_changes.extend(custom_changes)

        # Stage 2: Fuzzy/Pinyin matching
        if self._enable_fuzzy_matching:
            current, fuzzy_changes = self._fuzzy.correct(current)
            all_changes.extend(fuzzy_changes)

        return CorrectionResult(
            original=text,
            corrected=current,
            changes=all_changes,
        )

    def diagnose(self, text: str) -> DiagnosticResult:
        """Run correction pipeline with diagnostic candidate info.

        Returns the same correction result plus all fuzzy match
        candidates and their scores. Candidates are computed against
        the post-custom-replacement text (what the fuzzy matcher sees).
        """
        if not text:
            return DiagnosticResult(original=text, corrected=text)

        all_changes: list[CorrectionChange] = []
        current = text

        # Stage 1: Custom replacements
        if self._enable_custom_replacements:
            current, custom_changes = self._apply_custom_replacements(current)
            all_changes.extend(custom_changes)

        # Cache post-replacement text for candidate computation (avoids
        # calling _apply_custom_replacements twice)
        post_replacement = current

        # Stage 2: Fuzzy/Pinyin matching
        if self._enable_fuzzy_matching:
            current, fuzzy_changes = self._fuzzy.correct(current)
            all_changes.extend(fuzzy_changes)

        # Candidates computed against post-replacement text
        candidates = (
            self._fuzzy.find_candidates(post_replacement)
            if self._enable_fuzzy_matching
            else []
        )

        return DiagnosticResult(
            original=text,
            corrected=current,
            changes=all_changes,
            candidates=candidates,
        )

    def update_phrases(self, phrases: list[str]) -> None:
        """Update the fuzzy matcher's known phrases.

        Args:
            phrases: New list of correct phrases.
        """
        self._fuzzy.update_phrases(phrases)

    def _apply_custom_replacements(
        self, text: str
    ) -> tuple[str, list[CorrectionChange]]:
        """Apply custom string replacements.

        Rules are sorted by key length descending to prevent partial matches.

        Args:
            text: Text to apply replacements to.

        Returns:
            Tuple of (corrected_text, list_of_changes).
        """
        if not self._custom_replacements:
            return text, []

        changes: list[CorrectionChange] = []
        corrected = text

        # Sort by key length descending
        sorted_rules = sorted(
            self._custom_replacements.items(),
            key=lambda item: len(item[0]),
            reverse=True,
        )

        for old, new in sorted_rules:
            if old in corrected:
                corrected = corrected.replace(old, new)
                changes.append(
                    CorrectionChange(
                        original_segment=old,
                        corrected_segment=new,
                        method=CorrectionMethod.CUSTOM_RULE,
                        confidence=1.0,
                    )
                )

        return corrected, changes
