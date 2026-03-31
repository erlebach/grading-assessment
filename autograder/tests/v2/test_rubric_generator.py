# tests/v2/test_rubric_generator.py
import json
from unittest.mock import MagicMock
import pytest
from v2.rubric_generator import RubricGeneratorV2, RubricGeneratorConfig
from v2.models import RubricV2, SyntheticAnswer, AnswerQuality


MINIMAL_LLM_RESPONSE = json.dumps({
    "criteria": [
        {
            "criterion_id": "zero_role",
            "points": 2,
            "checks": [
                {
                    "check_id": "c1",
                    "check_type": "definition",
                    "concept": "interval scale zero is arbitrary",
                    "points": 2,
                    "precision_levels": {
                        "full": "Names convention, states not absence of quantity",
                        "partial": "States zero is arbitrary without specifics",
                        "none": "Absent or wrong",
                    },
                }
            ],
        }
    ]
})


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.complete.return_value = MagicMock(text=MINIMAL_LLM_RESPONSE)
    return llm


@pytest.fixture
def synthetic_answers():
    return [
        SyntheticAnswer(question_id="q01", quality=AnswerQuality.GOOD, variant=1, text="Good answer text."),
        SyntheticAnswer(question_id="q01", quality=AnswerQuality.LESS_GOOD, variant=1, text="Less good text."),
        SyntheticAnswer(question_id="q01", quality=AnswerQuality.WRONG, variant=1, text="Wrong answer text."),
    ]


def test_generate_rubric_returns_rubric_v2(mock_llm, synthetic_answers):
    gen = RubricGeneratorV2(llm=mock_llm, config=RubricGeneratorConfig())
    rubric = gen.generate(
        question_id="q01",
        question_text="Why can't you compute ratios on Celsius?",
        question_type="mechanism",
        source_material="Celsius uses arbitrary zero...",
        synthetic_answers=synthetic_answers,
        version=1,
    )
    assert isinstance(rubric, RubricV2)
    assert rubric.question_id == "q01"
    assert rubric.version == 1


def test_generate_rubric_has_at_least_one_criterion(mock_llm, synthetic_answers):
    gen = RubricGeneratorV2(llm=mock_llm, config=RubricGeneratorConfig())
    rubric = gen.generate(
        question_id="q01",
        question_text="Q text",
        question_type="mechanism",
        source_material="source",
        synthetic_answers=synthetic_answers,
        version=1,
    )
    assert len(rubric.criteria) >= 1


def test_generate_rubric_calls_llm_once(mock_llm, synthetic_answers):
    gen = RubricGeneratorV2(llm=mock_llm, config=RubricGeneratorConfig())
    gen.generate("q01", "Q", "mechanism", "source", synthetic_answers, version=1)
    assert mock_llm.complete.call_count == 1
