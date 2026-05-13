import math

import pytest

from plugins.grading.python.aggregation import (
    JudgeVote,
    AggregateResult,
    LEVEL_VALUES,
    compute_aggregate,
)


def test_level_values_match_spec():
    assert LEVEL_VALUES == {"full": 1.0, "partial": 0.5, "none": 0.0}


def test_q03_worked_example():
    """Spec §3.3 worked example.

    Universal axis weights: causal=0.35, temporal=0.25, completeness=0.25, deps=0.15
    Concept weights: C1=0.30, C2=0.25, C3=0.20, C4=0.25
    Per-concept scores from votes (back-computed to match spec):
      C1 (relevant=[causal]):                causal=full         -> 1.0
      C2 (relevant=[temporal,completeness]): both full           -> 1.0
      C3 (relevant=[causal,completeness]):   causal=partial,
                                              completeness=full  -> 0.7083
      C4 (relevant=[temporal,deps]):         temporal=full,
                                              deps=partial       -> 0.8125
    aggregate = 0.30*1 + 0.25*1 + 0.20*0.7083 + 0.25*0.8125 = 0.8948
    """
    axis_weights = {
        "causal": 0.35,
        "temporal": 0.25,
        "completeness": 0.25,
        "deps": 0.15,
    }
    concept_weights = {"C1": 0.30, "C2": 0.25, "C3": 0.20, "C4": 0.25}
    concept_relevant_axes = {
        "C1": ["causal"],
        "C2": ["temporal", "completeness"],
        "C3": ["causal", "completeness"],
        "C4": ["temporal", "deps"],
    }
    votes = [
        JudgeVote("C1", "causal", "full"),
        JudgeVote("C2", "temporal", "full"),
        JudgeVote("C2", "completeness", "full"),
        JudgeVote("C3", "causal", "partial"),
        JudgeVote("C3", "completeness", "full"),
        JudgeVote("C4", "temporal", "full"),
        JudgeVote("C4", "deps", "partial"),
    ]
    result = compute_aggregate(
        axis_weights=axis_weights,
        concept_weights=concept_weights,
        concept_relevant_axes=concept_relevant_axes,
        votes=votes,
    )
    assert math.isclose(result.per_concept_score["C1"], 1.0)
    assert math.isclose(result.per_concept_score["C2"], 1.0)
    assert math.isclose(result.per_concept_score["C3"], 0.425 / 0.60)
    assert math.isclose(result.per_concept_score["C4"], 0.325 / 0.40)
    assert math.isclose(result.aggregate, 0.8948, abs_tol=1e-3)
    assert math.isclose(result.aggregate_x10, 8.948, abs_tol=1e-2)


def test_all_full_gives_one():
    axis_weights = {"a": 0.5, "b": 0.5}
    concept_weights = {"C": 1.0}
    relevant = {"C": ["a", "b"]}
    votes = [JudgeVote("C", "a", "full"), JudgeVote("C", "b", "full")]
    r = compute_aggregate(
        axis_weights=axis_weights,
        concept_weights=concept_weights,
        concept_relevant_axes=relevant,
        votes=votes,
    )
    assert r.aggregate == 1.0 and r.aggregate_x10 == 10.0


def test_all_none_gives_zero():
    axis_weights = {"a": 1.0}
    concept_weights = {"C": 1.0}
    relevant = {"C": ["a"]}
    votes = [JudgeVote("C", "a", "none")]
    r = compute_aggregate(
        axis_weights=axis_weights,
        concept_weights=concept_weights,
        concept_relevant_axes=relevant,
        votes=votes,
    )
    assert r.aggregate == 0.0 and r.aggregate_x10 == 0.0


def test_missing_vote_raises():
    with pytest.raises(KeyError):
        compute_aggregate(
            axis_weights={"a": 1.0},
            concept_weights={"C": 1.0},
            concept_relevant_axes={"C": ["a"]},
            votes=[],
        )
