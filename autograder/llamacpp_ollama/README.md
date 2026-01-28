# LLM Performance Comparison Tool

A comprehensive benchmarking tool to compare performance between **Ollama** and **Llama.cpp** using the OSS 20B model.

## Overview

This tool helps diagnose performance issues and compare inference speeds between two LLM backends:
- **Ollama**: Server-based approach running at `http://localhost:11434`
- **Llama.cpp**: Direct model loading using `llama-cpp-python`

Both use the same 20B parameter base model (`gpt-oss:20b`) with 4-bit quantization:
- **Ollama**: MXFP4 format (13 GB)
- **Llama.cpp**: Q4_K_M format (11 GB)

While the quantization formats differ, both are 4-bit compressions with similar accuracy/size tradeoffs. The comparison is valid for answering: **"Which setup performs better in practice?"**

## Directory Structure

```
llamacpp_ollama/
├── README.md                          # This file
├── compare_llm_performance.py         # Main benchmark script
├── config/
│   └── llm_benchmark_prompts.yaml     # Test prompts configuration
├── tests/
│   └── test_benchmark.py              # Test suite
└── results/                           # Generated benchmark results (gitignored)
    └── llm_comparison_TIMESTAMP/
        ├── results.json               # Raw data
        ├── report.md                  # Human-readable report
        └── results.csv                # Spreadsheet export
```

## Prerequisites

### 1. Verify Ollama is Running

```bash
curl http://localhost:11434/api/version
# Should return: {"version":"0.15.0"}
```

If not running, start Ollama:
```bash
ollama serve
```

### 2. Verify Llama.cpp Model Exists

```bash
ls -lh /Users/erlebach/data/llm_models/gpt-oss-20b-Q4_K_M.gguf
# Should show: 11GB file (Q4_K_M quantization)
```

### 3. Check Model Quantization Details

**Ollama model info:**
```bash
ollama show gpt-oss:20b
# Shows: quantization MXFP4, size 13 GB
```

**Llama.cpp model info:**
```bash
# Quantization is in the filename: Q4_K_M
# File size: 11 GB
```

⚠️ **Current models use different quantizations**: MXFP4 (Ollama) vs Q4_K_M (Llama.cpp)

**To get matching models** (for true apples-to-apples comparison):
```bash
# Option A: Use Q4_K_M for both
# Pull/create Ollama model with Q4_K_M quantization, OR

# Option B: Use MXFP4 for both
# Convert/download GGUF file with MXFP4 quantization for Llama.cpp
```

### 3. Install Dependencies

Dependencies are already in the project's `pyproject.toml`:
- `pyyaml` - Configuration loading
- `tabulate` - Table formatting
- `llama-index-llms-ollama` - Ollama integration
- `llama-index-llms-llama-cpp` - Llama.cpp integration

If missing, install with:
```bash
uv add pyyaml tabulate
```

## Usage

### Basic Usage

Run the complete benchmark suite from the project root:

```bash
uv run python llamacpp_ollama/compare_llm_performance.py
```

This runs:
- 9 prompts (3 short, 3 medium, 3 long)
- 3 repetitions per prompt
- 1 warmup iteration per prompt
- Both Ollama and Llama.cpp providers

Results are saved to: `llamacpp_ollama/results/llm_comparison_TIMESTAMP/`

### Advanced Options

**Test specific categories:**
```bash
uv run python llamacpp_ollama/compare_llm_performance.py --categories short,medium
```

**More repetitions for robust statistics:**
```bash
uv run python llamacpp_ollama/compare_llm_performance.py --repetitions 5
```

**Custom output directory:**
```bash
uv run python llamacpp_ollama/compare_llm_performance.py --output-dir llamacpp_ollama/results/my_test
```

**Skip cold start tests (faster):**
```bash
uv run python llamacpp_ollama/compare_llm_performance.py --skip-cold-start
```

**Verbose output:**
```bash
uv run python llamacpp_ollama/compare_llm_performance.py --verbose
```

**Test only one provider:**
```bash
uv run python llamacpp_ollama/compare_llm_performance.py --providers ollama
```

**Custom configuration file:**
```bash
uv run python llamacpp_ollama/compare_llm_performance.py --config path/to/custom_prompts.yaml
```

### Quick Single-Category Test

For fast validation:

```bash
uv run python llamacpp_ollama/compare_llm_performance.py \
    --categories short \
    --repetitions 1 \
    --verbose
```

This runs in ~30 seconds and tests basic functionality.

## Configuration

### Prompt Configuration

Edit `llamacpp_ollama/config/llm_benchmark_prompts.yaml` to customize:

```yaml
config:
  repetitions: 3              # Number of times to run each prompt
  warmup_iterations: 1        # Warmup runs (discarded from stats)
  max_tokens: 512             # Maximum tokens to generate
  temperature: 0.7            # Sampling temperature
  timeout_seconds: 60         # Timeout per inference

prompts:
  - id: short_1
    category: short
    complexity: simple
    prompt: "What is the capital of France?"
    expected_tokens: 10
```

### LLM Configuration

LLM settings are loaded from `~/.env` via `config/llm_config.py`:

**Ollama:**
```bash
OLLAMA_BASE_URL=http://localhost:11434
LMQL_MODEL=gpt-oss:20b
```

**Llama.cpp:**
```bash
LLAMACPP_MODEL_PATH=/Users/erlebach/data/llm_models/gpt-oss-20b-Q4_K_M.gguf
LLAMACPP_N_CTX=4096
LLAMACPP_N_GPU_LAYERS=35
LLAMACPP_TEMPERATURE=0.7
LLAMACPP_MAX_TOKENS=512
```

## Output Format

### Terminal Summary

```
============================================================
PERFORMANCE SUMMARY
============================================================

Provider    Mean Time    Median Time    Tokens/sec    P95 Time    Success
----------  -----------  -------------  ------------  ----------  ---------
OLLAMA      4.632s       3.511s         13.0          9.375s      3/3
LLAMACPP    9.146s       9.202s         53.5          9.245s      3/3

🏆 WINNER: OLLAMA
   OLLAMA is 1.97x faster than LLAMACPP (97.5% improvement)
```

### Generated Reports

1. **JSON (`results.json`)**: Complete raw data with all metrics
2. **Markdown (`report.md`)**: Human-readable tables and analysis
3. **CSV (`results.csv`)**: Flat format for spreadsheet analysis

## Testing

### Run Validation Tests

Quick validation without external dependencies:

```bash
uv run python llamacpp_ollama/tests/test_benchmark.py
```

### Run Full Test Suite

With pytest (tests actual LLM calls):

```bash
pytest llamacpp_ollama/tests/test_benchmark.py -v
```

Individual test classes:
```bash
# Test only configuration loading
pytest llamacpp_ollama/tests/test_benchmark.py::TestConfigurationLoading -v

# Test only statistics
pytest llamacpp_ollama/tests/test_benchmark.py::TestStatisticsCalculation -v

# Test with coverage
pytest llamacpp_ollama/tests/test_benchmark.py --cov=llamacpp_ollama --cov-report=html
```

## Key Findings

### Model Details

| Aspect | Ollama | Llama.cpp |
|--------|---------|-----------|
| **Base Model** | gpt-oss:20b | gpt-oss:20b |
| **Quantization** | MXFP4 | Q4_K_M |
| **File Size** | 13 GB | 11 GB |
| **Format** | Ollama blob | GGUF |

### Initial Test Results

From preliminary testing with short prompts:

| Metric | Ollama (MXFP4) | Llama.cpp (Q4_K_M) | Winner |
|--------|---------|-----------|--------|
| **Mean Inference Time** | 4.6s | 9.1s | Ollama (1.97x faster) |
| **Tokens per Second** | 13 tok/s | 53.5 tok/s | Llama.cpp (4.1x higher) |
| **Tokens Generated** | 8-230 | 417-535 | Ollama (appropriate) |
| **Model Load Time** | 0.004s | 7.7s | Ollama |

### Root Cause: Llama.cpp Issue

**Problem**: Llama.cpp generates excessive tokens (500+) even for simple prompts like "What is the capital of France?"

**Expected**: "Paris" (1-2 tokens)
**Actual**: Full 512 tokens of rambling content

**Diagnosis**: Llama.cpp lacks proper stop sequences and continues generating until hitting max_tokens limit.

**Evidence**:
```python
# Prompt: "What is the capital of France?"
# Ollama response (8 tokens): "Paris"
# Llama.cpp response (516 tokens): "': 'Paris', 'Who wrote Pride and Prejudice?': ..."
```

**Fix Needed**: Configure proper stop sequences in `~/.env`:
```bash
LLAMACPP_STOP_SEQUENCES="<|return|>,<|end|>,\n\n"
```

### Performance Summary

- **For total inference time**: Ollama is faster (4.6s vs 9.1s)
- **For token throughput**: Llama.cpp generates faster (53.5 vs 13 tok/s)
- **For usability**: Ollama produces appropriate output length

### Root Cause: Llama.cpp Stop Sequence Problem

**The key issue** is NOT that Llama.cpp is slow at token generation - it's actually **faster** (53.5 vs 13 tok/s).

**The problem**: Llama.cpp generates **excessive tokens** due to missing stop sequences:
- **Expected**: "Paris" (1-2 tokens) for "What is the capital of France?"
- **Actual**: 500+ tokens of rambling content

Llama.cpp spends 9 seconds generating 516 tokens when it should stop after 2 tokens. If it stopped correctly, inference would take ~0.04 seconds (2 tokens ÷ 53.5 tok/s).

**Fix**: Configure proper stop sequences in `~/.env`:
```bash
LLAMACPP_STOP_SEQUENCES="<|return|>,<|end|>,\n\n"
```

## Troubleshooting

### Ollama Connection Error

```bash
# Check if Ollama is running
curl http://localhost:11434/api/version

# Start Ollama if not running
ollama serve

# Verify model is pulled
ollama list | grep gpt-oss
```

### Llama.cpp Model Not Found

```bash
# Verify model path
ls -lh /Users/erlebach/data/llm_models/gpt-oss-20b-Q4_K_M.gguf

# Update .env if path is different
echo "LLAMACPP_MODEL_PATH=/correct/path/to/model.gguf" >> ~/.env
```

### Llama.cpp Metal/GPU Issues

If you see Metal compilation warnings:

```bash
# Run the fix script
./fix_llamacpp.sh

# Or reinstall with Metal support
pip uninstall llama-cpp-python
CMAKE_ARGS="-DLLAMA_METAL=on" pip install llama-cpp-python --no-cache-dir
```

### Import Errors

```bash
# Ensure you're in the project root and using uv run
cd /Users/erlebach/src/2026/grading_assessment/autograder
uv run python llamacpp_ollama/compare_llm_performance.py
```

## Architecture

### Fair Comparison Methodology

1. **Sequential Execution**: Providers run one at a time (no resource contention)
2. **Randomized Order**: Provider order randomized to prevent systematic bias
3. **Thermal Throttling Prevention**: 2-second delay between tests
4. **Warmup Runs**: 1 warmup iteration per prompt (discarded from statistics)
5. **Multiple Repetitions**: 3 runs per test for statistical robustness
6. **Parameter Parity**: Same temperature, max_tokens, and prompts for both

**Note**: Models use different 4-bit quantization formats (MXFP4 vs Q4_K_M), but both provide similar output quality. Results reflect real-world performance of each backend with its respective quantization.

### Metrics Collected

For each test run:
- `inference_time_sec`: Wall clock time for inference
- `tokens_generated`: Estimated token count (chars ÷ 4)
- `tokens_per_sec`: Throughput (tokens ÷ time)
- `model_load_time_sec`: Cold start time
- `response_text`: Full response for analysis
- `success`: Whether test completed without error

### Statistics Calculated

Per provider:
- Mean, median, standard deviation
- P95, P99 percentiles
- Category-specific breakdowns
- Success/failure rates

## Future Improvements

1. **Fix Llama.cpp Stop Sequences**: Configure proper stopping criteria (HIGH PRIORITY)
2. **Token Accuracy**: Use actual tokenizer instead of char÷4 estimation
3. **Memory Profiling**: Track RAM and VRAM usage
4. **GPU Utilization**: Monitor Metal GPU usage during inference
5. **Add More Models**: Test with different model sizes and quantization levels
6. **Batch Testing**: Test concurrent requests handling
7. **Prompt Caching**: Test with repeated prompts to measure cache efficiency
8. **Benchmark After Fix**: Re-run comparison after fixing stop sequences to see true performance

## Related Files

- `../config/llm_config.py` - Shared LLM configuration loader
- `../tests/test_llama_cpp.py` - Additional Llama.cpp tests
- `../fix_llamacpp.sh` - Script to fix Metal compilation issues
- `~/.env` - Environment configuration for both providers

## License

Part of the autograder project.

## Support

For issues or questions:
1. Check troubleshooting section above
2. Verify prerequisites are met
3. Run validation tests: `uv run python llamacpp_ollama/tests/test_benchmark.py`
4. Check generated reports for detailed error messages
