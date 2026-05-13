import pytest

from plugins.grading.python.contracts import SeedGenOutput


def test_seed_gen_accepts_good():
    raw = {
        "seeds": [
            {"topic": "physics", "text": "How does evaporation cool a liquid?", "rationale": "..."},
        ]
    }
    SeedGenOutput.model_validate(raw)


def test_seed_gen_rejects_missing_topic():
    raw = {"seeds": [{"text": "...", "rationale": "..."}]}
    with pytest.raises(Exception):
        SeedGenOutput.model_validate(raw)
