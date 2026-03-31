# tests/v2/test_question_types.py
import pytest
from v2.question_types import QuestionType, get_prompt_template, QUESTION_TYPE_TEMPLATES


def test_all_ten_types_defined():
    assert len(QuestionType) == 10


def test_get_prompt_template_returns_nonempty_string():
    for qt in QuestionType:
        tmpl = get_prompt_template(qt)
        assert isinstance(tmpl, str) and len(tmpl) > 20, f"empty template for {qt}"


def test_template_contains_required_placeholders():
    # Every template must have {question} and {quality_level} placeholders
    for qt in QuestionType:
        tmpl = get_prompt_template(qt)
        assert "{question}" in tmpl, f"missing {{question}} in {qt}"


def test_unknown_type_raises():
    with pytest.raises(KeyError):
        get_prompt_template("nonexistent_type")
