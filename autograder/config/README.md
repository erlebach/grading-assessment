# LLM Configuration

This directory contains the LLM and embedding model configuration system for the autograder.

## Overview

The configuration system supports multiple providers for both LLMs and embeddings:

- **LLMs**: OpenAI, Anthropic Claude, Google Gemini, Ollama (local models)
- **Embeddings**: OpenAI, SentenceTransformer (local models)

## Configuration File

Create a `~/.env` file with your configuration:

```bash
# LLM Provider Configuration
# Options: "openai", "anthropic", "gemini", "ollama"
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

## Performance Comparison

| Provider | Speed | Cost | Quality | Local |
|----------|-------|------|---------|-------|
| Ollama (gpt-oss:20b) | Fast | Free | Good | Yes |
| OpenAI (gpt-4o-mini) | Fast | $$ | Excellent | No |
| Anthropic (Claude) | Medium | $$$ | Excellent | No |
| Gemini (1.5-flash) | Very Fast | $ | Excellent | No |
| SentenceTransformer | Very Fast | Free | Good | Yes |

## Recommended Configurations

### Development (Free, Local)

```bash
LMQL_BACKEND=ollama
LMQL_MODEL=gpt-oss:20b
OLLAMA_BASE_URL=http://localhost:11434
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
