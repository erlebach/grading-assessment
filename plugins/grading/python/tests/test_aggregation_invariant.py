import math

from hypothesis import given, settings
from hypothesis import strategies as st

from plugins.grading.python.aggregation import (
    JudgeVote,
    LEVEL_VALUES,
    compute_aggregate,
)


def _normalize(weights: list[float]) -> list[float]:
    total = sum(weights)
    return [w / total for w in weights] if total > 0 else [1.0 / len(weights)] * len(weights)


@st.composite
def rubric_strategy(draw):
    n_axes = draw(st.integers(min_value=1, max_value=5))
    n_concepts = draw(st.integers(min_value=1, max_value=5))

    raw_axis_weights = draw(st.lists(
        st.floats(min_value=0.01, max_value=1.0, allow_nan=False, allow_infinity=False),
        min_size=n_axes, max_size=n_axes,
    ))
    axis_names = [f"a{i}" for i in range(n_axes)]
    axis_weights = dict(zip(axis_names, _normalize(raw_axis_weights), strict=True))

    raw_concept_weights = draw(st.lists(
        st.floats(min_value=0.01, max_value=1.0, allow_nan=False, allow_infinity=False),
        min_size=n_concepts, max_size=n_concepts,
    ))
    concept_names = [f"c{i}" for i in range(n_concepts)]
    concept_weights = dict(zip(concept_names, _normalize(raw_concept_weights), strict=True))

    concept_relevant_axes: dict[str, list[str]] = {}
    for c in concept_names:
        k = draw(st.integers(min_value=1, max_value=n_axes))
        chosen = draw(st.lists(st.sampled_from(axis_names), min_size=k, max_size=k, unique=True))
        concept_relevant_axes[c] = chosen

    levels: list[JudgeVote] = []
    for c, axes in concept_relevant_axes.items():
        for a in axes:
            level = draw(st.sampled_from(list(LEVEL_VALUES.keys())))
            levels.append(JudgeVote(c, a, level))

    return axis_weights, concept_weights, concept_relevant_axes, levels


@given(rubric_strategy())
@settings(max_examples=200, deadline=None)
def test_aggregate_in_unit_interval(payload):
    axis_w, concept_w, rel, votes = payload
    r = compute_aggregate(
        axis_weights=axis_w,
        concept_weights=concept_w,
        concept_relevant_axes=rel,
        votes=votes,
    )
    assert 0.0 <= r.aggregate <= 1.0


@given(rubric_strategy())
@settings(max_examples=200, deadline=None)
def test_aggregate_x10_consistent(payload):
    axis_w, concept_w, rel, votes = payload
    r = compute_aggregate(
        axis_weights=axis_w,
        concept_weights=concept_w,
        concept_relevant_axes=rel,
        votes=votes,
    )
    assert math.isclose(r.aggregate_x10, r.aggregate * 10.0, abs_tol=1e-9)
    assert 0.0 <= r.aggregate_x10 <= 10.0


@given(rubric_strategy())
@settings(max_examples=200, deadline=None)
def test_no_nan(payload):
    axis_w, concept_w, rel, votes = payload
    r = compute_aggregate(
        axis_weights=axis_w,
        concept_weights=concept_w,
        concept_relevant_axes=rel,
        votes=votes,
    )
    assert not math.isnan(r.aggregate)
    for score in r.per_concept_score.values():
        assert not math.isnan(score)
