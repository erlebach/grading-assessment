#!/usr/bin/env python3
"""LLM Performance Comparison Tool: Ollama vs Llama.cpp

This script benchmarks and compares response times and performance between
Ollama and Llama.cpp using the OSS 20B model.

Usage:
    python compare_llm_performance.py
    python compare_llm_performance.py --config path/to/prompts.yaml
    python compare_llm_performance.py --repetitions 5 --verbose
"""

import argparse
import csv
import json
import random
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml
from tabulate import tabulate

# Add parent directory to path to import config module
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.llm_config import configure_llm
from llama_index.core.llms import ChatMessage


@dataclass
class PerformanceMetrics:
    """Metrics for a single LLM inference test."""

    provider: str  # "ollama" or "llamacpp"
    prompt_id: str
    prompt_category: str
    model_load_time_sec: float
    inference_time_sec: float
    tokens_generated: int
    tokens_per_sec: float
    response_text: str
    response_length_chars: int
    success: bool
    error_message: Optional[str]
    timestamp: str
    is_warmup: bool = False


@dataclass
class ProviderStatistics:
    """Aggregated statistics for a provider."""

    provider: str
    total_tests: int
    successful_tests: int
    failed_tests: int
    mean_inference_time: float
    median_inference_time: float
    std_dev_inference_time: float
    p95_inference_time: float
    p99_inference_time: float
    mean_tokens_per_sec: float
    median_tokens_per_sec: float
    mean_model_load_time: float
    category_breakdown: dict[str, dict[str, float]] = field(default_factory=dict)


class BenchmarkRunner:
    """Manages LLM benchmarking across providers."""

    def __init__(self, config_path: str = "llamacpp_ollama/config/llm_benchmark_prompts.yaml"):
        """Initialize benchmark runner.

        Args:
            config_path: Path to YAML configuration file with prompts.
        """
        self.config_path = Path(config_path)
        self.prompts = []
        self.config = {}
        self.results: list[PerformanceMetrics] = []
        self.load_prompts_from_yaml()

    def load_prompts_from_yaml(self) -> None:
        """Load test prompts and configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path) as f:
            data = yaml.safe_load(f)

        self.config = data.get("config", {})
        self.prompts = data.get("prompts", [])

        print(f"✓ Loaded {len(self.prompts)} prompts from {self.config_path}")
        print(f"  Repetitions: {self.config.get('repetitions', 3)}")
        print(f"  Warmup iterations: {self.config.get('warmup_iterations', 1)}")
        print(f"  Max tokens: {self.config.get('max_tokens', 512)}")
        print(f"  Temperature: {self.config.get('temperature', 0.7)}")

    def initialize_llm(self, provider: str, verbose: bool = False) -> Any:
        """Initialize LLM for the specified provider.

        Args:
            provider: "ollama" or "llamacpp"
            verbose: Print initialization details

        Returns:
            Configured LLM instance
        """
        if verbose:
            print(f"\nInitializing {provider} LLM...")

        start_time = time.time()
        llm = configure_llm(provider)
        load_time = time.time() - start_time

        if verbose:
            print(f"✓ {provider} initialized in {load_time:.2f}s")

        return llm, load_time

    def run_single_test(
        self,
        provider: str,
        llm: Any,
        prompt_config: dict,
        is_warmup: bool = False,
        verbose: bool = False,
        model_load_time: float = 0.0,
    ) -> PerformanceMetrics:
        """Run a single benchmark test.

        Args:
            provider: Provider name
            llm: LLM instance
            prompt_config: Prompt configuration dict
            is_warmup: Whether this is a warmup run
            verbose: Print test details
            model_load_time: Time to load the model (cold start)

        Returns:
            PerformanceMetrics for this test
        """
        prompt_id = prompt_config["id"]
        category = prompt_config["category"]
        prompt_text = prompt_config["prompt"]

        if verbose and not is_warmup:
            print(f"  Testing {provider} on {prompt_id} ({category})...", end=" ", flush=True)

        metrics = PerformanceMetrics(
            provider=provider,
            prompt_id=prompt_id,
            prompt_category=category,
            model_load_time_sec=model_load_time,
            inference_time_sec=0.0,
            tokens_generated=0,
            tokens_per_sec=0.0,
            response_text="",
            response_length_chars=0,
            success=False,
            error_message=None,
            timestamp=datetime.now().isoformat(),
            is_warmup=is_warmup,
        )

        try:
            start_time = time.time()
            # Use chat method for proper formatting and stop sequence handling
            messages = [ChatMessage(role="user", content=prompt_text)]
            response = llm.chat(messages)
            inference_time = time.time() - start_time

            response_text = str(response.message.content)
            response_length = len(response_text)

            # Estimate tokens (rough approximation: 1 token ≈ 4 characters)
            tokens_generated = response_length // 4
            tokens_per_sec = tokens_generated / inference_time if inference_time > 0 else 0.0

            metrics.inference_time_sec = inference_time
            metrics.tokens_generated = tokens_generated
            metrics.tokens_per_sec = tokens_per_sec
            metrics.response_text = response_text
            metrics.response_length_chars = response_length
            metrics.success = True

            if verbose and not is_warmup:
                print(
                    f"{inference_time:.2f}s ({tokens_per_sec:.1f} tok/s)"
                )

        except Exception as e:
            metrics.error_message = str(e)
            metrics.success = False
            if verbose and not is_warmup:
                print(f"FAILED: {e}")

        return metrics

    def run_benchmark_suite(
        self,
        providers: list[str] = None,
        categories: list[str] = None,
        repetitions: int = None,
        skip_cold_start: bool = False,
        verbose: bool = False,
    ) -> list[PerformanceMetrics]:
        """Run complete benchmark suite.

        Args:
            providers: List of providers to test (default: ["ollama", "llamacpp"])
            categories: List of categories to test (default: all)
            repetitions: Number of repetitions per prompt (default: from config)
            skip_cold_start: Skip cold start tests
            verbose: Print detailed progress

        Returns:
            List of all performance metrics
        """
        providers = providers or ["ollama", "llamacpp"]
        repetitions = repetitions or self.config.get("repetitions", 3)
        warmup_iterations = self.config.get("warmup_iterations", 1)

        # Filter prompts by category if specified
        test_prompts = self.prompts
        if categories:
            test_prompts = [p for p in self.prompts if p["category"] in categories]
            print(f"\n✓ Filtered to {len(test_prompts)} prompts in categories: {categories}")

        print(f"\n{'='*60}")
        print(f"Starting Benchmark Suite")
        print(f"{'='*60}")
        print(f"Providers: {', '.join(providers)}")
        print(f"Prompts: {len(test_prompts)}")
        print(f"Repetitions: {repetitions}")
        print(f"Warmup iterations: {warmup_iterations}")
        print(f"Total tests: {len(providers) * len(test_prompts) * (repetitions + warmup_iterations)}")
        print(f"{'='*60}\n")

        results = []

        # Randomize provider order to avoid bias
        test_order = list(providers)
        random.shuffle(test_order)
        print(f"Randomized provider order: {' → '.join(test_order)}\n")

        for provider in test_order:
            print(f"\n{'─'*60}")
            print(f"Testing Provider: {provider.upper()}")
            print(f"{'─'*60}")

            # Cold start test (measure model loading time)
            if not skip_cold_start:
                print(f"\nCold start test (measuring model load time)...")
                llm, load_time = self.initialize_llm(provider, verbose=True)
            else:
                llm, load_time = self.initialize_llm(provider, verbose=verbose)

            for prompt_config in test_prompts:
                # Warmup iterations
                for i in range(warmup_iterations):
                    if verbose:
                        print(f"\n  Warmup {i+1}/{warmup_iterations} for {prompt_config['id']}")
                    self.run_single_test(
                        provider, llm, prompt_config, is_warmup=True, verbose=verbose
                    )
                    time.sleep(0.5)  # Small delay between warmup runs

                # Actual test iterations
                for rep in range(repetitions):
                    metrics = self.run_single_test(
                        provider,
                        llm,
                        prompt_config,
                        is_warmup=False,
                        verbose=verbose,
                        model_load_time=load_time if rep == 0 else 0.0,
                    )
                    results.append(metrics)

                    # Delay between tests to avoid thermal throttling
                    if rep < repetitions - 1:
                        time.sleep(2)

            print(f"\n✓ Completed all tests for {provider}")

        self.results = results
        print(f"\n{'='*60}")
        print(f"Benchmark Complete")
        print(f"{'='*60}")
        print(f"Total results collected: {len(results)}")
        print(f"Successful tests: {sum(1 for r in results if r.success)}")
        print(f"Failed tests: {sum(1 for r in results if not r.success)}\n")

        return results

    def calculate_statistics(self, provider: str) -> ProviderStatistics:
        """Calculate aggregated statistics for a provider.

        Args:
            provider: Provider name

        Returns:
            ProviderStatistics with aggregated metrics
        """
        provider_results = [
            r for r in self.results if r.provider == provider and not r.is_warmup
        ]

        if not provider_results:
            return ProviderStatistics(
                provider=provider,
                total_tests=0,
                successful_tests=0,
                failed_tests=0,
                mean_inference_time=0.0,
                median_inference_time=0.0,
                std_dev_inference_time=0.0,
                p95_inference_time=0.0,
                p99_inference_time=0.0,
                mean_tokens_per_sec=0.0,
                median_tokens_per_sec=0.0,
                mean_model_load_time=0.0,
            )

        successful_results = [r for r in provider_results if r.success]
        inference_times = [r.inference_time_sec for r in successful_results]
        tokens_per_sec = [r.tokens_per_sec for r in successful_results]
        load_times = [r.model_load_time_sec for r in provider_results if r.model_load_time_sec > 0]

        inference_times_sorted = sorted(inference_times)
        n = len(inference_times_sorted)

        # Calculate statistics
        mean_inference = sum(inference_times) / n if n > 0 else 0.0
        median_inference = (
            inference_times_sorted[n // 2] if n > 0 else 0.0
        )

        # Standard deviation
        if n > 1:
            variance = sum((x - mean_inference) ** 2 for x in inference_times) / (n - 1)
            std_dev = variance ** 0.5
        else:
            std_dev = 0.0

        # Percentiles
        p95_idx = int(n * 0.95) if n > 0 else 0
        p99_idx = int(n * 0.99) if n > 0 else 0
        p95 = inference_times_sorted[min(p95_idx, n - 1)] if n > 0 else 0.0
        p99 = inference_times_sorted[min(p99_idx, n - 1)] if n > 0 else 0.0

        mean_tps = sum(tokens_per_sec) / len(tokens_per_sec) if tokens_per_sec else 0.0
        median_tps = sorted(tokens_per_sec)[len(tokens_per_sec) // 2] if tokens_per_sec else 0.0
        mean_load = sum(load_times) / len(load_times) if load_times else 0.0

        # Category breakdown
        category_breakdown = {}
        for category in set(r.prompt_category for r in provider_results):
            cat_results = [r for r in successful_results if r.prompt_category == category]
            if cat_results:
                cat_times = [r.inference_time_sec for r in cat_results]
                cat_tps = [r.tokens_per_sec for r in cat_results]
                category_breakdown[category] = {
                    "mean_time": sum(cat_times) / len(cat_times),
                    "mean_tps": sum(cat_tps) / len(cat_tps),
                    "count": len(cat_results),
                }

        return ProviderStatistics(
            provider=provider,
            total_tests=len(provider_results),
            successful_tests=len(successful_results),
            failed_tests=len(provider_results) - len(successful_results),
            mean_inference_time=mean_inference,
            median_inference_time=median_inference,
            std_dev_inference_time=std_dev,
            p95_inference_time=p95,
            p99_inference_time=p99,
            mean_tokens_per_sec=mean_tps,
            median_tokens_per_sec=median_tps,
            mean_model_load_time=mean_load,
            category_breakdown=category_breakdown,
        )

    def generate_reports(self, output_dir: Path) -> None:
        """Generate all output reports.

        Args:
            output_dir: Directory to save reports
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"\nGenerating reports in {output_dir}...")

        # Calculate statistics for each provider
        providers = list(set(r.provider for r in self.results if not r.is_warmup))
        stats = {p: self.calculate_statistics(p) for p in providers}

        # Generate JSON results
        self._generate_json_results(output_dir, stats)

        # Generate Markdown report
        self._generate_markdown_report(output_dir, stats)

        # Generate CSV export
        self._generate_csv_export(output_dir)

        # Print terminal summary
        self._print_terminal_summary(stats)

        print(f"\n✓ Reports generated successfully in {output_dir}")

    def _generate_json_results(self, output_dir: Path, stats: dict) -> None:
        """Generate JSON results file."""
        json_path = output_dir / "results.json"

        output = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "config": self.config,
                "total_tests": len(self.results),
            },
            "raw_results": [asdict(r) for r in self.results if not r.is_warmup],
            "statistics": {p: asdict(s) for p, s in stats.items()},
        }

        with open(json_path, "w") as f:
            json.dump(output, f, indent=2)

        print(f"  ✓ JSON results: {json_path}")

    def _generate_markdown_report(self, output_dir: Path, stats: dict) -> None:
        """Generate Markdown report."""
        md_path = output_dir / "report.md"

        lines = [
            "# LLM Performance Comparison Report",
            f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"\n**Total Tests:** {len([r for r in self.results if not r.is_warmup])}",
            "\n## Overall Performance Summary\n",
        ]

        # Summary table
        table_data = []
        for provider, stat in stats.items():
            table_data.append([
                provider.upper(),
                f"{stat.mean_inference_time:.3f}s",
                f"{stat.median_inference_time:.3f}s",
                f"{stat.mean_tokens_per_sec:.1f}",
                f"{stat.successful_tests}/{stat.total_tests}",
            ])

        lines.append(tabulate(
            table_data,
            headers=["Provider", "Mean Time", "Median Time", "Tokens/sec", "Success Rate"],
            tablefmt="github",
        ))

        # Determine winner
        if len(stats) == 2:
            providers = list(stats.keys())
            faster = min(providers, key=lambda p: stats[p].mean_inference_time)
            slower = [p for p in providers if p != faster][0]
            speedup = (
                stats[slower].mean_inference_time / stats[faster].mean_inference_time
            )
            lines.append(f"\n### Winner: **{faster.upper()}**")
            lines.append(
                f"\n{faster.upper()} is **{speedup:.2f}x faster** than {slower.upper()} "
                f"({((speedup - 1) * 100):.1f}% improvement)"
            )

        # Category breakdown
        lines.append("\n## Performance by Category\n")
        for category in ["short", "medium", "long"]:
            lines.append(f"\n### {category.capitalize()} Prompts\n")
            cat_table = []
            for provider, stat in stats.items():
                if category in stat.category_breakdown:
                    bd = stat.category_breakdown[category]
                    cat_table.append([
                        provider.upper(),
                        f"{bd['mean_time']:.3f}s",
                        f"{bd['mean_tps']:.1f}",
                        bd['count'],
                    ])
            if cat_table:
                lines.append(tabulate(
                    cat_table,
                    headers=["Provider", "Mean Time", "Tokens/sec", "Tests"],
                    tablefmt="github",
                ))

        # Detailed statistics
        lines.append("\n## Detailed Statistics\n")
        for provider, stat in stats.items():
            lines.append(f"\n### {provider.upper()}\n")
            lines.append(f"- **Total Tests:** {stat.total_tests}")
            lines.append(f"- **Successful:** {stat.successful_tests}")
            lines.append(f"- **Failed:** {stat.failed_tests}")
            lines.append(f"- **Mean Inference Time:** {stat.mean_inference_time:.3f}s")
            lines.append(f"- **Median Inference Time:** {stat.median_inference_time:.3f}s")
            lines.append(f"- **Std Dev:** {stat.std_dev_inference_time:.3f}s")
            lines.append(f"- **P95:** {stat.p95_inference_time:.3f}s")
            lines.append(f"- **P99:** {stat.p99_inference_time:.3f}s")
            lines.append(f"- **Mean Tokens/sec:** {stat.mean_tokens_per_sec:.1f}")
            lines.append(f"- **Mean Model Load Time:** {stat.mean_model_load_time:.3f}s")

        with open(md_path, "w") as f:
            f.write("\n".join(lines))

        print(f"  ✓ Markdown report: {md_path}")

    def _generate_csv_export(self, output_dir: Path) -> None:
        """Generate CSV export."""
        csv_path = output_dir / "results.csv"

        non_warmup_results = [r for r in self.results if not r.is_warmup]

        with open(csv_path, "w", newline="") as f:
            if non_warmup_results:
                writer = csv.DictWriter(f, fieldnames=asdict(non_warmup_results[0]).keys())
                writer.writeheader()
                for result in non_warmup_results:
                    writer.writerow(asdict(result))

        print(f"  ✓ CSV export: {csv_path}")

    def _print_terminal_summary(self, stats: dict) -> None:
        """Print summary to terminal."""
        print(f"\n{'='*60}")
        print("PERFORMANCE SUMMARY")
        print(f"{'='*60}\n")

        table_data = []
        for provider, stat in stats.items():
            table_data.append([
                provider.upper(),
                f"{stat.mean_inference_time:.3f}s",
                f"{stat.median_inference_time:.3f}s",
                f"{stat.mean_tokens_per_sec:.1f}",
                f"{stat.p95_inference_time:.3f}s",
                f"{stat.successful_tests}/{stat.total_tests}",
            ])

        print(tabulate(
            table_data,
            headers=[
                "Provider",
                "Mean Time",
                "Median Time",
                "Tokens/sec",
                "P95 Time",
                "Success",
            ],
            tablefmt="simple",
        ))

        # Determine winner
        if len(stats) == 2:
            providers = list(stats.keys())
            faster = min(providers, key=lambda p: stats[p].mean_inference_time)
            slower = [p for p in providers if p != faster][0]
            speedup = (
                stats[slower].mean_inference_time / stats[faster].mean_inference_time
            )
            print(f"\n🏆 WINNER: {faster.upper()}")
            print(
                f"   {faster.upper()} is {speedup:.2f}x faster than {slower.upper()} "
                f"({((speedup - 1) * 100):.1f}% improvement)"
            )

        print(f"\n{'='*60}\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Compare LLM performance between Ollama and Llama.cpp"
    )
    parser.add_argument(
        "--config",
        default="llamacpp_ollama/config/llm_benchmark_prompts.yaml",
        help="Path to prompts configuration file",
    )
    parser.add_argument(
        "--output-dir",
        help="Output directory for results (default: results/llm_comparison_TIMESTAMP)",
    )
    parser.add_argument(
        "--categories",
        help="Comma-separated list of categories to test (e.g., 'short,medium')",
    )
    parser.add_argument(
        "--repetitions",
        type=int,
        help="Number of repetitions per prompt (overrides config)",
    )
    parser.add_argument(
        "--skip-cold-start",
        action="store_true",
        help="Skip cold start model loading tests",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--providers",
        default="ollama,llamacpp",
        help="Comma-separated list of providers to test (default: ollama,llamacpp)",
    )

    args = parser.parse_args()

    # Parse categories
    categories = None
    if args.categories:
        categories = [c.strip() for c in args.categories.split(",")]

    # Parse providers
    providers = [p.strip() for p in args.providers.split(",")]

    # Set output directory
    output_dir = args.output_dir
    if not output_dir:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = f"results/llm_comparison_{timestamp}"
    output_dir = Path(output_dir)

    # Run benchmark
    runner = BenchmarkRunner(args.config)
    runner.run_benchmark_suite(
        providers=providers,
        categories=categories,
        repetitions=args.repetitions,
        skip_cold_start=args.skip_cold_start,
        verbose=args.verbose,
    )
    runner.generate_reports(output_dir)


if __name__ == "__main__":
    main()
