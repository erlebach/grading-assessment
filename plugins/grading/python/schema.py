"""Pydantic models + invariant validators for every grading-plugin artifact.

Spec reference: docs/superpowers/specs/2026-05-13-grading-plugin-design.md §3.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


WEIGHT_EPSILON = 1e-6


class TypeName(str, Enum):
    DEFINITION = "DEFINITION"
    DISTINCTION = "DISTINCTION"
    MECHANISM = "MECHANISM"
    CLASSIFICATION = "CLASSIFICATION"
    ENUMERATION = "ENUMERATION"
    EXAMPLE_GENERATION = "EXAMPLE_GENERATION"
    ERROR_IDENTIFICATION = "ERROR_IDENTIFICATION"
    COMPARISON = "COMPARISON"
    APPLICATION = "APPLICATION"
    PROOF_OR_ARGUMENT = "PROOF_OR_ARGUMENT"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TypeCatalogEntry(_Strict):
    name: TypeName
    description: str = Field(min_length=1)
    candidate_axes: list[str] = Field(min_length=1)

    @field_validator("candidate_axes")
    @classmethod
    def axes_nonempty_strings(cls, v: list[str]) -> list[str]:
        if any((not isinstance(a, str)) or not a.strip() for a in v):
            raise ValueError("candidate_axes entries must be non-empty strings")
        if len(set(v)) != len(v):
            raise ValueError("candidate_axes must be unique within a type")
        return v


class TypeCatalog(_Strict):
    types: list[TypeCatalogEntry] = Field(min_length=1)

    @field_validator("types")
    @classmethod
    def names_unique(cls, v: list[TypeCatalogEntry]) -> list[TypeCatalogEntry]:
        names = [t.name for t in v]
        if len(set(names)) != len(names):
            raise ValueError("type names must be unique")
        return v


class ScoreLevelEntry(_Strict):
    value: float
    criterion: str = Field(min_length=1)


class ScoreLevels(_Strict):
    full: ScoreLevelEntry
    partial: ScoreLevelEntry
    none: ScoreLevelEntry


class AxisDef(_Strict):
    name: str = Field(min_length=1)
    description: str = ""
    weight: float = Field(ge=0.0)
    score_levels: ScoreLevels


class Aggregate(_Strict):
    method: str = Field(min_length=1)
    out_of: float = Field(gt=0.0)


class UniversalRubricStatus(str, Enum):
    FROZEN = "frozen"
    WARNING_TEST_MARGINAL = "warning_test_marginal"
    FAILED_TO_CONVERGE = "failed_to_converge"


class UniversalRubric(_Strict):
    type: TypeName
    status: UniversalRubricStatus
    axes: list[AxisDef] = Field(min_length=1)
    aggregate: Aggregate


def validate_universal_rubric(raw: dict) -> UniversalRubric:
    """Apply §3.6 first bullet's invariants.

    Returns the validated model. Raises ValueError with a useful message on
    any invariant violation.
    """
    rubric = UniversalRubric.model_validate(raw)

    names = [a.name for a in rubric.axes]
    if len(set(names)) != len(names):
        raise ValueError(f"duplicate axis names: {names}")

    total = sum(a.weight for a in rubric.axes)
    if abs(total - 1.0) > WEIGHT_EPSILON:
        raise ValueError(f"axis weights must sum to 1.0; got {total}")

    for axis in rubric.axes:
        sl = axis.score_levels
        if not (sl.full.value > sl.partial.value > sl.none.value):
            raise ValueError(
                f"axis {axis.name!r}: score_levels not monotone "
                f"(full={sl.full.value}, partial={sl.partial.value}, none={sl.none.value})"
            )

    return rubric


class ConceptOverlayEntry(_Strict):
    id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    weight: float = Field(ge=0.0)
    relevant_axes: list[str] = Field(min_length=1)


class PerQuestionRubricStatus(str, Enum):
    FROZEN = "frozen"
    DEGRADED = "degraded"


class PerQuestionRubric(_Strict):
    question_id: str = Field(min_length=1)
    course: str = Field(min_length=1)
    type: TypeName
    universal_rubric_ref: str = Field(min_length=1)
    concept_overlay: list[ConceptOverlayEntry] = Field(min_length=1)
    status: PerQuestionRubricStatus


def validate_per_question_rubric(
    raw: dict,
    *,
    universal: UniversalRubric,
) -> PerQuestionRubric:
    """Apply §3.6 second bullet's invariants."""
    pqr = PerQuestionRubric.model_validate(raw)

    if pqr.type != universal.type:
        raise ValueError(
            f"type mismatch: per-question rubric says {pqr.type}, "
            f"universal rubric says {universal.type}"
        )

    ids = [c.id for c in pqr.concept_overlay]
    if len(set(ids)) != len(ids):
        raise ValueError(f"duplicate concept ids: {ids}")

    total = sum(c.weight for c in pqr.concept_overlay)
    if abs(total - 1.0) > WEIGHT_EPSILON:
        raise ValueError(f"concept weights must sum to 1.0; got {total}")

    universal_axis_names = {a.name for a in universal.axes}
    for c in pqr.concept_overlay:
        if not c.relevant_axes:
            raise ValueError(f"concept {c.id!r}: relevant_axes empty")
        bad = set(c.relevant_axes) - universal_axis_names
        if bad:
            raise ValueError(
                f"concept {c.id!r}: relevant_axes {sorted(bad)} not in universal axes"
            )

    return pqr


class Level(str, Enum):
    FULL = "full"
    PARTIAL = "partial"
    NONE = "none"


class AnswerGrade(_Strict):
    answer_id: str = Field(min_length=1)
    per_concept: dict[str, dict[str, Level]]
    aggregate: float = Field(ge=0.0, le=1.0)
    aggregate_x10: float = Field(ge=0.0, le=10.0)
    target_axis_drop_observed: float | None = None


class GradesSummary(_Strict):
    mean_by_quality: dict[str, float]
    ordering_preserved: bool
    bands_satisfied: bool
    axis_discrimination_passed: bool


class Grades(_Strict):
    question_id: str = Field(min_length=1)
    rubric_ref: str = Field(min_length=1)
    universal_rubric_ref: str = Field(min_length=1)
    grades: list[AnswerGrade] = Field(min_length=1)
    summary: GradesSummary


def validate_grade(
    raw: dict,
    *,
    rubric: PerQuestionRubric,
    universal: UniversalRubric,
) -> Grades:
    """Apply §3.6 third bullet's invariants."""
    try:
        grades = Grades.model_validate(raw)
    except ValidationError as exc:
        err_str = str(exc)
        # Pydantic enum errors don't include "level" in the message;
        # re-raise with a clearer message so tests can match on "level".
        if "enum" in err_str or "Input should be" in err_str:
            raise ValueError(
                f"invalid level value in grades (must be 'full', 'partial', or 'none'): {exc}"
            ) from exc
        raise ValueError(str(exc)) from exc

    if grades.question_id != rubric.question_id:
        raise ValueError(
            f"question_id mismatch: grades={grades.question_id}, "
            f"rubric={rubric.question_id}"
        )

    expected_pairs: set[tuple[str, str]] = set()
    for c in rubric.concept_overlay:
        for axis in c.relevant_axes:
            expected_pairs.add((c.id, axis))

    for g in grades.grades:
        present_pairs: set[tuple[str, str]] = set()
        for concept_id, axis_map in g.per_concept.items():
            for axis_name in axis_map:
                present_pairs.add((concept_id, axis_name))
        missing = expected_pairs - present_pairs
        if missing:
            raise ValueError(
                f"answer {g.answer_id!r}: missing (concept,axis) pairs: {sorted(missing)}"
            )
        extras = present_pairs - expected_pairs
        if extras:
            raise ValueError(
                f"answer {g.answer_id!r}: unexpected (concept,axis) pairs: {sorted(extras)}"
            )

        if abs(g.aggregate_x10 - g.aggregate * 10.0) > WEIGHT_EPSILON:
            raise ValueError(
                f"answer {g.answer_id!r}: aggregate_x10 ({g.aggregate_x10}) "
                f"!= aggregate ({g.aggregate}) * 10"
            )

    return grades


class UserReview(_Strict):
    approved: bool
    note: str | None = None


class SeedQuestion(_Strict):
    seed_id: str = Field(min_length=1)
    type: TypeName
    topic: str = Field(min_length=1)
    source: str = Field(min_length=1)
    text: str = Field(min_length=1)
    generated_by: str = Field(min_length=1)
    user_review: UserReview


class Question(_Strict):
    question_id: str = Field(min_length=1)
    course: str = Field(min_length=1)
    type: TypeName
    text: str = Field(min_length=1)
    sources: list[str] = Field(default_factory=list)
    notes: str | None = None


class SourceFormat(str, Enum):
    PDF = "pdf"
    MARKDOWN = "markdown"


class ExtractionMeta(_Strict):
    role: str
    tier: str
    ts: str


class SourceMeta(_Strict):
    format: SourceFormat
    courses: list[str]
    topics: list[str]
    extraction: ExtractionMeta | None
    content_sha: str = Field(min_length=8)
    figure_count: int = Field(ge=0)
    page_count: int = Field(ge=0)
