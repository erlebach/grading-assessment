# Task List: LLM Performance Comparison Tool (Ollama vs Llama.cpp)

**Project**: Benchmark and compare Ollama vs Llama.cpp performance with OSS 20B model
**Session**: autograder_2026-01-25
**Created**: 2026-01-28
**Last Updated**: 2026-01-28 14:56

---

## Overall Status Summary

| Phase | Tasks | Completed | Status |
|-------|-------|-----------|--------|
| **Phase 1: Prerequisites** | 2 | 2 | ✅ Complete |
| **Phase 2: Configuration** | 1 | 1 | ✅ Complete |
| **Phase 3: Core Implementation** | 6 | 6 | ✅ Complete |
| **Phase 4: Output & Reporting** | 4 | 4 | ✅ Complete |
| **Phase 5: CLI** | 2 | 2 | ✅ Complete |
| **Phase 6: Testing** | 4 | 4 | ✅ Complete |
| **Phase 7: Documentation** | 2 | 2 | ✅ Complete |
| **Phase 8: Constrained Generation** | 7 | 7 | ✅ Complete |
| **Phase 9: Fair Comparison** | 3 | 3 | ✅ Complete |
| **Phase 10: Batch Inference** | 6 | 1 | 🔄 In Progress |
| **Phase 11: Quality & Optimization** | 3 | 0 | ⏳ Pending |
| **TOTAL** | **43** | **32** | **🔄 74% Complete** |

## Detailed Task Status

| Task ID | Task Name | Status | Priority |
|---------|-----------|--------|----------|
| T1.1 | Verify System Prerequisites | ✅ Complete | High |
| T1.2 | Install Required Dependencies | ✅ Complete | High |
| T2.1 | Create Benchmark Prompt Configuration | ✅ Complete | High |
| T3.1 | Create PerformanceMetrics Data Class | ✅ Complete | High |
| T3.2 | Implement Configuration Loading | ✅ Complete | High |
| T3.3 | Implement LLM Initialization | ✅ Complete | High |
| T3.4 | Implement Single Test Execution | ✅ Complete | High |
| T3.5 | Implement Full Benchmark Suite | ✅ Complete | High |
| T3.6 | Implement Statistical Analysis | ✅ Complete | Medium |
| T4.1 | Implement JSON Results Export | ✅ Complete | Medium |
| T4.2 | Implement Markdown Report Generation | ✅ Complete | Medium |
| T4.3 | Implement CSV Export | ✅ Complete | Low |
| T4.4 | Implement Terminal Summary Output | ✅ Complete | High |
| T5.1 | Implement CLI Argument Parsing | ✅ Complete | High |
| T5.2 | Implement Main Entry Point | ✅ Complete | High |
| T6.1 | Unit Test - Configuration Loading | ✅ Complete | Medium |
| T6.2 | Unit Test - LLM Initialization | ✅ Complete | Medium |
| T6.3 | Integration Test - Single Category | ✅ Complete | High |
| T6.4 | Integration Test - Full Benchmark | ✅ Complete | High |
| T7.1 | Analyze Results | ✅ Complete | High |
| T7.2 | Create README Documentation | ✅ Complete | Medium |
| **T8.1** | **Investigate JSON Output Issues** | ✅ Complete | High |
| **T8.2** | **Implement GBNF JSON Grammar (LlamaCPP)** | ✅ Complete | High |
| **T8.3** | **Enable JSON Mode (Ollama)** | ✅ Complete | High |
| **T8.4** | **Implement Actual Token Counting** | ✅ Complete | High |
| **T8.5** | **Add JSON Extraction Functions** | ✅ Complete | Medium |
| **T8.6** | **Add Progress Indicators/Timestamps** | ✅ Complete | Medium |
| **T8.7** | **Remove Custom Chat Template** | ✅ Complete | High |
| **T9.1** | **Run Fair Comparison Benchmark** | ✅ Complete | High |
| **T9.2** | **Analyze Token-Accurate Results** | ✅ Complete | High |
| **T9.3** | **Update Documentation** | ✅ Complete | Medium |
| **T10.1** | **Design Batch Benchmark Architecture** | ✅ Complete | High |
| **T10.2** | **Implement Sequential Baseline** | ✅ Complete | High |
| **T10.3** | **Implement Batch Inference (n=4,8)** | ⏳ Pending | High |
| **T10.4** | **Add CPU Time Measurement** | ⏳ Pending | Medium |
| **T10.5** | **Run Batch Benchmarks** | ⏳ Pending | High |
| **T10.6** | **Analyze Batch Speedup Results** | ⏳ Pending | High |
| **T11.1** | **Fix LlamaCPP Whitespace Padding** | ⏳ Pending | High |
| **T11.2** | **Implement Incremental Results Writing** | ⏳ Pending | High |
| **T11.3** | **Add Run Description to Reports** | ⏳ Pending | Medium |

## Additional Work Completed

| Task | Description | Status |
|------|-------------|--------|
| **LlamaCPP Chat Template Fix** | Added custom `gpt_oss_messages_to_prompt()` function (later removed in T8.7) | ✅ Complete (Superseded) |
| **Stop Sequences Configuration** | Configured proper stop sequences (`<|return|>`, `<|end|>`, `<|endoftext|>`) for LlamaCPP | ✅ Complete |
| **Output Directory Fix** | Fixed hardcoded path from `llamacpp_ollama/results/` to `results/` | ✅ Complete |
| **Initial Benchmarks (Unconstrained)** | Ran full benchmarks WITHOUT grammar constraints (both providers) | ✅ Complete |
| **Initial Performance Analysis** | Analyzed unconstrained results - found issues with meta-commentary | ✅ Complete |
| **GBNF JSON Grammar Implementation** | Implemented JSON grammar for LlamaCPP using `LlamaGrammar.from_string()` | ✅ Complete |
| **Ollama JSON Mode Enable** | Enabled `json_mode=True` for fair comparison with LlamaCPP | ✅ Complete |
| **Actual Token Counting** | Replaced character approximation with real API token counts | ✅ Complete |
| **JSON Extraction Functions** | Added `extract_json_answer()` to parse JSON responses | ✅ Complete |
| **Progress Monitoring** | Added timestamps and unbuffered output (`-u` flag, `flush=True`) | ✅ Complete |
| **Chat Template Removal** | Removed custom chat template in favor of default + grammar | ✅ Complete |
| **Fair Benchmark Launch** | Started benchmark with both providers using JSON constraints | 🔄 In Progress |

## Key Findings

### Initial Findings (Unconstrained Mode - MISLEADING)
**⚠️ Note**: These results were from UNFAIR comparison (no grammar constraints):

- **7.6x faster** overall than Ollama (660% improvement)
- **13.4x faster** on medium prompts
- **7.5x faster** on long prompts with 71.1 tokens/sec throughput
- **BUT**: Token counts were misleading (Ollama hides thinking, LlamaCPP includes it)

### Corrected Understanding
**✅ What We Actually Learned**:

1. **Both models generate similar reasoning** - Ollama stores in hidden `thinking` field
2. **Token count differences were artifacts** - not true speed differences
3. **Ollama does NOT automatically apply grammar** - must enable `json_mode=True`
4. **GBNF grammar = logit masking** - forces valid JSON at inference level
5. **Fair comparison requires equal constraints** - both with or both without grammar

### Fair Comparison Results (Completed)
**✅ Results from T9.1** - Both providers with JSON grammar enabled

**Winner: LlamaCPP (1.57x faster overall)**

| Provider | Mean Time | Tokens/sec | P95 Latency |
|----------|-----------|------------|-------------|
| Ollama | 13.8s | 16.8 | 36.9s |
| LlamaCPP | 8.8s | 28.3 | 18.6s |

**By Category**:
- **Short**: Ollama 2.9s (5.8 tok/s) vs LlamaCPP 3.3s (26.6 tok/s)
- **Medium**: Ollama 16.3s (18.9 tok/s) vs LlamaCPP 13.8s (29.1 tok/s)
- **Long**: Ollama 22.3s (25.8 tok/s) vs **LlamaCPP 9.3s (29.1 tok/s)** ← 2.4x faster

**Quality Issue Found**: LlamaCPP pads responses with ~500 whitespace tokens after JSON (needs fix in T11.1)

**Recommendation**: Use **LlamaCPP** for grading pipeline (1.57x faster, 2.4x on long prompts, more consistent)

---

## Phase 1: Prerequisites and Environment Setup

### T1.1: Verify System Prerequisites
**Status**: ✅ Complete
**Priority**: High
**Description**: Verify all required components are available and properly configured.

**Checklist**:

- [ ] Verify Ollama server is running: `curl http://localhost:11434/api/tags`
- [ ] Verify Llama.cpp model file exists and is accessible:
  ```bash
  ls -lh /Users/erlebach/data/llm_models/gpt-oss-20b-Q4_K_M.gguf
  ```

- [ ] Check Metal GPU support for Llama.cpp:
  ```bash
  python -c "from llama_cpp import Llama; print('Metal support OK')"
  ```

    - If errors, run: `./fix_llamacpp.sh`
- [ ] Verify environment variables in `~/.env`:
    - `OLLAMA_BASE_URL=http://localhost:11434`
    - `LMQL_MODEL=gpt-oss:20b`
    - `LLAMACPP_MODEL_PATH=/Users/erlebach/data/llm_models/gpt-oss-20b-Q4_K_M.gguf`
    - `LLAMACPP_N_CTX=4096`
    - `LLAMACPP_N_GPU_LAYERS=35`
    - `LLAMACPP_TEMPERATURE=0.7`
    - `LLAMACPP_MAX_TOKENS=512`

**Acceptance Criteria**: All commands execute without errors, confirming both systems are ready for testing.

---

### T1.2: Install Required Dependencies
**Status**: ✅ Complete
**Priority**: High
**Description**: Install any missing Python packages required for benchmarking.

**Commands**:
```bash
pip install tabulate pyyaml
```

**Verify**:
```bash
python -c "import tabulate, yaml; print('Dependencies OK')"
```

**Acceptance Criteria**: All dependencies import without errors.

---

## Phase 2: Configuration Files

### T2.1: Create Benchmark Prompt Configuration (YAML)
**Status**: ✅ Complete
**Priority**: High
**Location**: `llamacpp_ollama/config/llm_benchmark_prompts.yaml`
**Description**: Create YAML configuration file with test prompts across three complexity categories.

**Requirements**:

- **Metadata section**: version, created_date, description
- **Short prompts** (< 50 tokens): 2-3 simple questions
    - Example: "What is 2+2? Answer with just the number."
    - Example: "Define 'machine learning' in one sentence."
- **Medium prompts** (50-200 tokens): 2-3 moderate complexity tasks
    - Example: "Explain the difference between supervised and unsupervised learning in 2-3 sentences."
- **Long prompts** (200-500 tokens): 2-3 complex tasks
    - Example: Grading assessment task with detailed instructions
- **Test configuration section**:
    - `repetitions: 3`
    - `warmup_iterations: 1`
    - `max_tokens: 512`
    - `temperature: 0.7`
    - `timeout_sec: 60`

**Acceptance Criteria**:

- YAML file is valid and parseable
- Contains 6-9 total prompts across 3 categories
- Each prompt has: category, complexity, prompt text, expected_tokens
- Test config section is complete

---

## Phase 3: Core Implementation

### T3.1: Create PerformanceMetrics Data Class
**Status**: ✅ Complete
**Priority**: High
**Location**: `llamacpp_ollama/compare_llm_performance.py`
**Description**: Implement dataclass to store performance metrics for each test run.

**Fields**:
```python
@dataclass
class PerformanceMetrics:
    provider: str                      # "ollama" or "llamacpp"
    prompt_id: str                     # e.g., "short_001"
    prompt_category: str               # "short", "medium", "long"
    model_load_time_sec: float         # Time to initialize model
    inference_time_sec: float          # Time to generate response
    tokens_generated: int              # Number of tokens in response
    tokens_per_sec: float              # Throughput metric
    response_text: str                 # Actual response content
    response_length_chars: int         # Response length in characters
    success: bool                      # True if test completed successfully
    error_message: Optional[str]       # Error details if failed
    timestamp: str                     # ISO 8601 timestamp
```

**Acceptance Criteria**: Dataclass is defined with all required fields and proper type annotations.

---

### T3.2: Implement BenchmarkRunner Class - Configuration Loading
**Status**: ✅ Complete
**Priority**: High
**Location**: `llamacpp_ollama/compare_llm_performance.py`
**Description**: Implement YAML configuration loading and validation.

**Methods**:
```python
class BenchmarkRunner:
    def __init__(self, config_path: str = "config/llm_benchmark_prompts.yaml"):
        """Initialize benchmark runner with configuration."""

    def load_prompts_from_yaml(self, config_path: str) -> dict:
        """Load and validate prompts from YAML configuration file."""
```

**Requirements**:

- Load YAML using `yaml.safe_load()`
- Validate required sections exist (metadata, prompts, test_config)
- Store prompts organized by category
- Store test configuration parameters
- Raise clear errors if configuration is invalid

**Acceptance Criteria**:

- Successfully loads valid YAML configuration
- Raises informative errors for invalid/missing configuration
- Returns structured data ready for benchmarking

---

### T3.3: Implement BenchmarkRunner - LLM Initialization
**Status**: ✅ Complete
**Priority**: High
**Dependencies**: T1.1, T1.2
**Location**: `llamacpp_ollama/compare_llm_performance.py`
**Description**: Implement methods to initialize both Ollama and Llama.cpp LLMs using existing config infrastructure.

**Methods**:
```python
def initialize_llm(self, provider: str):
    """Initialize LLM for specified provider using config/llm_config.py."""
    # Import from parent directory
    # Use configure_llm(provider) from config.llm_config
    # Time the initialization (cold start)
    # Store initialized LLM instance
    # Return initialization time
```

**Requirements**:

- Import and use `configure_llm()` from `../config/llm_config.py`
- Support both "ollama" and "llamacpp" providers
- Time model loading (cold start metric)
- Handle initialization errors gracefully
- Store LLM instances for reuse in warm tests

**Acceptance Criteria**:

- Both providers initialize successfully
- Initialization time is captured accurately
- Errors are caught and reported clearly

---

### T3.4: Implement BenchmarkRunner - Single Test Execution
**Status**: ✅ Complete
**Priority**: High
**Dependencies**: T3.1, T3.3
**Location**: `llamacpp_ollama/compare_llm_performance.py`
**Description**: Implement method to run a single inference test and collect metrics.

**Method**:
```python
def run_single_test(
    self,
    provider: str,
    prompt: str,
    prompt_id: str,
    category: str,
    is_warmup: bool = False
) -> PerformanceMetrics:
    """Run single inference test and collect performance metrics."""
```

**Requirements**:

- Start timer before inference
- Call LLM with prompt (use `.complete()` or similar method)
- End timer after response received
- Calculate tokens_per_sec (tokens / inference_time)
- Count tokens in response
- Catch and record any errors
- Return PerformanceMetrics instance
- If is_warmup=True, mark in output but don't count in stats

**Retry Logic**:

- Max 2 retries on failure
- Delay 2 seconds between retries
- Record final error if all retries fail

**Acceptance Criteria**:

- Successfully runs inference on both providers
- Timing is accurate (uses `time.perf_counter()`)
- All metrics are collected correctly
- Errors are handled without crashing

---

### T3.5: Implement BenchmarkRunner - Full Benchmark Suite
**Status**: ✅ Complete
**Priority**: High
**Dependencies**: T3.2, T3.4
**Location**: `llamacpp_ollama/compare_llm_performance.py`
**Description**: Implement orchestration method to run complete benchmark across all prompts and providers.

**Method**:
```python
def run_benchmark_suite(
    self,
    categories: Optional[List[str]] = None,
    repetitions: Optional[int] = None,
    skip_cold_start: bool = False,
    verbose: bool = False
) -> List[PerformanceMetrics]:
    """Run complete benchmark suite across all prompts and providers."""
```

**Execution Strategy**:

1. **Warm-up phase** (unless skip_cold_start):
    - Run warmup_iterations for each prompt (results discarded)
2. **Cold start tests** (unless skip_cold_start):
    - Reinitialize models fresh
    - Run each prompt once per provider
    - Measure total time including model loading
3. **Warm tests**:
    - Reuse loaded models
    - Run each prompt N times (repetitions)
    - Randomize provider order to avoid bias
    - Add 2-second delay between tests
4. **Progress reporting** (if verbose):
    - Print progress after each test
    - Show running time estimates

**Fair Comparison Controls**:

- Randomize provider order: `random.shuffle(["ollama", "llamacpp"])`
- Sequential execution (not parallel)
- Same prompts for both providers
- Same parameters (temp=0.7, max_tokens=512)

**Acceptance Criteria**:

- All prompts tested on both providers
- Repetitions executed correctly
- Progress is reported clearly (if verbose)
- Results list contains all expected metrics

---

### T3.6: Implement Statistical Analysis
**Status**: ✅ Complete
**Priority**: Medium
**Dependencies**: T3.5
**Location**: `llamacpp_ollama/compare_llm_performance.py`
**Description**: Implement statistical calculations for performance comparison.

**Method**:
```python
def calculate_statistics(self, results: List[PerformanceMetrics]) -> dict:
    """Calculate statistical summaries for each provider."""
```

**Statistics to Calculate**:
Per provider (Ollama, Llama.cpp):

- **Inference time**: mean, median, std dev, min, max
- **Tokens per second**: mean, median, std dev
- **Percentiles**: P95, P99 latency
- **Consistency**: Coefficient of variation (std_dev / mean)
- **Success rate**: successful_tests / total_tests
- **Error count**: Number of failed tests

Per category (short, medium, long):

- Same metrics as above, grouped by prompt category

**Comparison**:

- Winner by average inference time
- Winner by throughput (tokens/sec)
- Winner by consistency (lower CV)
- Percentage differences

**Acceptance Criteria**:

- All statistics calculated correctly
- Results organized by provider and category
- Clear winner identification
- Handles edge cases (all failures, high variance)

---

## Phase 4: Output and Reporting

### T4.1: Implement JSON Results Export
**Status**: ✅ Complete
**Priority**: Medium
**Dependencies**: T3.5, T3.6
**Location**: `llamacpp_ollama/compare_llm_performance.py`
**Description**: Export complete results to JSON format.

**Method**:
```python
def export_json(
    self,
    results: List[PerformanceMetrics],
    statistics: dict,
    output_dir: str
) -> str:
    """Export results to JSON file."""
```

**JSON Structure**:
```json
{
  "metadata": {
    "test_date": "ISO timestamp",
    "ollama_model": "gpt-oss:20b",
    "llamacpp_model": "path/to/model.gguf",
    "total_prompts": N,
    "total_tests": M
  },
  "configuration": { ... },
  "results": [ ... PerformanceMetrics as dicts ... ],
  "statistics": { ... calculated stats ... },
  "summary": {
    "winner": { ... }
  }
}
```

**Output**: `{output_dir}/results.json`

**Acceptance Criteria**: Valid JSON file with all results and metadata.

---

### T4.2: Implement Markdown Report Generation
**Status**: ✅ Complete
**Priority**: Medium
**Dependencies**: T3.6
**Location**: `llamacpp_ollama/compare_llm_performance.py`
**Description**: Generate human-readable Markdown report.

**Method**:
```python
def generate_markdown_report(
    self,
    statistics: dict,
    output_dir: str
) -> str:
    """Generate Markdown report with tables and summaries."""
```

**Report Sections**:

1. **Title and metadata**
2. **Configuration table** (models, settings)
3. **Overall summary table** (key metrics comparison)
4. **Performance by category** (3 tables: short, medium, long)
5. **Winner identification** with percentage improvements
6. **Recommendations** based on results

**Output**: `{output_dir}/report.md`

**Acceptance Criteria**:

- Valid Markdown formatting
- Tables are properly aligned
- Clear winner identification
- Easy to scan and understand

---

### T4.3: Implement CSV Export
**Status**: ✅ Complete
**Priority**: Low
**Dependencies**: T3.5
**Location**: `llamacpp_ollama/compare_llm_performance.py`
**Description**: Export flat CSV file for spreadsheet analysis.

**Method**:
```python
def export_csv(
    self,
    results: List[PerformanceMetrics],
    output_dir: str
) -> str:
    """Export results to CSV file."""
```

**CSV Columns**:
```
provider,prompt_id,category,load_time_sec,inference_time_sec,tokens_generated,tokens_per_sec,success,error_message,timestamp
```

**Output**: `{output_dir}/results.csv`

**Acceptance Criteria**: Valid CSV with one row per test result.

---

### T4.4: Implement Terminal Summary Output
**Status**: ✅ Complete
**Priority**: High
**Dependencies**: T3.6
**Location**: `llamacpp_ollama/compare_llm_performance.py`
**Description**: Print summary table to terminal during and after execution.

**Method**:
```python
def print_terminal_summary(self, statistics: dict):
    """Print formatted summary table to terminal using tabulate."""
```

**Use**: `tabulate` library for nice formatting

**Output Example**:
```
┌──────────────────────────────────────────────────┐
│   LLM Performance Comparison Results             │
├──────────────────────────────────────────────────┤
│                                                  │
│  Overall Summary                                 │
│  ───────────────────────────────────────────     │
│  Metric          Ollama      Llama.cpp   Winner  │
│  ─────────────────────────────────────────────   │
│  Avg Latency     2.45s       3.12s       Ollama  │
│  Avg Tokens/sec  38.7        28.3        Ollama  │
│  Success Rate    100%        98%         Ollama  │
│                                                  │
└──────────────────────────────────────────────────┘
```

**Acceptance Criteria**:

- Clear, readable terminal output
- Tables properly aligned
- Winner clearly identified

---

## Phase 5: Command-Line Interface

### T5.1: Implement CLI Argument Parsing
**Status**: ✅ Complete
**Priority**: High
**Dependencies**: T3.2
**Location**: `llamacpp_ollama/compare_llm_performance.py`
**Description**: Implement command-line argument parsing for flexible execution.

**Arguments**:
```python
--config PATH              # Path to YAML config (default: config/llm_benchmark_prompts.yaml)
--output-dir PATH          # Output directory (default: results/llm_comparison_TIMESTAMP)
--categories CATS          # Comma-separated categories to test (default: all)
--repetitions N            # Number of repetitions per prompt (default: 3)
--skip-cold-start          # Skip cold start tests (faster)
--verbose                  # Enable verbose output
--help                     # Show help message
```

**Use**: `argparse` library

**Acceptance Criteria**:

- All arguments parsed correctly
- Help message is clear and complete
- Defaults work as expected
- Invalid arguments show helpful errors

---

### T5.2: Implement Main Entry Point
**Status**: ✅ Complete
**Priority**: High
**Dependencies**: T3.5, T4.1, T4.2, T4.3, T4.4, T5.1
**Location**: `llamacpp_ollama/compare_llm_performance.py`
**Description**: Implement main() function to orchestrate complete benchmark workflow.

**Workflow**:
```python
def main():
    # 1. Parse CLI arguments
    # 2. Load configuration from YAML
    # 3. Create output directory with timestamp
    # 4. Initialize BenchmarkRunner
    # 5. Run benchmark suite
    # 6. Calculate statistics
    # 7. Generate all output formats (JSON, MD, CSV, terminal)
    # 8. Print final summary
    # 9. Print output file locations
```

**Error Handling**:

- Wrap in try/except to catch and report errors
- Provide helpful error messages
- Exit with proper exit codes (0=success, 1=error)

**Acceptance Criteria**:

- Complete end-to-end execution
- All outputs generated correctly
- Errors handled gracefully
- User sees clear progress and results

---

## Phase 6: Testing and Validation

### T6.1: Unit Test - Configuration Loading
**Status**: ✅ Complete
**Priority**: Medium
**Dependencies**: T2.1, T3.2
**Description**: Test that configuration loading works correctly.

**Test**:
```bash
python -c "from compare_llm_performance import BenchmarkRunner; \
           runner = BenchmarkRunner('config/llm_benchmark_prompts.yaml'); \
           print(f'Loaded {len(runner.prompts)} prompts')"
```

**Acceptance Criteria**:

- Prints expected number of prompts
- No errors or exceptions

---

### T6.2: Unit Test - LLM Initialization
**Status**: ✅ Complete
**Priority**: Medium
**Dependencies**: T1.1, T3.3
**Description**: Test that both LLMs initialize correctly.

**Test**:
```bash
python -c "from compare_llm_performance import BenchmarkRunner; \
           runner = BenchmarkRunner(); \
           runner.initialize_llm('ollama'); \
           runner.initialize_llm('llamacpp'); \
           print('Both LLMs initialized successfully')"
```

**Acceptance Criteria**:

- Both LLMs initialize without errors
- Success message printed

---

### T6.3: Integration Test - Single Category
**Status**: ✅ Complete
**Priority**: High
**Dependencies**: T5.2
**Description**: Run benchmark on single category to verify end-to-end functionality.

**Test**:
```bash
cd llamacpp_ollama
python compare_llm_performance.py --categories short --repetitions 1
```

**Expected Output**:

- Terminal shows progress
- Creates output directory with timestamp
- Generates results.json with 2 test results (1 per provider)
- Generates report.md with summary table
- Generates results.csv with 2 rows
- Terminal displays final summary

**Acceptance Criteria**:

- All output files created
- No errors during execution
- Results look reasonable (positive times, plausible token counts)

---

### T6.4: Integration Test - Full Benchmark
**Status**: ✅ Complete
**Priority**: High
**Dependencies**: T6.3
**Description**: Run complete benchmark with all categories and repetitions.

**Test**:
```bash
cd llamacpp_ollama
python compare_llm_performance.py --repetitions 3 --verbose
```

**Expected Results**:

- All prompts tested on both providers
- 3 repetitions per prompt
- Verbose output shows progress
- Statistical summary shows clear winner
- All output files complete and properly formatted

**Acceptance Criteria**:

- All tests complete successfully
- Results are consistent across repetitions
- Clear performance differences identified
- No crashes or errors

---

## Phase 7: Analysis and Documentation

### T7.1: Analyze Results
**Status**: ✅ Complete
**Priority**: High
**Dependencies**: T6.4
**Description**: Review benchmark results to identify performance characteristics and issues.

**Analysis Tasks**:

- Compare average latency (Ollama vs Llama.cpp)
- Compare throughput (tokens/sec)
- Check consistency (coefficient of variation)
- Identify error rates
- Determine overall winner
- Identify specific scenarios where each provider excels
- Look for patterns (e.g., Llama.cpp slower on long prompts?)

**Questions to Answer**:

1. Which provider is faster overall?
2. By how much (percentage)?
3. Is one more consistent than the other?
4. Are there category-specific differences?
5. What is "not quite right with Llama.cpp"? (if anything)

**Deliverable**: Analysis notes in `results/analysis_notes.md`

**Acceptance Criteria**:

- Clear understanding of performance differences
- Root cause hypothesis for any Llama.cpp issues
- Recommendations for optimization or provider choice

---

### T7.2: Create README Documentation
**Status**: ✅ Complete
**Priority**: Medium
**Dependencies**: T7.1
**Location**: `llamacpp_ollama/README.md`
**Description**: Create comprehensive README for the benchmark tool.

**Sections**:

1. **Overview**: What this tool does
2. **Prerequisites**: System requirements and setup
3. **Installation**: Dependencies and configuration
4. **Usage**: Command-line examples and options
5. **Configuration**: How to modify prompts and settings
6. **Output**: Description of output formats and locations
7. **Interpreting Results**: How to read and understand the reports
8. **Troubleshooting**: Common issues and solutions
9. **Results Summary**: Key findings from initial benchmarks

**Acceptance Criteria**:

- Complete, clear documentation
- Examples that can be copy-pasted
- Helpful for future users

---

## Phase 8: Constrained Generation & JSON Mode

### T8.1: Investigate JSON Output Issues
**Status**: ✅ Complete
**Priority**: High
**Dependencies**: T6.4, T7.1
**Description**: Investigate why LlamaCPP generates meta-commentary instead of direct JSON responses.

**Findings**:

- LlamaCPP was generating reasoning/thinking text instead of JSON
- Root cause: Missing GBNF grammar constraints
- Ollama appeared cleaner due to hidden `thinking` field in responses
- Both models actually generate similar amounts of reasoning

**Key Discovery**:

From `constrained_grammars.md` and Perplexity research:

- Ollama uses GBNF grammar constraints when `format: json` is set
- LlamaCPP requires explicit `LlamaGrammar` object
- Without grammar: models rely on instruction following (unreliable)
- With grammar: logit masking forces valid JSON token selection

**Acceptance Criteria**: ✅ Root cause identified and documented

---

### T8.2: Implement GBNF JSON Grammar for LlamaCPP
**Status**: ✅ Complete
**Priority**: High
**Dependencies**: T8.1
**Location**: `config/llm_config.py`
**Description**: Implement GBNF JSON grammar constraint for LlamaCPP to force valid JSON output.

**Implementation**:

```python
from llama_cpp import LlamaGrammar

json_grammar = LlamaGrammar.from_string(r'''
root   ::= object
value  ::= object | array | string | number | ("true" | "false" | "null") ws
object ::= "{" ws (string ":" ws value ("," ws string ":" ws value)*)? "}" ws
...
''')

llm_kwargs["generate_kwargs"] = {
    "grammar": json_grammar,
    ...
}
```

**Key Features**:

- Uses BNF grammar specification for JSON
- Forces token selection to only JSON-valid tokens (logit masking)
- Equivalent to `--grammar-file json.gbnf` in CLI
- Works at the inference engine level, not prompt level

**Test Results**:

- ✅ Generates valid JSON: `{"answer": "Paris"}`
- ✅ No meta-commentary
- ✅ Only 13 tokens (efficient)

**Acceptance Criteria**: ✅ LlamaCPP reliably generates valid JSON

---

### T8.3: Enable JSON Mode for Ollama
**Status**: ✅ Complete
**Priority**: High
**Dependencies**: T8.1
**Location**: `config/llm_config.py`
**Description**: Enable Ollama's JSON mode to apply GBNF grammar constraints for fair comparison.

**Important Correction**:

- **FALSE**: "Ollama automatically applies GBNF grammar constraints"
- **TRUE**: Ollama only applies grammar when explicitly requested via `json_mode=True` or `format: json`

**Implementation**:
```python
return Ollama(
    model=model_name,
    base_url=base_url,
    request_timeout=120.0,
    json_mode=True  # Enable JSON constrained generation
)
```

**Fair Comparison**:

- **Before**: Ollama (no grammar) vs LlamaCPP (no grammar) - unfair due to different chat templates
- **After**: Ollama (grammar) vs LlamaCPP (grammar) - both use same constraint mechanism

**Acceptance Criteria**: ✅ Both providers use GBNF grammar constraints

---

### T8.4: Implement Actual Token Counting
**Status**: ✅ Complete
**Priority**: High
**Dependencies**: T8.1
**Location**: `llamacpp_ollama/compare_llm_performance.py`
**Description**: Replace character-based token estimation with actual token counts from LLM APIs.

**Implementation**:
```python
def get_token_count(raw_response: dict, provider: str) -> int:
    """Extract actual token count from raw LLM response."""
    if provider == "ollama":
        return raw_response.get("eval_count", 0)
    elif provider == "llamacpp":
        usage = raw_response.get("usage", {})
        return usage.get("completion_tokens", 0)
    return 0
```

**Key Changes**:

- Counts ALL tokens including thinking/reasoning
- No more `tokens = chars // 4` approximation
- Fair comparison of true inference speed
- Extracts from `response.raw` API responses

**Example**:

- Ollama: 72 tokens (actual count, includes hidden thinking)
- LlamaCPP: 13 tokens (actual count with grammar)

**Acceptance Criteria**: ✅ Using real token counts from APIs

---

### T8.5: Add JSON Extraction Functions
**Status**: ✅ Complete
**Priority**: Medium
**Dependencies**: T8.2
**Location**: `llamacpp_ollama/compare_llm_performance.py`
**Description**: Implement functions to extract clean answers from JSON responses.

**Implementation**:
```python
def extract_json_answer(response_text: str) -> tuple[str, str]:
    """Extract answer from JSON response.

    Returns:
        Tuple of (extracted_answer, full_response_text)
    """
    # Try to parse as JSON
    # Extract "answer" field
    # Fallback to full text if no JSON found
```

**New Fields in PerformanceMetrics**:

- `response_text`: Full response including thinking/reasoning
- `extracted_answer`: Clean answer from JSON "answer" field

**Acceptance Criteria**: ✅ Can extract clean answers from JSON responses

---

### T8.6: Add Progress Indicators and Timestamps
**Status**: ✅ Complete
**Priority**: Medium
**Dependencies**: None
**Location**: `llamacpp_ollama/compare_llm_performance.py`
**Description**: Add timestamps and unbuffered output to track benchmark progress.

**Implementation**:

- Added `Start time:` and `End time:` timestamps at:
  - Overall benchmark start/end
  - Each provider start/end
- Added `flush=True` to all print statements
- Run Python with `-u` (unbuffered) flag
- Helps distinguish between frozen/running/complete states

**Example Output**:
```
============================================================
Starting Benchmark Suite
============================================================
Start time: 2026-01-28 13:30:45
Providers: ollama, llamacpp
...
End time: 2026-01-28 13:45:12
```

**Acceptance Criteria**: ✅ Can monitor benchmark progress in real-time

---

### T8.7: Remove Custom Chat Template
**Status**: ✅ Complete
**Priority**: High
**Dependencies**: T8.2
**Location**: `config/llm_config.py`
**Description**: Remove problematic custom `messages_to_prompt` function that caused meta-commentary.

**Rationale**:

- Custom template was causing model to narrate reasoning process
- Default template + JSON grammar works better
- Let LlamaCPP use model's built-in chat template

**Changes**:

- Removed: `"messages_to_prompt": gpt_oss_messages_to_prompt`
- Added: `"grammar": json_grammar` (replaces template-based control)
- Result: Clean JSON output without meta-commentary

**Acceptance Criteria**: ✅ Using default chat template with grammar constraints

---

## Phase 9: Fair Comparison & Final Analysis

### T9.1: Run Fair Comparison Benchmark
**Status**: 🔄 In Progress
**Priority**: High
**Dependencies**: T8.2, T8.3, T8.4, T8.6
**Location**: `llamacpp_ollama/`
**Description**: Run comprehensive benchmark with both providers using JSON mode for fair comparison.

**Configuration**:

- Ollama: `json_mode=True` (GBNF grammar enabled)
- LlamaCPP: `grammar=json_grammar` (GBNF grammar enabled)
- All prompts request JSON format: `{"answer": "..."}`
- Actual token counting from API responses
- Progress indicators with timestamps

**Command**:
```bash
python3 -u compare_llm_performance.py \
  --config config/llm_benchmark_prompts.yaml \
  --providers ollama,llamacpp \
  --categories short,medium,long \
  --repetitions 2 \
  --verbose
```

**Expected Outcomes**:

- Both providers generate valid JSON
- Token counts include all generated tokens (thinking + answer)
- Fair speed comparison with same constraints
- Clean JSON extraction for answer comparison

**Acceptance Criteria**: ⏳ Fair benchmark completes with both providers using grammar

---

### T9.2: Analyze Token-Accurate Results
**Status**: ⏳ Pending
**Priority**: High
**Dependencies**: T9.1
**Description**: Analyze benchmark results with accurate token counts and JSON constraints.

**Analysis Focus**:

1. **True Speed Comparison**:

    - Compare inference time with equal grammar constraints
    - Tokens/sec with actual token counts
    - Impact of JSON grammar on performance

2. **Token Generation Patterns**:

    - How many tokens does each provider actually generate?
    - Are token counts similar with grammar constraints?
    - Does grammar reduce verbosity equally?

3. **Quality Assessment**:

    - JSON validity rate
    - Answer extraction success rate
    - Consistency across repetitions

4. **Grading Use Case Projection**:

    -  Performance on long prompts (rubrics + answers)
    - Reliability with constrained generation
    - Recommendation for production use

**Deliverable**: Updated `results/analysis_notes.md` with fair comparison findings

**Acceptance Criteria**: ⏳ Complete analysis with accurate token counts

---

### T9.3: Update Documentation with Findings
**Status**: ⏳ Pending
**Priority**: Medium
**Dependencies**: T9.2
**Locations**: `README.md`, `results/analysis_notes.md`, `TASK_LIST.md`
**Description**: Update all documentation with constrained generation findings.

**Updates Needed**:

1. **README.md**:

    - Explain JSON mode configuration for both providers
    - Document GBNF grammar implementation
    - Add note about Ollama's optional grammar (not automatic)
    - Link to `constrained_grammars.md`

2. **analysis_notes.md**:

    - Add section on constrained vs unconstrained comparison
    - Update performance numbers with actual token counts
    - Explain grammar impact on speed and quality
    - Revise recommendations based on fair comparison

3. **TASK_LIST.md**:

    - Mark T9.1, T9.2, T9.3 as complete when done
    - Update summary statistics
    - Add lessons learned section

**Key Points to Document**:

- Ollama does NOT automatically apply grammar constraints
- JSON mode must be explicitly enabled for both providers
- GBNF grammar = logit masking at inference level
- Actual token counts essential for fair comparison
- Both providers generate similar reasoning (thinking vs content)

**Acceptance Criteria**: ✅ All documentation reflects accurate findings

---

## Phase 10: Batch Inference Benchmarking

### T10.1: Design Batch Benchmark Architecture
**Status**: ✅ Complete
**Priority**: High
**Location**: `llamacpp_ollama/batch_benchmark.py`
**Description**: Design architecture for batch inference benchmarking to measure speedup from processing multiple requests simultaneously.

**Design Requirements**:

- Measure both wall-clock and CPU time
- Compare sequential (batch_size=1) vs batch processing (batch_size=4,8)
- Use identical prompts N times for objective comparison
- Calculate speedup vs ideal (batch_size)
- Report efficiency percentage (actual_speedup / ideal_speedup * 100)

**Metrics to Collect**:

- Wall-clock time (what users experience)
- CPU time (reproducible, system-independent)
- Total tokens generated
- Tokens/sec (wall and CPU)
- Speedup vs sequential baseline
- Efficiency percentage

**Acceptance Criteria**: ✅ Architecture designed and documented

---

### T10.2: Implement Sequential Baseline
**Status**: ✅ Complete
**Priority**: High
**Dependencies**: T10.1
**Location**: `llamacpp_ollama/batch_benchmark.py`
**Description**: Implement baseline sequential inference function that processes prompts one at a time.

**Implementation**:
```python
def run_sequential_inference(llm, prompt, n) -> tuple[float, float, list[str], int]:
    """Run N inferences sequentially.
    Returns: (wall_time, cpu_time, responses, total_tokens)
    """
    # Use time.time() for wall-clock
    # Use time.process_time() for CPU time
    # Process one request at a time
    # Extract token counts from API responses
```

**Acceptance Criteria**: ✅ Sequential baseline implemented with accurate timing

---

### T10.3: Implement Batch Inference (n=4,8)
**Status**: ⏳ Pending
**Priority**: High
**Dependencies**: T10.2
**Location**: `llamacpp_ollama/batch_benchmark.py`
**Description**: Implement true batch processing using llama-cpp-python's native batch API.

**Current Implementation**:

- Using sequential processing with KV cache sharing (relies on identical prompts)
- llama.cpp recognizes identical prefixes and shares computation

**Needed Improvement**:

- Use llama-cpp-python's `Llama` class directly with `n_batch` parameter
- Configure proper batch processing:
  ```python
  from llama_cpp import Llama
  llm = Llama(
      model_path=model_path,
      n_batch=batch_size,  # Enable batch processing
      n_ctx=4096,
      n_gpu_layers=35
  )
  ```

- Use `.create_completion()` with batch of identical prompts
- Measure true parallel processing speedup

**Acceptance Criteria**: ⏳ Batch inference uses native llama.cpp batch API

---

### T10.4: Add CPU Time Measurement
**Status**: ⏳ Pending
**Priority**: Medium
**Dependencies**: T10.2, T10.3
**Location**: `llamacpp_ollama/batch_benchmark.py`
**Description**: Ensure all timing measurements include both wall-clock and CPU time.

**Implementation**:

- Use `time.process_time()` for CPU time (user + system time spent in process)
- Use `time.time()` for wall-clock time (actual elapsed time)
- Report both metrics separately
- Calculate tokens/sec for both

**Benefits**:

- **CPU time** is reproducible across different system loads
- **Wall-clock time** is what users actually experience
- Comparison helps identify if slowdowns are from CPU contention vs model processing

**Acceptance Criteria**: ⏳ All results report both wall-clock and CPU time

---

### T10.5: Run Batch Benchmarks
**Status**: ⏳ Pending
**Priority**: High
**Dependencies**: T10.3, T10.4
**Description**: Run batch inference benchmarks with batch sizes 4 and 8 across short, medium, and long prompts.

**Test Plan**:

```bash
cd llamacpp_ollama
python3 -u batch_benchmark.py \
    --batch-sizes 4,8 \
    --prompts short,medium,long \
    --verbose 2>&1 | tee batch_results_$(date +%Y%m%d_%H%M%S).log
```

**Expected Behavior**:

- Batch size 4 should show ~2-3x speedup (50-75% efficiency)
- Batch size 8 should show ~3-6x speedup (37-75% efficiency)
- Longer prompts may show better batch efficiency (more computation to parallelize)

**Acceptance Criteria**: ⏳ Benchmark completes and produces results for all batch sizes

---

### T10.6: Analyze Batch Speedup Results
**Status**: ⏳ Pending
**Priority**: High
**Dependencies**: T10.5
**Description**: Analyze batch benchmark results and determine optimal batch size for grading pipeline.

**Analysis Questions**:

1. What speedup does batch_size=4 achieve? (ideal: 4x)
2. What speedup does batch_size=8 achieve? (ideal: 8x)
3. Do longer prompts benefit more from batching?
4. What is the efficiency percentage for each batch size?
5. Is there diminishing returns beyond batch_size=4?

**Recommendations to Generate**:

- Optimal batch size for grading pipeline
- Expected throughput improvement
- Memory considerations (batch size vs context window)

**Acceptance Criteria**: ⏳ Analysis complete with recommendation for production use

---

## Phase 11: Quality & Optimization

### T11.1: Fix LlamaCPP Whitespace Padding
**Status**: ✅ Partially Complete (50%)
**Priority**: High
**Location**: `config/llm_config.py`
**Description**: Fix LlamaCPP generating excessive whitespace after JSON responses.

**Current Issue**:

- LlamaCPP generates valid JSON: `{"answer":"Paris"}`
- Then pads with whitespace until hitting max_tokens=512
- Wastes tokens and time (~500 extra tokens per response)

**Root Cause**:

- Grammar allows whitespace after JSON: `ws ::= [ \t\n]*`
- Model continues generating until max_tokens

**Solutions Attempted**:

1. ❌ **Stricter stop sequences**: Added `}\n` → caused initialization hang
2. ✅ **Lower max_tokens**: Reduced from 512 to 256 (50% reduction in padding)
3. ❌ **Grammar refinement**: Modified grammar to limit trailing ws → caused segfault
4. ⏳ **Use `finish_reason`**: Not yet tested

**Current State**:

- ✅ max_tokens reduced to 256 (prevents >256 token padding)
- ⏳ Need to test actual impact on responses
- ⏳ May need different approach for full fix (e.g., post-processing trimming)

**Acceptance Criteria**: 🔄 LlamaCPP generates <100 tokens for simple JSON responses (currently: ~256 max vs 512 before)

---

### T11.2: Implement Incremental Results Writing
**Status**: ⏳ Pending
**Priority**: High
**Location**: `llamacpp_ollama/compare_llm_performance.py`, `batch_benchmark.py`
**Description**: Write results incrementally to avoid data loss on crashes/interruptions.

**Current Problem**:

- Results buffered in memory
- Only written at end of benchmark
- If process crashes, **all data is lost**

**Implementation**:

```python
def run_benchmark_suite(...):
    results_file = output_dir / "results.jsonl"  # JSON Lines format

    for test in tests:
        result = run_single_test(...)

        # Write immediately after each test
        with open(results_file, "a") as f:
            f.write(json.dumps(asdict(result)) + "\n")
            f.flush()  # Force write to disk
```

**Benefits**:

- No data loss on crashes
- Can monitor progress by tailing results file
- Easy to resume interrupted benchmarks

**Acceptance Criteria**: ⏳ Results written after each test completion

---

### T11.3: Add Run Description to Reports
**Status**: ⏳ Pending
**Priority**: Medium
**Location**: Report generation code
**Description**: Add meaningful descriptions to result folders and reports to distinguish different runs.

**Current Problem**:

- Folders named `llm_comparison_20260128_144338/`
- No description of what each run tested
- Difficult to distinguish: "Was this with grammar? Without? Batch size 4?"

**Implementation**:

1. **Add --description CLI flag**:
   ```bash
   python compare_llm_performance.py \
       --description "Fair comparison: both providers with JSON grammar" \
       ...
   ```

2. **Include in folder name**:
   ```
   results/fair_json_comparison_20260128_144338/
   results/batch_size_4_20260128_150000/
   ```

3. **Add to report header**:
   ```markdown
   # LLM Performance Comparison Report

   **Run Description**: Fair comparison with both providers using JSON grammar constraints
   **Generated**: 2026-01-28 14:54:53
   ```

4. **Add metadata to results.json**:
   ```json
   {
     "metadata": {
       "description": "Fair comparison: both providers with JSON grammar",
       "timestamp": "2026-01-28T14:54:53",
       ...
     }
   }
   ```

**Acceptance Criteria**: ⏳ All reports include run description

---

## Summary

**Total Tasks**: 43 (Updated 2026-01-28 14:56)
**Completed**: 32
**In Progress**: 1
**Pending**: 10
**High Priority**: 29
**Medium Priority**: 13
**Low Priority**: 1

**Completion Status by Phase**:

1. ✅ Phase 1: Prerequisites (T1.1, T1.2) - Complete
2. ✅ Phase 2: Configuration (T2.1) - Complete
3. ✅ Phase 3: Core Implementation (T3.1 → T3.6) - Complete
4. ✅ Phase 4: Output (T4.1 → T4.4) - Complete
5. ✅ Phase 5: CLI (T5.1, T5.2) - Complete
6. ✅ Phase 6: Testing (T6.1 → T6.4) - Complete
7. ✅ Phase 7: Documentation (T7.1, T7.2) - Complete
8. ✅ Phase 8: Constrained Generation (T8.1 → T8.7) - Complete
9. ✅ Phase 9: Fair Comparison (T9.1 → T9.3) - Complete
10. 🔄 Phase 10: Batch Inference (T10.1 → T10.6) - In Progress
11. ⏳ Phase 11: Quality & Optimization (T11.1 → T11.3) - Pending

**Total Tasks**: 31 (Updated 2026-01-28)
**Completed**: 28
**In Progress**: 1
**Pending**: 2
**High Priority**: 21
**Medium Priority**: 9
**Low Priority**: 1

**Completion Status by Phase**:

1. ✅ Phase 1: Prerequisites (T1.1, T1.2) - Complete
2. ✅ Phase 2: Configuration (T2.1) - Complete
3. ✅ Phase 3: Core Implementation (T3.1 → T3.6) - Complete
4. ✅ Phase 4: Output (T4.1 → T4.4) - Complete
5. ✅ Phase 5: CLI (T5.1, T5.2) - Complete
6. ✅ Phase 6: Testing (T6.1 → T6.4) - Complete
7. ✅ Phase 7: Documentation (T7.1, T7.2) - Complete
8. ✅ Phase 8: Constrained Generation (T8.1 → T8.7) - Complete
9. 🔄 Phase 9: Fair Comparison (T9.1 → T9.3) - In Progress

**Current Status**:

- **Phase 9**: ✅ Complete - Fair comparison shows LlamaCPP 1.57x faster
- **Phase 10**: 🔄 In Progress - Batch inference benchmarking
  - **T10.1, T10.2**: ✅ Architecture designed and sequential baseline implemented
  - **T10.3**: ⏳ Need to implement native llama.cpp batch API
  - **T10.5**: ⏳ Ready to run batch benchmarks once T10.3 complete
- **Phase 11**: ⏳ Pending - Quality improvements needed (whitespace padding, incremental writes)

**Key Achievements**:

- ✅ Implemented GBNF JSON grammar for constrained generation
- ✅ Fixed token counting to use actual API counts (not approximation)
- ✅ Completed fair comparison: LlamaCPP 1.57x faster, 2.4x on long prompts
- ✅ Added progress monitoring with timestamps and unbuffered output
- ✅ Documented constrained generation mechanism (logit masking)
- ✅ Designed batch inference benchmark architecture
- 🔄 Implementing native batch processing for throughput testing

**Lessons Learned**:

1. **Ollama does NOT automatically apply grammar** - must explicitly enable `json_mode=True`
2. **GBNF grammar = logit masking** at inference level (not prompt-based)
3. **Token counts matter** - both providers generate reasoning, but Ollama hides it in `thinking` field
4. **Custom chat templates can hurt** - removed in favor of default + grammar constraints
5. **Quantization affects instruction following** - grammar constraints bypass this issue

---

**Notes**:

- All file paths are relative to `llamacpp_ollama/` directory
- Configuration references `../config/llm_config.py` from parent autograder directory
- Follow CLAUDE.md principles: YAML configs, no hardcoding, transparency
- Use existing patterns from `../tests/test_llama_cpp.py`
