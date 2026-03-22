"""Tests for matcher registry."""

from custom_components.azure_speech_stt.stt_corrector.languages.mandarin import (
    PinyinMatcher,
)
from custom_components.azure_speech_stt.stt_corrector.matchers import (
    DefaultMatcher,
    PhoneticMatcher,
)
from custom_components.azure_speech_stt.stt_corrector.registry import (
    MatcherRegistry,
)


class TestMatcherRegistry:
    """Tests for MatcherRegistry locale-to-matcher resolution."""

    def test_mandarin_zh_cn_includes_pinyin(self) -> None:
        """zh-CN locale should include PinyinMatcher + DefaultMatcher."""
        matchers = MatcherRegistry.get_matchers("zh-CN")
        assert len(matchers) == 2
        assert isinstance(matchers[0], PinyinMatcher)
        assert isinstance(matchers[1], DefaultMatcher)

    def test_mandarin_zh_tw_includes_pinyin(self) -> None:
        """zh-TW locale should include PinyinMatcher + DefaultMatcher."""
        matchers = MatcherRegistry.get_matchers("zh-TW")
        assert len(matchers) == 2
        assert isinstance(matchers[0], PinyinMatcher)
        assert isinstance(matchers[1], DefaultMatcher)

    def test_english_uses_default_only(self) -> None:
        """en-US locale should only use DefaultMatcher."""
        matchers = MatcherRegistry.get_matchers("en-US")
        assert len(matchers) == 1
        assert isinstance(matchers[0], DefaultMatcher)

    def test_japanese_uses_default_only(self) -> None:
        """ja-JP locale (no registered matcher) should fall back to DefaultMatcher."""
        matchers = MatcherRegistry.get_matchers("ja-JP")
        assert len(matchers) == 1
        assert isinstance(matchers[0], DefaultMatcher)

    def test_none_locale_includes_pinyin(self) -> None:
        """None locale (unknown) should include all matchers as fallback."""
        matchers = MatcherRegistry.get_matchers(None)
        assert len(matchers) == 2
        assert isinstance(matchers[0], PinyinMatcher)
        assert isinstance(matchers[1], DefaultMatcher)

    def test_default_matcher_always_last(self) -> None:
        """DefaultMatcher should always be the last matcher."""
        for locale in ["zh-CN", "en-US", "ja-JP", None]:
            matchers = MatcherRegistry.get_matchers(locale)
            assert isinstance(matchers[-1], DefaultMatcher)

    def test_all_returned_matchers_are_phonetic_matchers(self) -> None:
        """All returned matchers should be PhoneticMatcher instances."""
        for locale in ["zh-CN", "en-US", None]:
            matchers = MatcherRegistry.get_matchers(locale)
            for m in matchers:
                assert isinstance(m, PhoneticMatcher)

    def test_cantonese_not_pinyin(self) -> None:
        """Cantonese (yue-CN) should NOT use PinyinMatcher."""
        matchers = MatcherRegistry.get_matchers("yue-CN")
        assert len(matchers) == 1
        assert isinstance(matchers[0], DefaultMatcher)
