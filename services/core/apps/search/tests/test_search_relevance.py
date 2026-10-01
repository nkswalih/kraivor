"""Tests for compute_relevance.

This function produces the `relevance` field on every SearchResult across
projects, tasks, knowledge, repositories, notifications, chat and profiles,
so its scoring contract is load-bearing and previously had no direct tests.

The tiering matters for result ordering:

  prefix match (1.0) > substring match (0.7) > fuzzy overlap (<= 0.4)

`type_score` scales the final value per source type.
"""

import pytest

from apps.search.services import compute_relevance

pytestmark = pytest.mark.unit


class TestEmptyInputs:
    def test_empty_text_scores_zero(self):
        assert compute_relevance("", "query") == 0.0

    def test_empty_query_scores_zero(self):
        assert compute_relevance("some text", "") == 0.0

    def test_both_empty_scores_zero(self):
        assert compute_relevance("", "") == 0.0

    def test_type_score_does_not_rescue_empty_text(self):
        """A 0.0 base must stay 0.0; no source weight may invent relevance."""
        assert compute_relevance("", "query", type_score=1.0) == 0.0


class TestTiering:
    def test_prefix_match_scores_full(self):
        assert compute_relevance("authentication service", "auth") == 1.0

    def test_substring_match_scores_sevenths(self):
        assert compute_relevance("the authentication service", "auth") == 0.7

    def test_fuzzy_overlap_is_capped_below_substring(self):
        """All query chars present but not contiguous must not reach 0.7.

        This is the property that keeps a fuzzy hit from outranking a real
        substring match in the merged result list.
        """
        fuzzy = compute_relevance("a-u-t-h scrambled", "auth")
        assert fuzzy < 0.7
        assert fuzzy > 0.0

    def test_tier_ordering_is_prefix_then_substring_then_fuzzy(self):
        prefix = compute_relevance("auth service", "auth")
        substring = compute_relevance("the auth service", "auth")
        fuzzy = compute_relevance("a-u-t-h", "auth")
        assert prefix > substring > fuzzy

    def test_no_characters_in_common_scores_zero(self):
        assert compute_relevance("nothing alike", "qjxz") == 0.0


class TestCaseInsensitivity:
    def test_matching_is_case_insensitive(self):
        assert compute_relevance("Authentication", "auth") == 1.0

    def test_query_case_does_not_matter(self):
        assert compute_relevance("auth service", "AUTH") == 1.0

    def test_prefix_detection_is_case_insensitive(self):
        """A prefix match must still score 1.0, not fall through to 0.7."""
        assert compute_relevance("AUTHENTICATION", "auth") == 1.0


class TestTypeScore:
    def test_type_score_scales_the_result(self):
        assert compute_relevance("auth", "auth", type_score=0.8) == pytest.approx(0.8)

    def test_type_score_scales_substring_tier(self):
        assert compute_relevance("the auth", "auth", type_score=0.5) == pytest.approx(
            0.35
        )

    def test_zero_type_score_zeroes_relevance(self):
        assert compute_relevance("auth", "auth", type_score=0.0) == 0.0

    def test_type_score_greater_than_one_can_exceed_one(self):
        """Not clamped — a source may be weighted above 1.0 by design."""
        assert compute_relevance("auth", "auth", type_score=1.2) == pytest.approx(1.2)


class TestFuzzyScoring:
    def test_fuzzy_is_character_overlap_ratio(self):
        # "ab" against "axb": both query chars are present.
        assert compute_relevance("axb", "ab") == pytest.approx(0.4)

    def test_fuzzy_proportions_partial_overlap(self):
        # "ab" against "ay": one of two query chars present -> 0.5 * 0.4.
        assert compute_relevance("ay", "ab") == pytest.approx(0.2)

    def test_repeated_query_chars_count_each_time(self):
        # "aa" against "axa" -> both query chars found -> full 0.4.
        assert compute_relevance("axa", "aa") == pytest.approx(0.4)

    def test_repeated_query_chars_can_score_on_one_text_char(self):
        # Each query character is counted independently, so one text character
        # can satisfy every repetition. "xyzzy" scores 0.16 against
        # "completely unrelated" purely because that phrase contains two y's.
        # This is a known weakness of character-overlap scoring, pinned here
        # so a future change to it is a deliberate decision, not a surprise.
        assert compute_relevance("completely unrelated", "xyzzy") == pytest.approx(0.16)

    def test_single_char_query_uses_the_prefix_tier_when_it_matches(self):
        # "a" is a prefix of "abc", so this never reaches the fuzzy branch.
        assert compute_relevance("abc", "a") == 1.0

    def test_single_char_query_uses_the_substring_tier_when_embedded(self):
        assert compute_relevance("bcd", "c") == 0.7

    def test_single_char_query_reaches_the_fuzzy_branch_when_absent(self):
        # No 'a' anywhere in "bcx", so the fuzzy branch runs on a
        # single-character query — the max() guard against /0 matters here.
        assert compute_relevance("bcx", "a") == 0.0


class TestResultContract:
    @pytest.mark.parametrize(
        ("text", "query"),
        [
            ("auth service", "auth"),
            ("the auth service", "auth"),
            ("a-u-t-h", "auth"),
            ("nothing alike", "qjxz"),
            ("", "auth"),
        ],
    )
    def test_always_returns_a_float_in_unit_range(self, text, query):
        score = compute_relevance(text, query)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
