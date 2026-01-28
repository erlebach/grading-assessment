# Task List: LLM Performance Comparison Tool (Ollama vs Llama.cpp)

**Project**: Benchmark and compare Ollama vs Llama.cpp performance with OSS 20B model
**Session**: autograder_2026-01-25
**Created**: 2026-01-28
**Last Updated**: 2026-01-28 10:15

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
| **TOTAL** | **21** | **21** | **✅ 100% Complete** |

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

## Additional Work Completed

| Task | Description | Status |
|------|-------------|--------|
| **LlamaCPP Chat Template Fix** | Added custom `gpt_oss_messages_to_prompt()` function to properly format chat messages for gpt-oss model | ✅ Complete |
| **Stop Sequences Configuration** | Configured proper stop sequences (`<|return|>`, `<|end|>`, `<|endoftext|>`) for LlamaCPP | ✅ Complete |
| **Output Directory Fix** | Fixed hardcoded path from `llamacpp_ollama/results/` to `results/` | ✅ Complete |
| **Comprehensive Benchmarks** | Ran full benchmarks across all categories (short, medium, long) with 3 repetitions | ✅ Complete |
| **Performance Analysis** | Analyzed results showing LlamaCPP is 7.6x faster overall with dramatic improvements on medium/long prompts | ✅ Complete |

## Key Findings

**LlamaCPP Performance Results:**
- **7.6x faster** overall than Ollama (660% improvement)
- **13.4x faster** on medium prompts
- **7.5x faster** on long prompts with 71.1 tokens/sec throughput
- **100% success rate** across all 27 tests
- All LLM responses saved in JSON/CSV for analysis

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

## Summary

**Total Tasks**: 23
**High Priority**: 13
**Medium Priority**: 7
**Low Priority**: 1

**Estimated Completion Order**:
1. Phase 1: Prerequisites (T1.1, T1.2)
2. Phase 2: Configuration (T2.1)
3. Phase 3: Core Implementation (T3.1 → T3.6)
4. Phase 4: Output (T4.1 → T4.4)
5. Phase 5: CLI (T5.1, T5.2)
6. Phase 6: Testing (T6.1 → T6.4)
7. Phase 7: Analysis (T7.1, T7.2)

**Next Steps**:
1. Start with T1.1 to verify prerequisites
2. Install dependencies (T1.2)
3. Create YAML config (T2.1)
4. Begin core implementation starting with T3.1

---

**Notes**:
- All file paths are relative to `llamacpp_ollama/` directory
- Configuration references `../config/llm_config.py` from parent autograder directory
- Follow CLAUDE.md principles: YAML configs, no hardcoding, transparency
- Use existing patterns from `../tests/test_llama_cpp.py`
