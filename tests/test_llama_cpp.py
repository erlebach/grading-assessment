"""Tests for llama.cpp LLM provider integration.

This module tests the llama.cpp provider configuration and initialization.
Tests include configuration loading, provider initialization, error handling,
and basic inference capabilities.
"""

import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

import pytest

from config.llm_config import configure_llm, load_env_config


@pytest.fixture
def mock_llamacpp_model_file():
    """Create a temporary mock model file for testing."""
    with TemporaryDirectory() as tmpdir:
        model_path = Path(tmpdir) / "test_model.gguf"
        model_path.write_text("mock model data")
        yield str(model_path)


@pytest.fixture
def mock_env_with_llamacpp(mock_llamacpp_model_file):
    """Mock environment variables for llama.cpp configuration."""
    original_env = os.environ.copy()
    os.environ["LLAMACPP_MODEL_PATH"] = mock_llamacpp_model_file
    os.environ["LLAMACPP_N_CTX"] = "2048"
    os.environ["LLAMACPP_N_GPU_LAYERS"] = "0"
    os.environ["LLAMACPP_TEMPERATURE"] = "0.7"
    os.environ["LLAMACPP_MAX_TOKENS"] = "512"
    yield
    os.environ.clear()
    os.environ.update(original_env)


def test_load_env_config_llamacpp_defaults():
    """Test loading llama.cpp configuration with default values."""
    # Save and clear any existing llamacpp env vars
    saved_env = {}
    for key in list(os.environ.keys()):
        if key.startswith("LLAMACPP_"):
            saved_env[key] = os.environ[key]
            del os.environ[key]

    try:
        # Mock load_dotenv to prevent loading from ~/.env
        with patch("config.llm_config.load_dotenv"):
            config = load_env_config()

            # Check default values
            assert "llamacpp_model_path" in config
            assert config["llamacpp_model_path"] == ""
            assert config["llamacpp_n_ctx"] == 2048
            assert config["llamacpp_n_gpu_layers"] == 0
            assert config["llamacpp_temperature"] == 0.7
            assert config["llamacpp_max_tokens"] == 512
            print("✓ test_load_env_config_llamacpp_defaults passed")
    finally:
        # Restore saved environment
        for key, value in saved_env.items():
            os.environ[key] = value


def test_load_env_config_llamacpp_custom(mock_env_with_llamacpp):
    """Test loading llama.cpp configuration with custom values."""
    config = load_env_config()

    # Check custom values from environment
    assert config["llamacpp_model_path"] != ""
    assert Path(config["llamacpp_model_path"]).exists()
    assert config["llamacpp_n_ctx"] == 2048
    assert config["llamacpp_n_gpu_layers"] == 0
    assert config["llamacpp_temperature"] == 0.7
    assert config["llamacpp_max_tokens"] == 512
    print("✓ test_load_env_config_llamacpp_custom passed")


def test_configure_llm_llamacpp_missing_package():
    """Test that configure_llm raises error when llama.cpp package is missing."""
    with patch("config.llm_config.LlamaCPP", None):
        with pytest.raises(ImportError, match="LlamaCPP provider requested but llama-cpp package is not available"):
            configure_llm("llamacpp", model="/path/to/model.gguf")
    print("✓ test_configure_llm_llamacpp_missing_package passed")


def test_configure_llm_llamacpp_missing_model_path():
    """Test that configure_llm raises error when model path is not provided."""
    # Mock LlamaCPP and load_env_config to return empty model path
    mock_config = {
        "llamacpp_model_path": "",
        "llamacpp_n_ctx": 2048,
        "llamacpp_n_gpu_layers": 0,
        "llamacpp_temperature": 0.7,
        "llamacpp_max_tokens": 512,
    }

    with patch("config.llm_config.LlamaCPP", MagicMock()):
        with patch("config.llm_config.load_env_config", return_value=mock_config):
            with pytest.raises(ValueError, match="LLAMACPP_MODEL_PATH must be set"):
                configure_llm("llamacpp")

    print("✓ test_configure_llm_llamacpp_missing_model_path passed")


@patch("config.llm_config.LlamaCPP", MagicMock())
def test_configure_llm_llamacpp_nonexistent_model():
    """Test that configure_llm raises error when model file doesn't exist."""
    nonexistent_path = "/nonexistent/path/to/model.gguf"

    with pytest.raises(FileNotFoundError, match="LlamaCPP model file not found"):
        configure_llm("llamacpp", model=nonexistent_path)

    print("✓ test_configure_llm_llamacpp_nonexistent_model passed")


@patch("config.llm_config.LlamaCPP")
def test_configure_llm_llamacpp_success(mock_llamacpp_class, mock_env_with_llamacpp):
    """Test successful llama.cpp provider initialization."""
    # Create a mock LlamaCPP instance
    mock_llm_instance = MagicMock()
    mock_llamacpp_class.return_value = mock_llm_instance

    # Get the model path from environment
    model_path = os.environ["LLAMACPP_MODEL_PATH"]

    # Configure LLM
    result = configure_llm("llamacpp")

    # Verify LlamaCPP was called with correct parameters
    mock_llamacpp_class.assert_called_once_with(
        model_path=model_path,
        temperature=0.7,
        model_kwargs={
            "n_ctx": 2048,
            "n_gpu_layers": 0,
        },
        max_new_tokens=512,
    )

    # Verify the returned instance
    assert result == mock_llm_instance
    print("✓ test_configure_llm_llamacpp_success passed")


@patch("config.llm_config.LlamaCPP")
def test_configure_llm_llamacpp_with_custom_model_path(mock_llamacpp_class, mock_llamacpp_model_file):
    """Test llama.cpp provider initialization with custom model path."""
    # Create a mock LlamaCPP instance
    mock_llm_instance = MagicMock()
    mock_llamacpp_class.return_value = mock_llm_instance

    # Configure LLM with explicit model path
    result = configure_llm("llamacpp", model=mock_llamacpp_model_file)

    # Verify LlamaCPP was called with the custom path
    assert mock_llamacpp_class.call_args[1]["model_path"] == mock_llamacpp_model_file
    assert result == mock_llm_instance
    print("✓ test_configure_llm_llamacpp_with_custom_model_path passed")


@patch("config.llm_config.LlamaCPP")
def test_configure_llm_llamacpp_parameters(mock_llamacpp_class, mock_env_with_llamacpp):
    """Test that llama.cpp is initialized with correct parameters."""
    # Set custom environment variables
    os.environ["LLAMACPP_N_CTX"] = "4096"
    os.environ["LLAMACPP_N_GPU_LAYERS"] = "35"
    os.environ["LLAMACPP_TEMPERATURE"] = "0.9"
    os.environ["LLAMACPP_MAX_TOKENS"] = "1024"

    mock_llm_instance = MagicMock()
    mock_llamacpp_class.return_value = mock_llm_instance

    result = configure_llm("llamacpp")

    # Verify all parameters were passed correctly
    call_kwargs = mock_llamacpp_class.call_args[1]
    assert call_kwargs["temperature"] == 0.9
    assert call_kwargs["max_new_tokens"] == 1024
    assert call_kwargs["model_kwargs"]["n_ctx"] == 4096
    assert call_kwargs["model_kwargs"]["n_gpu_layers"] == 35

    print("✓ test_configure_llm_llamacpp_parameters passed")


@patch("config.llm_config.LlamaCPP")
def test_configure_llm_llamacpp_inference_mock(mock_llamacpp_class, mock_env_with_llamacpp):
    """Test basic inference with mocked llama.cpp provider."""
    # Create a mock LlamaCPP instance with a complete method
    mock_llm_instance = MagicMock()
    mock_llm_instance.complete.return_value = MagicMock(text="This is a test response.")
    mock_llamacpp_class.return_value = mock_llm_instance

    # Configure and test
    llm = configure_llm("llamacpp")

    # Test completion
    response = llm.complete("Test prompt")
    assert response.text == "This is a test response."
    mock_llm_instance.complete.assert_called_once_with("Test prompt")

    print("✓ test_configure_llm_llamacpp_inference_mock passed")


def test_llamacpp_config_type_conversion():
    """Test that environment variables are converted to correct types."""
    # Set string values in environment
    os.environ["LLAMACPP_N_CTX"] = "3072"
    os.environ["LLAMACPP_N_GPU_LAYERS"] = "20"
    os.environ["LLAMACPP_TEMPERATURE"] = "0.8"
    os.environ["LLAMACPP_MAX_TOKENS"] = "256"

    config = load_env_config()

    # Verify types are correct
    assert isinstance(config["llamacpp_n_ctx"], int)
    assert isinstance(config["llamacpp_n_gpu_layers"], int)
    assert isinstance(config["llamacpp_temperature"], float)
    assert isinstance(config["llamacpp_max_tokens"], int)

    # Verify values
    assert config["llamacpp_n_ctx"] == 3072
    assert config["llamacpp_n_gpu_layers"] == 20
    assert config["llamacpp_temperature"] == 0.8
    assert config["llamacpp_max_tokens"] == 256

    print("✓ test_llamacpp_config_type_conversion passed")


@pytest.mark.skipif(
    not os.getenv("LLAMACPP_MODEL_PATH") or not Path(os.getenv("LLAMACPP_MODEL_PATH", "")).exists(),
    reason="LLAMACPP_MODEL_PATH not set or model file doesn't exist"
)
def test_llamacpp_real_inference():
    """Integration test: Real llama.cpp inference (only runs if model is available)."""
    import time

    print("\n" + "=" * 60)
    print("REAL INTEGRATION TEST - Loading actual model")
    print("=" * 60)

    # Get model path from environment
    model_path = os.getenv("LLAMACPP_MODEL_PATH")
    print(f"Model path: {model_path}")

    # Try to initialize the real LlamaCPP
    print("Initializing LlamaCPP (may take 30-60 seconds)...")
    start = time.time()

    try:
        llm = configure_llm("llamacpp")
        load_time = time.time() - start
        print(f"✓ Model loaded in {load_time:.2f}s")
    except Exception as e:
        pytest.fail(f"Failed to initialize LlamaCPP: {e}")

    # Try a simple inference
    print("Testing inference with simple prompt...")
    test_prompt = "What is 2+2? Answer with just the number:"
    start = time.time()

    try:
        response = llm.complete(test_prompt)
        inference_time = time.time() - start
        print(f"✓ Response generated in {inference_time:.2f}s")
        print(f"Response: {response.text[:100]}")

        # Verify we got some response
        assert response.text, "Response should not be empty"
        assert len(response.text) > 0, "Response should have content"

        print("✓ test_llamacpp_real_inference passed")
    except Exception as e:
        pytest.fail(f"Failed during inference: {e}")


if __name__ == "__main__":
    # Run all tests
    print("\nRunning llama.cpp integration tests...\n")

    test_load_env_config_llamacpp_defaults()

    # Tests requiring fixtures need to be run with pytest
    print("\nNote: Some tests require pytest fixtures and should be run with:")
    print("  pytest tests/test_llama_cpp.py -v")
    print("\nTo run with real model (integration test):")
    print("  1. Set LLAMACPP_MODEL_PATH=/path/to/your/model.gguf")
    print("  2. pytest tests/test_llama_cpp.py::test_llamacpp_real_inference -v -s")
    print("\n✓ Basic tests passed. Run with pytest for full test suite.")
