"""Aggregation formula from spec §3.3.

Single source of truth: aggregate_x10 = aggregate * 10 with aggregate ∈ [0, 1].
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


LEVEL_VALUES: dict[str, float] = {"full": 1.0, "partial": 0.5, "none": 0.0}


@dataclass(frozen=True)
class JudgeVote:
    concept_id: str
    axis: str
    level: str   # "full" | "partial" | "none"


@dataclass(frozen=True)
class AggregateResult:
    per_concept_score: Mapping[str, float]
    aggregate: float       # [0, 1]
    aggregate_x10: float   # [0, 10]


def compute_aggregate(
    *,
    axis_weights: Mapping[str, float],
    concept_weights: Mapping[str, float],
    concept_relevant_axes: Mapping[str, list[str]],
    votes: list[JudgeVote],
) -> AggregateResult:
    """Apply §3.3 formula.

    Inputs are assumed pre-validated (weights non-negative, etc.).
    Raises KeyError if a (concept, axis) pair declared in
    `concept_relevant_axes` has no matching vote.
    """
    vote_by_pair: dict[tuple[str, str], str] = {
        (v.concept_id, v.axis): v.level for v in votes
    }

    per_concept: dict[str, float] = {}
    for concept_id, axes in concept_relevant_axes.items():
        num = 0.0
        den = 0.0
        for axis in axes:
            weight = axis_weights[axis]
            level = vote_by_pair[(concept_id, axis)]
            num += weight * LEVEL_VALUES[level]
            den += weight
        per_concept[concept_id] = num / den if den > 0 else 0.0

    total_num = sum(concept_weights[c] * per_concept[c] for c in concept_weights)
    total_den = sum(concept_weights[c] for c in concept_weights)
    agg = total_num / total_den if total_den > 0 else 0.0

    return AggregateResult(
        per_concept_score=per_concept,
        aggregate=agg,
        aggregate_x10=agg * 10.0,
    )
