"""Tests for grading_pipeline/deduplication.py (T2.4).

All tests derived from T2.4 specification in TASK_LIST.md:
  - deduplicate_checks() returns a new Rubric (does not mutate input)
  - No duplicates → all checks preserved, 0 removed
  - Obvious duplicates → second occurrence removed, first kept
  - Subtle (semantically similar) duplicates → removed by similarity_fn
  - Similar but distinct checks → both preserved
  - Returns metadata with count of duplicates removed
  - Works with 10+ check sets
  - similarity_fn is injectable (default is LLM-based)

Spec references:
  TASK_LIST.md §T2.4
  grading_pipeline/models.py  (Check, Rubric)
"""

import pytest

from grading_pipeline.deduplication import deduplicate_checks, DeduplicationResult
from grading_pipeline.models import Check, CheckCategory, Rubric


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _check(idx: int, text: str, category: str = "semantic") -> Check:
    return Check(
        id=f"q01_c{idx}",
        text=text,
        category=CheckCategory(category),
        weight=1.0,
        question_id="q01",
    )


def _rubric(*checks: Check) -> Rubric:
    return Rubric(
        id="q01_rubric",
        question_id="q01",
        title="Test Rubric",
        description="",
        checks=list(checks),
        dimensions=[],
        total_points=10.0,
        version=1,
    )


# Simple exact-text similarity function for deterministic testing (no LLM needed)
def _exact_similarity(a: str, b: str) -> float:
    """Returns 1.0 if texts are identical, 0.0 otherwise."""
    return 1.0 if a.strip().lower() == b.strip().lower() else 0.0


def _always_duplicate(a: str, b: str) -> float:
    """Returns 1.0 for any pair (for testing high-confidence removal)."""
    return 1.0


def _never_duplicate(a: str, b: str) -> float:
    """Returns 0.0 for any pair (for testing no removal)."""
    return 0.0


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------

class TestDeduplicationResult:
    def test_result_has_rubric(self):
        rubric = _rubric(_check(1, "Student defines X correctly"))
        result = deduplicate_checks(rubric, similarity_fn=_exact_similarity)
        assert isinstance(result, DeduplicationResult)
        assert isinstance(result.rubric, Rubric)

    def test_result_has_metadata_with_removed_count(self):
        rubric = _rubric(_check(1, "Student defines X correctly"))
        result = deduplicate_checks(rubric, similarity_fn=_exact_similarity)
        assert hasattr(result, "duplicates_removed")
        assert isinstance(result.duplicates_removed, int)

    def test_result_has_removed_pairs(self):
        rubric = _rubric(_check(1, "Student defines X correctly"))
        result = deduplicate_checks(rubric, similarity_fn=_exact_similarity)
        assert hasattr(result, "removed_pairs")
        assert isinstance(result.removed_pairs, list)


# ---------------------------------------------------------------------------
# No duplicates
# ---------------------------------------------------------------------------

class TestNoDuplicates:
    def test_empty_rubric_returns_empty(self):
        rubric = _rubric()
        result = deduplicate_checks(rubric, similarity_fn=_exact_similarity)
        assert result.rubric.checks == []
        assert result.duplicates_removed == 0

    def test_single_check_unchanged(self):
        c = _check(1, "Student defines 'object' correctly")
        rubric = _rubric(c)
        result = deduplicate_checks(rubric, similarity_fn=_exact_similarity)
        assert len(result.rubric.checks) == 1
        assert result.duplicates_removed == 0

    def test_distinct_checks_all_preserved(self):
        checks = [
            _check(1, "Student defines 'object' correctly"),
            _check(2, "Student provides a valid example"),
            _check(3, "Answer is grammatically correct"),
        ]
        rubric = _rubric(*checks)
        result = deduplicate_checks(rubric, similarity_fn=_exact_similarity)
        assert len(result.rubric.checks) == 3
        assert result.duplicates_removed == 0

    def test_never_duplicate_fn_preserves_all(self):
        checks = [_check(i, f"Check {i}") for i in range(1, 6)]
        rubric = _rubric(*checks)
        result = deduplicate_checks(rubric, similarity_fn=_never_duplicate)
        assert len(result.rubric.checks) == 5
        assert result.duplicates_removed == 0


# ---------------------------------------------------------------------------
# Obvious duplicates (identical text)
# ---------------------------------------------------------------------------

class TestObviousDuplicates:
    def test_exact_duplicate_second_removed(self):
        c1 = _check(1, "Student defines 'object' correctly")
        c2 = _check(2, "Student defines 'object' correctly")  # exact duplicate
        rubric = _rubric(c1, c2)
        result = deduplicate_checks(rubric, similarity_fn=_exact_similarity)
        assert len(result.rubric.checks) == 1
        assert result.rubric.checks[0].id == "q01_c1"  # first occurrence kept
        assert result.duplicates_removed == 1

    def test_first_occurrence_always_kept(self):
        c1 = _check(1, "same text")
        c2 = _check(2, "same text")
        c3 = _check(3, "same text")
        rubric = _rubric(c1, c2, c3)
        result = deduplicate_checks(rubric, similarity_fn=_exact_similarity)
        assert len(result.rubric.checks) == 1
        assert result.rubric.checks[0].id == "q01_c1"
        assert result.duplicates_removed == 2

    def test_duplicate_count_in_metadata(self):
        checks = [_check(i, "same text") for i in range(1, 6)]
        rubric = _rubric(*checks)
        result = deduplicate_checks(rubric, similarity_fn=_exact_similarity)
        assert result.duplicates_removed == 4

    def test_non_duplicate_checks_preserved_alongside_deduped(self):
        c1 = _check(1, "unique check A")
        c2 = _check(2, "duplicate check")
        c3 = _check(3, "duplicate check")
        c4 = _check(4, "unique check B")
        rubric = _rubric(c1, c2, c3, c4)
        result = deduplicate_checks(rubric, similarity_fn=_exact_similarity)
        ids = [c.id for c in result.rubric.checks]
        assert "q01_c1" in ids
        assert "q01_c2" in ids
        assert "q01_c3" not in ids
        assert "q01_c4" in ids
        assert result.duplicates_removed == 1


# ---------------------------------------------------------------------------
# Subtle duplicates (high similarity but not identical text)
# ---------------------------------------------------------------------------

class TestSubtleDuplicates:
    def test_high_similarity_triggers_removal(self):
        """similarity_fn always returns 1.0 → all pairs are duplicates."""
        c1 = _check(1, "Student correctly identifies the concept")
        c2 = _check(2, "Student identifies the concept correctly")
        rubric = _rubric(c1, c2)
        result = deduplicate_checks(rubric, similarity_fn=_always_duplicate)
        assert len(result.rubric.checks) == 1
        assert result.duplicates_removed == 1

    def test_threshold_boundary_below_keeps_both(self):
        """Below threshold → both checks kept."""
        def _below_threshold(a: str, b: str) -> float:
            return 0.5  # well below typical 0.85 threshold

        c1 = _check(1, "Check A")
        c2 = _check(2, "Check B")
        rubric = _rubric(c1, c2)
        result = deduplicate_checks(rubric, similarity_fn=_below_threshold, threshold=0.85)
        assert len(result.rubric.checks) == 2
        assert result.duplicates_removed == 0

    def test_threshold_boundary_at_threshold_removes(self):
        """At or above threshold → second check removed."""
        def _at_threshold(a: str, b: str) -> float:
            return 0.85

        c1 = _check(1, "Check A")
        c2 = _check(2, "Check B")
        rubric = _rubric(c1, c2)
        result = deduplicate_checks(rubric, similarity_fn=_at_threshold, threshold=0.85)
        assert len(result.rubric.checks) == 1
        assert result.duplicates_removed == 1


# ---------------------------------------------------------------------------
# Similar but distinct checks
# ---------------------------------------------------------------------------

class TestDistinctChecks:
    def test_similar_distinct_checks_both_preserved(self):
        """Checks that are related but NOT duplicates should both survive."""
        c1 = _check(1, "Student defines 'class' correctly")
        c2 = _check(2, "Student defines 'object' correctly")
        rubric = _rubric(c1, c2)
        # exact_similarity returns 0 for these (different texts)
        result = deduplicate_checks(rubric, similarity_fn=_exact_similarity)
        assert len(result.rubric.checks) == 2
        assert result.duplicates_removed == 0


# ---------------------------------------------------------------------------
# Mutation safety
# ---------------------------------------------------------------------------

class TestMutationSafety:
    def test_original_rubric_not_mutated(self):
        c1 = _check(1, "same text")
        c2 = _check(2, "same text")
        rubric = _rubric(c1, c2)
        original_count = len(rubric.checks)
        deduplicate_checks(rubric, similarity_fn=_exact_similarity)
        assert len(rubric.checks) == original_count  # input unchanged

    def test_returns_new_rubric_instance(self):
        c = _check(1, "unique check")
        rubric = _rubric(c)
        result = deduplicate_checks(rubric, similarity_fn=_exact_similarity)
        assert result.rubric is not rubric


# ---------------------------------------------------------------------------
# Removed pairs metadata
# ---------------------------------------------------------------------------

class TestRemovedPairsMetadata:
    def test_removed_pairs_records_kept_and_removed_ids(self):
        c1 = _check(1, "same text")
        c2 = _check(2, "same text")
        rubric = _rubric(c1, c2)
        result = deduplicate_checks(rubric, similarity_fn=_exact_similarity)
        assert len(result.removed_pairs) == 1
        kept_id, removed_id = result.removed_pairs[0]
        assert kept_id == "q01_c1"
        assert removed_id == "q01_c2"

    def test_no_duplicates_gives_empty_pairs(self):
        rubric = _rubric(_check(1, "A"), _check(2, "B"))
        result = deduplicate_checks(rubric, similarity_fn=_exact_similarity)
        assert result.removed_pairs == []


# ---------------------------------------------------------------------------
# Scale test (10+ checks)
# ---------------------------------------------------------------------------

class TestScale:
    def test_ten_unique_checks_all_preserved(self):
        checks = [_check(i, f"Unique check text number {i}") for i in range(1, 11)]
        rubric = _rubric(*checks)
        result = deduplicate_checks(rubric, similarity_fn=_exact_similarity)
        assert len(result.rubric.checks) == 10
        assert result.duplicates_removed == 0

    def test_ten_identical_checks_only_first_kept(self):
        checks = [_check(i, "Identical check text") for i in range(1, 11)]
        rubric = _rubric(*checks)
        result = deduplicate_checks(rubric, similarity_fn=_exact_similarity)
        assert len(result.rubric.checks) == 1
        assert result.rubric.checks[0].id == "q01_c1"
        assert result.duplicates_removed == 9

    def test_mixed_ten_checks(self):
        checks = (
            [_check(i, "Duplicate text") for i in range(1, 6)]
            + [_check(i + 5, f"Unique text {i}") for i in range(1, 6)]
        )
        rubric = _rubric(*checks)
        result = deduplicate_checks(rubric, similarity_fn=_exact_similarity)
        assert result.duplicates_removed == 4  # c2-c5 removed, c1 kept
        assert len(result.rubric.checks) == 6  # 1 from dupes + 5 unique
