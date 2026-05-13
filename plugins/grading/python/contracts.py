"""Subagent output schemas per spec §6.2.

These models validate the *shape* of structured JSON returned by subagent
roles. They do not call any LLM; they are exercised against fixture JSON
by the contract tests.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from plugins.grading.python.schema import (
    AnswerQuality,
    ConceptOverlayEntry,
    Level,
)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class JudgeRow(_Strict):
    answer_id: str = Field(min_length=1)
    concept_id: str = Field(min_length=1)
    axis: str = Field(min_length=1)
    level: Level
    rationale: str = Field(min_length=1)


class JudgeOutput(_Strict):
    rows: list[JudgeRow] = Field(min_length=1)


class CriticRevisionKind(str, Enum):
    WEIGHT = "weight"
    CRITERION = "criterion"


class CriticWeightRevision(_Strict):
    kind: Literal[CriticRevisionKind.WEIGHT] = CriticRevisionKind.WEIGHT
    axis: str = Field(min_length=1)
    new_weight: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(min_length=1)


class CriticCriterionRevision(_Strict):
    kind: Literal[CriticRevisionKind.CRITERION] = CriticRevisionKind.CRITERION
    axis: str = Field(min_length=1)
    level: Level
    new_criterion: str = Field(min_length=1)
    rationale: str = Field(min_length=1)


CriticRevision = CriticWeightRevision | CriticCriterionRevision


class CriticOutput(_Strict):
    revisions: list[CriticRevision] = Field(min_length=1)
    rationale_summary: str = Field(min_length=1)


class MaterializeSeedAnswer(_Strict):
    answer_id: str = Field(min_length=1)
    quality: AnswerQuality
    text: str = Field(min_length=1)
    target_axis: str | None = None


class MaterializeSeedOutput(_Strict):
    seed_id: str = Field(min_length=1)
    concept_overlay: list[ConceptOverlayEntry] = Field(min_length=1)
    answers: list[MaterializeSeedAnswer] = Field(min_length=1)
    gold_coverage: dict[str, dict[str, dict[str, Level]]]

    def model_post_init(self, _ctx) -> None:
        # Axis-perturbation answers must declare target_axis; others must not.
        for a in self.answers:
            if a.quality is AnswerQuality.AXIS_PERTURBATION and not a.target_axis:
                raise ValueError(
                    f"answer {a.answer_id!r}: axis_perturbation requires target_axis"
                )
            if a.quality is not AnswerQuality.AXIS_PERTURBATION and a.target_axis:
                raise ValueError(
                    f"answer {a.answer_id!r}: non-perturbation must not set target_axis"
                )


class SeedGenSeed(_Strict):
    topic: str = Field(min_length=1)
    text: str = Field(min_length=1)
    rationale: str = Field(min_length=1)


class SeedGenOutput(_Strict):
    seeds: list[SeedGenSeed] = Field(min_length=1)
