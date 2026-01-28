# LLM Configuration

This directory contains the LLM and embedding model configuration system for the autograder.

## Overview

The configuration system supports multiple providers for both LLMs and embeddings:

- **LLMs**: OpenAI, Anthropic Claude, Google Gemini, Ollama (local models), llama.cpp (local models)
- **Embeddings**: OpenAI, SentenceTransformer (local models)

## Configuration File

Create a `~/.env` file with your configuration:

```bash
# LLM Provider Configuration
# Options: "openai", "anthropic", "gemini", "ollama", "llamacpp"
LMQL_BACKEND=ollama

# LLM Model (provider-specific)
LMQL_MODEL=gpt-oss:20b  # For Ollama
# LMQL_MODEL=gpt-4o-mini  # For OpenAI
# LMQL_MODEL=claude-3-5-sonnet-20241022  # For Anthropic
# LMQL_MODEL=models/gemini-1.5-flash  # For Gemini

# Ollama Configuration (only needed if using Ollama)
OLLAMA_BASE_URL=http://localhost:11434

# API Keys (only needed for cloud providers)
OPENAI_API_KEY=sk-...  # Only if using OpenAI
ANTHROPIC_API_KEY=sk-ant-...  # Only if using Anthropic
GEMINI_API_KEY=...  # Only if using Gemini

# Embedding Configuration
# Options: "openai", "sentence-transformer", "huggingface"
EMBEDDING_PROVIDER=sentence-transformer

# Embedding Model (provider-specific)
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2  # For SentenceTransformer
# EMBEDDING_MODEL=text-embedding-3-small  # For OpenAI
```

## Provider Options

### LLM Providers

#### 1. Ollama (Recommended for Development)

**Advantages:**
- Free and local
- No API keys required
- Fast inference with local models
- Support for many open-source models

**Setup:**
```bash
# Install Ollama (if not already installed)
# Download from https://ollama.ai

# Start Ollama server
ollama serve

# Pull a model (examples)
ollama pull gpt-oss:20b  # 20B parameter model
ollama pull qwen2.5:32b  # 32B parameter model
ollama pull llama3:8b    # Llama 3 8B
```

**Configuration:**
```bash
LMQL_BACKEND=ollama
LMQL_MODEL=gpt-oss:20b
OLLAMA_BASE_URL=http://localhost:11434
```

#### 2. OpenAI

**Advantages:**
- High quality responses
- Fast API
- Reliable

**Disadvantages:**
- Requires API key
- Costs money per request
- Requires internet connection

**Configuration:**
```bash
LMQL_BACKEND=openai
LMQL_MODEL=gpt-4o-mini  # or gpt-4, gpt-3.5-turbo
OPENAI_API_KEY=sk-...
```

#### 3. Anthropic Claude

**Advantages:**
- High quality responses
- Good for complex reasoning
- Long context windows

**Disadvantages:**
- Requires API key
- Costs money per request
- Requires internet connection

**Configuration:**
```bash
LMQL_BACKEND=anthropic
LMQL_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=sk-ant-...
```

#### 4. Google Gemini

**Advantages:**
- High quality responses
- Fast inference
- Competitive pricing
- Long context windows
- Free tier available

**Disadvantages:**
- Requires API key
- Requires internet connection

**Configuration:**
```bash
LMQL_BACKEND=gemini
LMQL_MODEL=models/gemini-1.5-flash  # or models/gemini-1.5-pro
GEMINI_API_KEY=...
```

**Available Models:**
- `models/gemini-1.5-flash` - Fast and cost-effective
- `models/gemini-1.5-pro` - More capable, slower
- `models/gemini-2.0-flash-exp` - Latest experimental model

#### 5. llama.cpp (Local Inference)

**Advantages:**
- Free and local
- No API keys required
- Direct model file loading (GGUF format)
- Efficient CPU and GPU inference
- Full control over model and parameters
- No internet required after model download

**Disadvantages:**
- Requires downloading model files (can be large, 4-32GB)
- Setup more complex than Ollama
- May require manual GPU configuration

**Setup:**
```bash
# Install llama-cpp-python (already installed)
pip install llama-cpp-python llama-index-llms-llama-cpp

# Download a GGUF model file from HuggingFace
# Example: https://huggingface.co/TheBloke
# Popular models:
# - Llama 2 7B GGUF: https://huggingface.co/TheBloke/Llama-2-7B-GGUF
# - Mistral 7B GGUF: https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF
# - Qwen 2.5 7B GGUF: https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF

# Place the model file in a known location, e.g.:
# ~/models/mistral-7b-instruct-v0.2.Q4_K_M.gguf
```

**Configuration:**
```bash
LMQL_BACKEND=llamacpp
LLAMACPP_MODEL_PATH=/Users/yourname/models/mistral-7b-instruct-v0.2.Q4_K_M.gguf
LLAMACPP_N_CTX=2048              # Context window size (default: 2048)
LLAMACPP_N_GPU_LAYERS=0          # Number of layers to offload to GPU (0=CPU only)
LLAMACPP_TEMPERATURE=0.7          # Sampling temperature (default: 0.7)
LLAMACPP_MAX_TOKENS=512          # Max tokens to generate (default: 512)
```

**GPU Acceleration (Optional):**
```bash
# For GPU support, install with GPU backend:
# CUDA (NVIDIA)
CMAKE_ARGS="-DLLAMA_CUDA=on" pip install llama-cpp-python

# Metal (Apple Silicon)
CMAKE_ARGS="-DLLAMA_METAL=on" pip install llama-cpp-python

# Then set GPU layers in config:
LLAMACPP_N_GPU_LAYERS=35  # Offload 35 layers to GPU
```

**Model Quantization Formats:**
- `Q4_K_M` - 4-bit quantization, medium quality (recommended, ~4GB)
- `Q5_K_M` - 5-bit quantization, better quality (~5GB)
- `Q8_0` - 8-bit quantization, high quality (~7GB)
- `f16` - 16-bit float, highest quality (~14GB)

### Embedding Providers

#### 1. SentenceTransformer (Recommended)

**Advantages:**
- Free and local
- No API keys required
- Fast
- Good quality

**Configuration:**
```bash
EMBEDDING_PROVIDER=sentence-transformer
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

**Alternative models:**
- `BAAI/bge-small-en-v1.5` - Better quality, slightly slower
- `sentence-transformers/all-mpnet-base-v2` - Higher quality, larger model

#### 2. OpenAI

**Advantages:**
- High quality embeddings
- Fast API

**Disadvantages:**
- Requires API key and costs money

**Configuration:**
```bash
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
OPENAI_API_KEY=sk-...
```

## Usage in Code

### Automatic Configuration

```python
from config.llm_config import setup_llamaindex_defaults

# This configures both LLM and embeddings based on ~/.env
setup_llamaindex_defaults()
```

### Manual Configuration

```python
from config.llm_config import configure_llm, configure_embedding

# Configure LLM
llm = configure_llm("ollama", "gpt-oss:20b")

# Configure embeddings
embed_model = configure_embedding("sentence-transformer")
```

### LMQLGrader

```python
from grader.lmql_grading import LMQLGrader

# Uses configuration from ~/.env automatically
grader = LMQLGrader()

# Or provide specific LLM
from config.llm_config import configure_llm
llm = configure_llm("ollama", "gpt-oss:20b")
grader = LMQLGrader(llm=llm)
```

## Switching Providers

To switch providers, simply update your `~/.env` file:

### Switch from OpenAI to Ollama

```bash
# Before (OpenAI)
LMQL_BACKEND=openai
OPENAI_API_KEY=sk-...

# After (Ollama)
LMQL_BACKEND=ollama
LMQL_MODEL=gpt-oss:20b
OLLAMA_BASE_URL=http://localhost:11434
```

### Switch Embedding Models

```bash
# Before (OpenAI embeddings)
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
OPENAI_API_KEY=sk-...

# After (SentenceTransformer)
EMBEDDING_PROVIDER=sentence-transformer
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

## Troubleshooting

### Ollama Connection Errors

```
Error: Connection refused to localhost:11434
```

**Solution:** Make sure Ollama server is running:
```bash
ollama serve
```

### Model Not Found

```
Error: model 'gpt-oss:20b' not found
```

**Solution:** Pull the model first:
```bash
ollama pull gpt-oss:20b
```

### OpenAI API Key Errors

```
Error: No API key found for OpenAI
```

**Solution:** Add your API key to `~/.env`:
```bash
OPENAI_API_KEY=sk-...
```

### SentenceTransformer Download Errors

**Solution:** The model downloads automatically on first use. Ensure you have:
- Internet connection (first time only)
- Sufficient disk space (~500MB for models)
- Write access to `~/.cache/huggingface/`

### llama.cpp Model Not Found

```
Error: LlamaCPP model file not found: /path/to/model.gguf
```

**Solution:**
1. Verify the model file exists at the specified path
2. Check the LLAMACPP_MODEL_PATH environment variable
3. Download a GGUF model from HuggingFace (e.g., TheBloke's models)
4. Ensure the path is absolute, not relative

### llama.cpp Import Error

```
Error: LlamaCPP provider requested but llama-cpp package is not available
```

**Solution:** Install the required packages:
```bash
pip install llama-index-llms-llama-cpp llama-cpp-python
```

For GPU support (CUDA):
```bash
CMAKE_ARGS="-DLLAMA_CUDA=on" pip install llama-cpp-python --force-reinstall --no-cache-dir
```

For GPU support (Apple Metal):
```bash
CMAKE_ARGS="-DLLAMA_METAL=on" pip install llama-cpp-python --force-reinstall --no-cache-dir
```

## Performance Comparison

| Provider | Speed | Cost | Quality | Local | GPU Support |
|----------|-------|------|---------|-------|-------------|
| Ollama (gpt-oss:20b) | Fast | Free | Good | Yes | Yes |
| llama.cpp (7B Q4) | Fast | Free | Good | Yes | Yes |
| OpenAI (gpt-4o-mini) | Fast | $$ | Excellent | No | N/A |
| Anthropic (Claude) | Medium | $$$ | Excellent | No | N/A |
| Gemini (1.5-flash) | Very Fast | $ | Excellent | No | N/A |
| SentenceTransformer | Very Fast | Free | Good | Yes | Yes |

## Recommended Configurations

### Development (Free, Local - Ollama)

```bash
LMQL_BACKEND=ollama
LMQL_MODEL=gpt-oss:20b
OLLAMA_BASE_URL=http://localhost:11434
EMBEDDING_PROVIDER=sentence-transformer
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

### Development (Free, Local - llama.cpp)

```bash
LMQL_BACKEND=llamacpp
LLAMACPP_MODEL_PATH=/path/to/your/model.gguf
LLAMACPP_N_CTX=2048
LLAMACPP_N_GPU_LAYERS=35  # Use GPU if available, 0 for CPU only
LLAMACPP_TEMPERATURE=0.7
LLAMACPP_MAX_TOKENS=512
EMBEDDING_PROVIDER=sentence-transformer
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

### Production (Cloud, High Quality)

```bash
LMQL_BACKEND=openai
LMQL_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
```

### Cost-Effective (Gemini + Local Embeddings)

```bash
LMQL_BACKEND=gemini
LMQL_MODEL=models/gemini-1.5-flash
GEMINI_API_KEY=...
EMBEDDING_PROVIDER=sentence-transformer
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

### Hybrid (Local Embeddings, Cloud LLM)

```bash
LMQL_BACKEND=anthropic
LMQL_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=sk-ant-...
EMBEDDING_PROVIDER=sentence-transformer
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```
