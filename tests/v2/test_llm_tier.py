# tests/v2/test_llm_tier.py
from unittest.mock import MagicMock, patch

import pytest

from config.llm_config import configure_llm_for_tier


@patch("config.llm_config.configure_llm", return_value=MagicMock())
def test_tier_foundational_returns_llm(mock_configure):
    llm = configure_llm_for_tier("foundational")
    assert llm is not None
    mock_configure.assert_called_once_with(provider="gemini", model="models/gemini-2.5-flash")


@patch("config.llm_config.configure_llm", return_value=MagicMock())
def test_tier_oss_returns_llm(mock_configure):
    llm = configure_llm_for_tier("oss")
    assert llm is not None
    mock_configure.assert_called_once_with(provider="ollama", model="gpt-oss:20b")


def test_tier_unknown_raises():
    with pytest.raises(ValueError, match="Unknown model_tier"):
        configure_llm_for_tier("bogus")
