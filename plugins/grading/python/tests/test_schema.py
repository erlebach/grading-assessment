import pytest

from plugins.grading.python.schema import TypeName, TypeCatalog, TypeCatalogEntry


def test_type_name_has_ten_values():
    assert len(list(TypeName)) == 10


def test_type_name_expected_set():
    expected = {
        "DEFINITION",
        "DISTINCTION",
        "MECHANISM",
        "CLASSIFICATION",
        "ENUMERATION",
        "EXAMPLE_GENERATION",
        "ERROR_IDENTIFICATION",
        "COMPARISON",
        "APPLICATION",
        "PROOF_OR_ARGUMENT",
    }
    assert {t.value for t in TypeName} == expected


def test_type_catalog_round_trip():
    raw = {
        "types": [
            {
                "name": "MECHANISM",
                "description": "How a process unfolds.",
                "candidate_axes": ["causal_chain_correctness", "temporal_ordering"],
            }
        ]
    }
    catalog = TypeCatalog.model_validate(raw)
    assert catalog.types[0].name is TypeName.MECHANISM
    assert catalog.types[0].candidate_axes == ["causal_chain_correctness", "temporal_ordering"]


def test_type_catalog_rejects_unknown_type():
    raw = {"types": [{"name": "MADE_UP", "description": "x", "candidate_axes": ["a"]}]}
    with pytest.raises(Exception):
        TypeCatalog.model_validate(raw)


def test_type_catalog_rejects_empty_axes():
    raw = {"types": [{"name": "MECHANISM", "description": "x", "candidate_axes": []}]}
    with pytest.raises(Exception):
        TypeCatalog.model_validate(raw)


from plugins.grading.python.schema import (
    ScoreLevels,
    AxisDef,
    UniversalRubric,
    UniversalRubricStatus,
    Aggregate,
)


def _good_axis(name="a", weight=1.0):
    return {
        "name": name,
        "description": "x",
        "weight": weight,
        "score_levels": {
            "full":    {"value": 1.0, "criterion": "all"},
            "partial": {"value": 0.5, "criterion": "some"},
            "none":    {"value": 0.0, "criterion": "none"},
        },
    }


def test_universal_rubric_round_trip():
    raw = {
        "type": "MECHANISM",
        "status": "frozen",
        "axes": [_good_axis("causal", 0.6), _good_axis("temporal", 0.4)],
        "aggregate": {"method": "weighted_mean", "out_of": 10.0},
    }
    r = UniversalRubric.model_validate(raw)
    assert r.type is TypeName.MECHANISM
    assert len(r.axes) == 2


def test_universal_rubric_status_values():
    assert {s.value for s in UniversalRubricStatus} == {
        "frozen",
        "warning_test_marginal",
        "failed_to_converge",
    }


def test_score_level_value_constants():
    sl = ScoreLevels.model_validate({
        "full":    {"value": 1.0, "criterion": "x"},
        "partial": {"value": 0.5, "criterion": "x"},
        "none":    {"value": 0.0, "criterion": "x"},
    })
    assert sl.full.value == 1.0 and sl.partial.value == 0.5 and sl.none.value == 0.0


from plugins.grading.python.schema import (
    SeedQuestion,
    Question,
    SourceMeta,
    SourceFormat,
)


def test_seed_question_minimal():
    sq = SeedQuestion.model_validate({
        "seed_id": "MECHANISM_001",
        "type": "MECHANISM",
        "topic": "physics",
        "source": "claude_knowledge",
        "text": "How does evaporation cool a liquid?",
        "generated_by": "claude-sonnet-4-6",
        "user_review": {"approved": True},
    })
    assert sq.user_review.approved is True


def test_question_minimal():
    q = Question.model_validate({
        "question_id": "Q03",
        "course": "data_quality",
        "type": "MECHANISM",
        "text": "Describe how schema drift develops.",
        "sources": ["data_quality_lecture_01"],
    })
    assert q.type is TypeName.MECHANISM


def test_source_meta_pdf():
    sm = SourceMeta.model_validate({
        "format": "pdf",
        "courses": ["data_quality"],
        "topics": ["data quality"],
        "extraction": {"role": "pdf_translator", "tier": "claude-opus-4-7", "ts": "2026-05-13T00:00:00Z"},
        "content_sha": "deadbeef" * 8,
        "figure_count": 5,
        "page_count": 12,
    })
    assert sm.format is SourceFormat.PDF


def test_source_meta_markdown_no_figures():
    sm = SourceMeta.model_validate({
        "format": "markdown",
        "courses": ["data_quality"],
        "topics": [],
        "extraction": None,
        "content_sha": "abc" * 22,
        "figure_count": 0,
        "page_count": 0,
    })
    assert sm.format is SourceFormat.MARKDOWN


from plugins.grading.python.schema import (
    RunMeta,
    RunConfig,
    CalibrationMeta,
    SyntheticAnswerSet,
    AnswerQuality,
    GoldConceptCoverage,
    TimelineEvent,
    TimelineEventType,
)


def test_run_meta_minimal():
    rm = RunMeta.model_validate({
        "run_id": "2026-05-13_13-15-00Z__abc1",
        "started_at": "2026-05-13T13:15:00Z",
        "ended_at": "2026-05-13T14:00:00Z",
        "git_sha": "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
        "git_dirty": False,
        "status": "success",
        "stages_run": ["calibrate_types"],
    })
    assert rm.run_id.startswith("2026-05-13")


def test_synthetic_answer_qualities():
    assert {q.value for q in AnswerQuality} == {
        "good", "less_good", "wrong", "axis_perturbation",
    }


def test_synthetic_answer_set_axis_perturbation_requires_target_axis():
    raw = {
        "question_id": "Q03",
        "answers": [
            {
                "answer_id": "ap_1",
                "quality": "axis_perturbation",
                "text": "...",
                "target_axis": None,
            }
        ],
    }
    with pytest.raises(Exception):
        SyntheticAnswerSet.model_validate(raw)


def test_synthetic_answer_set_good_requires_no_target_axis():
    SyntheticAnswerSet.model_validate({
        "question_id": "Q03",
        "answers": [
            {"answer_id": "good_1", "quality": "good", "text": "..."},
        ],
    })


def test_timeline_event_event_types():
    assert {e.value for e in TimelineEventType} == {
        "stage", "iteration", "subagent_dispatch",
        "python_helper_call", "gate_decision", "error",
    }


def test_timeline_event_round_trip():
    ev = TimelineEvent.model_validate({
        "ts": "2026-05-13T16:15:33.214Z",
        "event_type": "subagent_dispatch",
        "actor": "main_agent",
        "name": "materialize_seed:MECHANISM_seed_001",
        "phase": "start",
        "details": {"role": "materialize_seed"},
    })
    assert ev.phase == "start"


def test_run_meta_profile_defaults_to_none():
    rm = RunMeta.model_validate({
        "run_id": "2026-05-14_09-00-00Z__abc1",
        "started_at": "2026-05-14T09:00:00Z",
        "status": "success",
    })
    assert rm.profile is None


def test_run_meta_profile_accepts_string():
    rm = RunMeta.model_validate({
        "run_id": "2026-05-14_09-00-00Z__abc1",
        "started_at": "2026-05-14T09:00:00Z",
        "status": "success",
        "profile": "smoke",
    })
    assert rm.profile == "smoke"
