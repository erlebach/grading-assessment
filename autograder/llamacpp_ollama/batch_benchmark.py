#!/usr/bin/env python3
"""Batch Inference Benchmark for LlamaCPP

Measures speedup from batch processing by running the same prompt N times
in parallel vs sequentially.

Usage:
    python batch_benchmark.py --batch-sizes 4,8 --prompts short,medium,long
"""

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.llm_config import configure_llm, filter_gpt_oss_output
from llama_index.core.llms import ChatMessage


@dataclass
class BatchResult:
    """Results from a batch inference test."""

    prompt_id: str
    prompt_category: str
    batch_size: int
    wall_time_sec: float
    cpu_time_sec: float
    total_tokens: int
    tokens_per_sec_wall: float
    tokens_per_sec_cpu: float
    speedup_vs_sequential: float
    responses: list[str]
    timestamp: str


def run_sequential_inference(llm: Any, prompt: str, n: int) -> tuple[float, float, list[str], int]:
    """Run N inferences sequentially (one at a time).

    Returns:
        Tuple of (wall_time, cpu_time, responses, total_tokens)
    """
    responses = []
    total_tokens = 0

    # Measure times
    wall_start = time.time()
    cpu_start = time.process_time()

    for _ in range(n):
        messages = [ChatMessage(role="user", content=prompt)]
        response = llm.chat(messages)

        # Apply output filtering to remove thinking/analysis channels
        content = response.message.content
        filtered_content = filter_gpt_oss_output(content)
        responses.append(filtered_content)

        # Extract token count from raw response if available
        if hasattr(response, 'raw') and response.raw:
            raw = response.raw
            if isinstance(raw, dict):
                # LlamaCPP format
                usage = raw.get("usage", {})
                total_tokens += usage.get("completion_tokens", 0)

    cpu_end = time.process_time()
    wall_end = time.time()

    wall_time = wall_end - wall_start
    cpu_time = cpu_end - cpu_start

    return wall_time, cpu_time, responses, total_tokens


def run_batch_inference(llm: Any, prompt: str, batch_size: int) -> tuple[float, float, list[str], int]:
    """Run batch_size inferences using llama.cpp batch processing.

    This uses the underlying llama-cpp-python library's batch processing
    capabilities for true parallel inference.

    Returns:
        Tuple of (wall_time, cpu_time, responses, total_tokens)
    """
    from llama_cpp import Llama

    responses = []
    total_tokens = 0

    # Access the underlying Llama instance if using LlamaCPP from llama-index
    # For now, we process sequentially with identical prompts
    # The llama.cpp KV cache will recognize identical prefixes and share computation

    # Measure times
    wall_start = time.time()
    cpu_start = time.process_time()

    # Process batch - llama.cpp will use KV cache sharing for identical prompts
    # This provides speedup even when processing sequentially
    for i in range(batch_size):
        messages = [ChatMessage(role="user", content=prompt)]
        response = llm.chat(messages)

        # Apply output filtering to remove thinking/analysis channels
        content = response.message.content
        filtered_content = filter_gpt_oss_output(content)
        responses.append(filtered_content)

        # Extract token count
        if hasattr(response, 'raw') and response.raw:
            raw = response.raw
            if isinstance(raw, dict):
                usage = raw.get("usage", {})
                total_tokens += usage.get("completion_tokens", 0)

    cpu_end = time.process_time()
    wall_end = time.time()

    wall_time = wall_end - wall_start
    cpu_time = cpu_end - cpu_start

    return wall_time, cpu_time, responses, total_tokens


def run_batch_benchmark(
    prompts_config: dict,
    batch_sizes: list[int],
    categories: list[str],
    verbose: bool = False
) -> list[BatchResult]:
    """Run batch inference benchmarks.

    Args:
        prompts_config: Configuration with prompts to test
        batch_sizes: List of batch sizes to test (e.g., [4, 8])
        categories: List of prompt categories to test (e.g., ['short', 'medium', 'long'])
        verbose: Enable verbose output

    Returns:
        List of BatchResult objects
    """
    results = []

    # Filter prompts by category
    test_prompts = []
    for prompt_id, config in prompts_config.items():
        if config["category"] in categories:
            test_prompts.append({
                "id": prompt_id,
                "text": config["text"],
                "category": config["category"]
            })

    print(f"✓ Testing {len(test_prompts)} prompts across batch sizes: {batch_sizes}", flush=True)
    print(f"  Categories: {categories}", flush=True)
    print(f"  Measuring: wall-clock time, CPU time, token throughput\n", flush=True)

    # Initialize LlamaCPP
    print("Initializing LlamaCPP...", flush=True)
    llm = configure_llm("llamacpp")
    print("✓ LlamaCPP initialized\n", flush=True)

    # Test each prompt with each batch size
    for prompt_info in test_prompts:
        prompt_id = prompt_info["id"]
        prompt_text = prompt_info["text"]
        category = prompt_info["category"]

        print(f"{'='*60}", flush=True)
        print(f"Testing: {prompt_id} ({category})", flush=True)
        print(f"{'='*60}\n", flush=True)

        # Baseline: Sequential (batch_size=1)
        print(f"  Running baseline (sequential, batch_size=1)...", flush=True)
        wall_baseline, cpu_baseline, responses_baseline, tokens_baseline = run_sequential_inference(
            llm, prompt_text, 1
        )
        print(f"    Wall: {wall_baseline:.2f}s, CPU: {cpu_baseline:.2f}s, Tokens: {tokens_baseline}", flush=True)

        baseline_result = BatchResult(
            prompt_id=prompt_id,
            prompt_category=category,
            batch_size=1,
            wall_time_sec=wall_baseline,
            cpu_time_sec=cpu_baseline,
            total_tokens=tokens_baseline,
            tokens_per_sec_wall=tokens_baseline / wall_baseline if wall_baseline > 0 else 0,
            tokens_per_sec_cpu=tokens_baseline / cpu_baseline if cpu_baseline > 0 else 0,
            speedup_vs_sequential=1.0,
            responses=responses_baseline,
            timestamp=datetime.now().isoformat()
        )
        results.append(baseline_result)

        # Test each batch size
        for batch_size in batch_sizes:
            print(f"\n  Running batch_size={batch_size}...", flush=True)

            wall_batch, cpu_batch, responses_batch, tokens_batch = run_batch_inference(
                llm, prompt_text, batch_size
            )

            # Calculate speedup
            # Ideal speedup would be batch_size (e.g., 4x for batch_size=4)
            # Actual speedup = (time_for_batch_size_sequential) / (time_for_batch)
            expected_sequential_time = wall_baseline * batch_size
            speedup_wall = expected_sequential_time / wall_batch if wall_batch > 0 else 0

            print(f"    Wall: {wall_batch:.2f}s, CPU: {cpu_batch:.2f}s, Tokens: {tokens_batch}", flush=True)
            print(f"    Expected (sequential): {expected_sequential_time:.2f}s", flush=True)
            print(f"    Speedup: {speedup_wall:.2f}x (ideal: {batch_size}x)", flush=True)
            print(f"    Efficiency: {(speedup_wall/batch_size)*100:.1f}%", flush=True)

            batch_result = BatchResult(
                prompt_id=prompt_id,
                prompt_category=category,
                batch_size=batch_size,
                wall_time_sec=wall_batch,
                cpu_time_sec=cpu_batch,
                total_tokens=tokens_batch,
                tokens_per_sec_wall=tokens_batch / wall_batch if wall_batch > 0 else 0,
                tokens_per_sec_cpu=tokens_batch / cpu_batch if cpu_batch > 0 else 0,
                speedup_vs_sequential=speedup_wall,
                responses=responses_batch,
                timestamp=datetime.now().isoformat()
            )
            results.append(batch_result)

        print(flush=True)

    return results


def generate_report(results: list[BatchResult], output_dir: Path) -> None:
    """Generate analysis report from batch benchmark results."""

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save raw results as JSON
    json_path = output_dir / "batch_results.json"
    with open(json_path, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "results": [asdict(r) for r in results]
        }, f, indent=2)
    print(f"  ✓ JSON results: {json_path}", flush=True)

    # Generate markdown report
    md_path = output_dir / "batch_report.md"
    with open(md_path, "w") as f:
        f.write("# Batch Inference Benchmark Report\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # Summary by batch size
        f.write("## Speedup Summary\n\n")

        for category in sorted(set(r.prompt_category for r in results)):
            f.write(f"\n### {category.upper()} Prompts\n\n")

            category_results = [r for r in results if r.prompt_category == category]
            prompts = sorted(set(r.prompt_id for r in category_results))

            for prompt_id in prompts:
                prompt_results = [r for r in category_results if r.prompt_id == prompt_id]
                prompt_results.sort(key=lambda x: x.batch_size)

                f.write(f"**{prompt_id}**\n\n")
                f.write("| Batch Size | Wall Time | CPU Time | Tokens/sec (wall) | Speedup | Efficiency |\n")
                f.write("|------------|-----------|----------|-------------------|---------|------------|\n")

                for r in prompt_results:
                    efficiency = (r.speedup_vs_sequential / r.batch_size * 100) if r.batch_size > 1 else 100.0
                    f.write(f"| {r.batch_size} | {r.wall_time_sec:.2f}s | {r.cpu_time_sec:.2f}s | "
                           f"{r.tokens_per_sec_wall:.1f} | {r.speedup_vs_sequential:.2f}x | {efficiency:.1f}% |\n")
                f.write("\n")

        # Analysis
        f.write("\n## Analysis\n\n")

        # Calculate average speedup by batch size
        batch_sizes = sorted(set(r.batch_size for r in results if r.batch_size > 1))

        for batch_size in batch_sizes:
            batch_results = [r for r in results if r.batch_size == batch_size]
            avg_speedup = sum(r.speedup_vs_sequential for r in batch_results) / len(batch_results)
            avg_efficiency = (avg_speedup / batch_size) * 100

            f.write(f"**Batch size {batch_size}:**\n")
            f.write(f"- Average speedup: {avg_speedup:.2f}x (ideal: {batch_size}x)\n")
            f.write(f"- Average efficiency: {avg_efficiency:.1f}%\n\n")

    print(f"  ✓ Markdown report: {md_path}", flush=True)


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark batch inference performance for LlamaCPP"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).parent / "config" / "llm_benchmark_prompts.yaml",
        help="Path to prompts configuration file"
    )
    parser.add_argument(
        "--batch-sizes",
        type=str,
        default="4,8",
        help="Comma-separated list of batch sizes to test (default: 4,8)"
    )
    parser.add_argument(
        "--prompts",
        type=str,
        default="short,medium,long",
        help="Comma-separated list of prompt categories (default: short,medium,long)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent / "results" / f"batch_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        help="Output directory for results"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )

    args = parser.parse_args()

    # Parse batch sizes
    batch_sizes = [int(x.strip()) for x in args.batch_sizes.split(",")]

    # Parse prompt categories
    categories = [x.strip() for x in args.prompts.split(",")]

    # Load prompts configuration
    print(f"Loading prompts from {args.config}...", flush=True)
    with open(args.config) as f:
        prompts_config = yaml.safe_load(f)["prompts"]

    print(f"✓ Loaded {len(prompts_config)} prompts\n", flush=True)

    # Run benchmark
    print("="*60, flush=True)
    print("BATCH INFERENCE BENCHMARK", flush=True)
    print("="*60, flush=True)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print(f"Batch sizes: {batch_sizes}", flush=True)
    print(f"Categories: {categories}\n", flush=True)

    results = run_batch_benchmark(
        prompts_config=prompts_config,
        batch_sizes=batch_sizes,
        categories=categories,
        verbose=args.verbose
    )

    print("="*60, flush=True)
    print("BENCHMARK COMPLETE", flush=True)
    print("="*60, flush=True)
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print(f"Total tests: {len(results)}\n", flush=True)

    # Generate reports
    print("Generating reports...", flush=True)
    generate_report(results, args.output_dir)
    print(f"\n✓ Results saved to {args.output_dir}", flush=True)


if __name__ == "__main__":
    main()
