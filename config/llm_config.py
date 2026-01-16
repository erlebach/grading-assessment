"""LLM provider configuration and abstraction.

This module provides a unified interface for configuring and accessing
different LLM providers (OpenAI, Anthropic) and embedding models.
Configuration is loaded from environment variables in $HOME/.env.

"""

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from llama_index.core import Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.anthropic import Anthropic
from llama_index.llms.gemini import Gemini
from llama_index.llms.ollama import Ollama
from llama_index.llms.openai import OpenAI


def load_env_config() -> dict[str, str]:
    """Load configuration from $HOME/.env file.

    Returns:
        Dictionary containing configuration values.

    """
    env_path = Path.home() / ".env"
    load_dotenv(env_path)

    return {
        "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
        "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY", ""),
        "gemini_api_key": os.getenv("GEMINI_API_KEY", ""),
        "lmql_backend": os.getenv("LMQL_BACKEND", "ollama"),
        "lmql_model": os.getenv("LMQL_MODEL", "gpt-oss:20b"),
        "ollama_base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        "embedding_provider": os.getenv("EMBEDDING_PROVIDER", "sentence-transformer"),
        "embedding_model": os.getenv(
            "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
        ),
    }


def configure_llm(provider: str = "ollama", model: str | None = None) -> Any:
    """Configure and return an LLM instance.

    Args:
        provider: LLM provider name ("openai", "anthropic", "gemini", or "ollama").
        model: Optional model name. If None, uses default for provider.

    Returns:
        Configured LLM instance.

    """
    config = load_env_config()

    if provider == "openai":
        api_key = config["openai_api_key"]
        model_name = model or "gpt-4o-mini"
        return OpenAI(model=model_name, api_key=api_key)
    elif provider == "anthropic":
        api_key = config["anthropic_api_key"]
        model_name = model or "claude-3-5-sonnet-20241022"
        return Anthropic(model=model_name, api_key=api_key)
    elif provider == "gemini":
        api_key = config["gemini_api_key"]
        model_name = model or "models/gemini-2.5-flash"
        return Gemini(model=model_name, api_key=api_key)
    elif provider == "ollama":
        model_name = model or config["lmql_model"]
        base_url = config["ollama_base_url"]
        return Ollama(model=model_name, base_url=base_url, request_timeout=120.0)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def configure_embedding(
    provider: str = "sentence-transformer", model: str | None = None
) -> Any:
    """Configure and return an embedding model instance.

    Args:
        provider: Embedding provider name ("openai", "sentence-transformer", or
            "huggingface").
        model: Optional model name. If None, uses default for provider.

    Returns:
        Configured embedding model instance.

    """
    config = load_env_config()

    if provider == "openai":
        api_key = config["openai_api_key"]
        model_name = model or config["embedding_model"]
        return OpenAIEmbedding(model=model_name, api_key=api_key)
    elif provider in ("sentence-transformer", "huggingface"):
        model_name = model or config["embedding_model"]
        return HuggingFaceEmbedding(model_name=model_name)
    else:
        raise ValueError(f"Unknown embedding provider: {provider}")


def setup_llamaindex_defaults() -> None:
    """Configure LlamaIndex global settings with default LLM and embedding.

    This sets up the default LLM and embedding model used by LlamaIndex
    throughout the application.

    """
    config = load_env_config()

    # Configure default LLM
    llm_provider = config["lmql_backend"]
    Settings.llm = configure_llm(llm_provider)

    # Configure default embedding
    embedding_provider = config["embedding_provider"]
    Settings.embed_model = configure_embedding(embedding_provider)


if __name__ == "__main__":
    # Test configuration loading
    print("Testing LLM configuration...")

    config = load_env_config()
    print(f"LMQL Backend: {config['lmql_backend']}")
    print(f"Embedding Provider: {config['embedding_provider']}")
    print(f"Embedding Model: {config['embedding_model']}")

    # Test LLM configuration
    print("\nConfiguring OpenAI LLM...")
    llm_openai = configure_llm("openai")
    print(f"✓ OpenAI LLM configured: {llm_openai.model}")

    print("\nConfiguring SentenceTransformer embedding model...")
    embed_model = configure_embedding("sentence-transformer")
    print(f"✓ Embedding model configured: {embed_model.model_name}")

    print("\nSetting up LlamaIndex defaults...")
    setup_llamaindex_defaults()
    print("✓ LlamaIndex defaults configured")
