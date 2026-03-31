# tests/v2/test_answer_generator.py
from unittest.mock import MagicMock
import pytest
from v2.answer_generator import AnswerGenerator, AnswerGeneratorConfig
from v2.models import AnswerQuality, SyntheticAnswer


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.complete.return_value = MagicMock(text="A synthetic student answer.")
    return llm


@pytest.fixture
def config():
    return AnswerGeneratorConfig(
        variants_per_level=3,
        temperature=0.7,
    )


def test_generate_returns_nine_answers(mock_llm, config):
    gen = AnswerGenerator(llm=mock_llm, config=config)
    answers = gen.generate(
        question_id="q01",
        question_text="Why can't you compute ratios on Celsius?",
        question_type="mechanism",
        source_material="Celsius zero is the freezing point of water...",
    )
    assert len(answers) == 9


def test_generate_has_three_per_quality(mock_llm, config):
    gen = AnswerGenerator(llm=mock_llm, config=config)
    answers = gen.generate(
        question_id="q01",
        question_text="Why can't you compute ratios on Celsius?",
        question_type="mechanism",
        source_material="Celsius zero is the freezing point of water...",
    )
    for quality in AnswerQuality:
        subset = [a for a in answers if a.quality == quality]
        assert len(subset) == 3, f"Expected 3 {quality} answers, got {len(subset)}"


def test_generate_variants_numbered_1_to_3(mock_llm, config):
    gen = AnswerGenerator(llm=mock_llm, config=config)
    answers = gen.generate(
        question_id="q01",
        question_text="Why can't you compute ratios on Celsius?",
        question_type="mechanism",
        source_material="x",
    )
    for quality in AnswerQuality:
        variants = sorted(a.variant for a in answers if a.quality == quality)
        assert variants == [1, 2, 3]


def test_generate_returns_synthetic_answer_objects(mock_llm, config):
    gen = AnswerGenerator(llm=mock_llm, config=config)
    answers = gen.generate("q01", "Question text", "mechanism", "source")
    assert all(isinstance(a, SyntheticAnswer) for a in answers)
