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
from llama_index.llms.openai import OpenAI
from llama_index.core.llms import ChatMessage

# Ollama import is conditional - done lazily in configure_llm() to avoid proxy initialization errors
try:
    from llama_index.llms.ollama import Ollama
except ImportError:
    Ollama = None  # Will be handled in configure_llm() if needed

# LlamaCPP import is conditional - requires llama-index-llms-llama-cpp package
try:
    from llama_index.llms.llama_cpp import LlamaCPP
except ImportError:
    LlamaCPP = None  # Will be handled in configure_llm() if needed

# LlamaCPP GBNF Grammar - Define ONCE at module level to avoid duplication
# This prevents grammar parsing errors when configure_llm() is called multiple times
JSON_GRAMMAR = None
try:
    from llama_cpp import LlamaGrammar

    # Simplified grammar: just {"answer": "text"} with comprehensive character support
    # The model handles reasoning internally via proper chat template (harmony/Jinja)
    JSON_GRAMMAR_STR = 'ws ::= [ \\t\\n]*\nvalue ::= [-a-zA-Z0-9 \\t\\n.,!?;:()\\[\\]{}\'"/@#$%&*+=<>_~`\\\\]*\nroot ::= "{" ws "\\"answer\\"" ws ":" ws "\\"" value "\\"" ws "}"\n'
    JSON_GRAMMAR = LlamaGrammar.from_string(JSON_GRAMMAR_STR)
    print(f"✓ JSON_GRAMMAR compiled successfully at module load", flush=True)
except Exception as e:
    print(f"✗ Failed to compile JSON_GRAMMAR: {e}", flush=True)
    JSON_GRAMMAR = None


def gpt_oss_messages_to_prompt(messages: list[ChatMessage]) -> str:
    """Convert messages to gpt-oss chat template format.

    This template is used by the gpt-oss:20b model in Ollama.
    Format: <|start|>role<|message|>content<|end|>

    Args:
        messages: List of ChatMessage objects

    Returns:
        Formatted prompt string
    """
    prompt_parts = []

    for msg in messages:
        role = msg.role
        content = msg.content or ""

        if role == "system":
            prompt_parts.append(f"<|start|>system<|message|>{content}<|end|>")
        elif role == "user":
            prompt_parts.append(f"<|start|>user<|message|>{content}<|end|>")
        elif role == "assistant":
            prompt_parts.append(f"<|start|>assistant<|message|>{content}<|end|>")

    # Add the start of the assistant's response
    prompt_parts.append("<|start|>assistant<|message|>")

    return "\n".join(prompt_parts)


def load_env_config() -> dict[str, str]:
    """Load configuration from $HOME/.env file.

    Also exports Ollama-specific environment variables (like OLLAMA_NUM_PARALLEL)
    to the current process environment so Ollama server can read them.

    Returns:
        Dictionary containing configuration values.

    """
    env_path = Path.home() / ".env"
    load_dotenv(env_path)  # This loads all variables from .env into os.environ

    # Note: OLLAMA_NUM_PARALLEL is read by the Ollama server process, not this Python code.
    # It must be set before Ollama starts, or Ollama must be restarted after setting it.
    # load_dotenv() above already makes it available in os.environ, but we check it here
    # to include it in the returned config dict for reference.
    ollama_num_parallel = os.getenv("OLLAMA_NUM_PARALLEL")

    return {
        "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
        "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY", ""),
        "gemini_api_key": os.getenv("GEMINI_API_KEY", ""),
        "lmql_backend": os.getenv("LMQL_BACKEND", "ollama"),
        "lmql_model": os.getenv("LMQL_MODEL", "gpt-oss:20b"),
        "ollama_base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        "ollama_num_parallel": ollama_num_parallel or "",
        "llamacpp_model_path": os.getenv("LLAMACPP_MODEL_PATH", ""),
        "llamacpp_n_ctx": int(os.getenv("LLAMACPP_N_CTX", "2048")),
        "llamacpp_n_gpu_layers": int(os.getenv("LLAMACPP_N_GPU_LAYERS", "0")),
        "llamacpp_temperature": float(os.getenv("LLAMACPP_TEMPERATURE", "0.7")),
        "llamacpp_max_tokens": int(os.getenv("LLAMACPP_MAX_TOKENS", "256")),  # Reduced from 512 to prevent whitespace padding
        "llamacpp_stop_sequences": os.getenv("LLAMACPP_STOP_SEQUENCES", "").split(",") if os.getenv("LLAMACPP_STOP_SEQUENCES") else None,
        "embedding_provider": os.getenv("EMBEDDING_PROVIDER", "sentence-transformer"),
        "embedding_model": os.getenv(
            "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
        ),
    }


def configure_llm(provider: str = "ollama", model: str | None = None) -> Any:
    """Configure and return an LLM instance.

    Args:
        provider: LLM provider name ("openai", "anthropic", "gemini", "ollama", or "llamacpp").
        model: Optional model name/path. For llamacpp, this should be the path to the GGUF model file.
               If None, uses default for provider.

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
        if Ollama is None:
            raise ImportError(
                "Ollama provider requested but ollama package is not available. "
                "Install with: pip install ollama"
            )
        model_name = model or config["lmql_model"]
        base_url = config["ollama_base_url"]
        # Enable JSON mode for constrained generation (equivalent to LlamaCPP's grammar)
        # This applies GBNF grammar constraints to force valid JSON output
        return Ollama(
            model=model_name,
            base_url=base_url,
            request_timeout=120.0,
            json_mode=True  # Enable JSON constrained generation
        )
    elif provider == "llamacpp":
        if LlamaCPP is None:
            raise ImportError(
                "LlamaCPP provider requested but llama-cpp package is not available. "
                "Install with: pip install llama-index-llms-llama-cpp llama-cpp-python"
            )
        model_path = model or config["llamacpp_model_path"]
        if not model_path:
            raise ValueError(
                "LLAMACPP_MODEL_PATH must be set in environment or provided as model parameter"
            )
        if not Path(model_path).exists():
            raise FileNotFoundError(
                f"LlamaCPP model file not found: {model_path}"
            )

        # Default stop sequences for gpt-oss model (similar to Ollama's behavior)
        default_stop_sequences = ["<|return|>", "<|end|>", "<|endoftext|>"]
        stop_sequences = config["llamacpp_stop_sequences"] or default_stop_sequences

        llm_kwargs = {
            "model_path": model_path,
            "temperature": 1.0,  # gpt-oss-20b requires temp=1.0 for proper behavior
            "model_kwargs": {
                "n_ctx": config["llamacpp_n_ctx"],
                "n_gpu_layers": config["llamacpp_n_gpu_layers"],
                # NOTE: chat_format parameter removed - causes hanging
                # The model should use its embedded chat template automatically
                "verbose": False,
            },
            "max_new_tokens": config["llamacpp_max_tokens"],
            # System prompt recommended for gpt-oss-20b (from Perplexity research)
            "system_prompt": (
                "You are a helpful, harmless, and honest AI assistant. "
                "You should provide concise, direct answers and use your reasoning "
                "capabilities to solve complex problems before responding."
            ),
        }

        # Add stop sequences and JSON grammar to generate_kwargs
        # Use pre-compiled global JSON_GRAMMAR to avoid duplication errors
        # when configure_llm() is called multiple times during benchmarking
        # Sampling parameters based on Perplexity research for gpt-oss-20b
        if JSON_GRAMMAR is None:
            print("⚠ Warning: JSON_GRAMMAR is None, grammar constraints disabled", flush=True)

        llm_kwargs["generate_kwargs"] = {
            "stop": stop_sequences,
            "temperature": 1.0,  # gpt-oss-20b requires temp=1.0
            "max_tokens": config["llamacpp_max_tokens"],
            "top_k": 128,  # CRITICAL: gpt-oss-20b requires top_k >= 128
            "repeat_penalty": 1.1,  # Recommended for "agentic" feel
            # Grammar temporarily disabled - causing hang in llama_decode()
            # TODO: Debug grammar compatibility with these sampling parameters
            # "grammar": JSON_GRAMMAR,
        }

        return LlamaCPP(**llm_kwargs)
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
        default_embed = HuggingFaceEmbedding(model_name=model_name)
        text_instruction = getattr(default_embed, "text_instruction", None)
        query_instruction = getattr(default_embed, "query_instruction", None)
        print(
            "Default embedding instructions for HuggingFaceEmbedding:",
            flush=True,
        )
        print(f"  text_instruction: {text_instruction!r}", flush=True)
        print(f"  query_instruction: {query_instruction!r}", flush=True)
        return HuggingFaceEmbedding(
            model_name=model_name,
            text_instruction="",
            query_instruction="",
        )
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
