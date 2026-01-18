"""Transparency logging for grading pipeline.

Provides detailed, colored logging to help students understand
how their answers were graded and what evidence was used.

"""

import math
from pathlib import Path
from typing import Any

# ANSI color codes
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
BLUE = "\033[34m"
RESET = "\033[0m"
BOLD = "\033[1m"


class TransparencyLogger:
    """Logger for transparent grading information."""

    def __init__(self, log_file: Path | None = None, enabled: bool = True):
        """Initialize transparency logger.

        Args:
            log_file: Optional path to log file.
            enabled: Whether logging is enabled.

        """
        self.log_file = log_file
        self.enabled = enabled
        self.handle = None
        if enabled and log_file:
            # Use line buffering (buffering=1) for text files
            # Unbuffered (0) only works for binary files
            self.handle = open(log_file, "w", buffering=1)

    def log_retrieval_results(
        self,
        question_text: str,
        criterion_id: str,
        top_10_word: list[dict[str, Any]],
        top_10_sentence: list[dict[str, Any]],
        top_5_reranked: list[dict[str, Any]],
    ) -> None:
        """Log retrieval results for a criterion in clear format.

        Args:
            question_text: The question text.
            criterion_id: Criterion identifier.
            top_10_word: Top 10 results from word index.
            top_10_sentence: Top 10 results from sentence index.
            top_5_reranked: Top 5 results after reranking.

        """
        if not self.enabled:
            return

        self._write(f"\n{'='*80}\n")
        self._write(f"{BOLD}Question:{RESET} {question_text}\n")
        self._write(f"{BOLD}Criterion:{RESET} {criterion_id}\n")
        self._write(f"{'='*80}\n\n")

        # Word Embedding Database
        self._write(f"{BOLD}Word Embedding Database (512 char chunks):{RESET}\n")
        self._write("  Score computation: ChromaDB returns cosine distance [0, 2].\n")
        self._write("  LlamaIndex transforms: score = exp(-distance).\n")
        self._write("  To recover distance: distance = -ln(score).\n")
        self._write("  To get cosine similarity: cosine_sim = 1 - distance (approx).\n")
        self._write(
            "  Higher score = more similar. Score range: (0, 1], where 1 = perfect match.\n\n"
        )
        for rank, result in enumerate(top_10_word[:10], 1):
            score = result.get("score", 0.0)
            # Convert back to distance for transparency
            if score > 0:
                raw_distance = -math.log(score)
                # Approximate cosine similarity (for cosine distance: sim ≈ 1 - distance)
                # Note: This is approximate; actual cosine similarity depends on normalization
                cosine_sim_approx = max(0.0, min(1.0, 1.0 - raw_distance))
            else:
                raw_distance = float("inf")
                cosine_sim_approx = 0.0

            text = result.get("text", "")
            # Show transformed score, raw distance, and approximate cosine similarity
            self._write(
                f"  rank {rank}: score={score:.3f} (distance={raw_distance:.3f}, cosine_sim≈{cosine_sim_approx:.3f})\n"
            )
            self._write(f"  span: >>>{text}<<<\n\n")

        # Sentence Embedding Database
        self._write(f"\n{BOLD}Sentence Embedding Database:{RESET}\n")
        self._write("  Score computation: ChromaDB returns cosine distance [0, 2].\n")
        self._write("  LlamaIndex transforms: score = exp(-distance).\n")
        self._write("  To recover distance: distance = -ln(score).\n")
        self._write("  To get cosine similarity: cosine_sim = 1 - distance (approx).\n")
        self._write(
            "  Higher score = more similar. Score range: (0, 1], where 1 = perfect match.\n\n"
        )
        for rank, result in enumerate(top_10_sentence[:10], 1):
            score = result.get("score", 0.0)
            # Convert back to distance for transparency
            import math

            if score > 0:
                raw_distance = -math.log(score)
                # Approximate cosine similarity (for cosine distance: sim ≈ 1 - distance)
                cosine_sim_approx = max(0.0, min(1.0, 1.0 - raw_distance))
            else:
                raw_distance = float("inf")
                cosine_sim_approx = 0.0

            text = result.get("text", "")
            # Show transformed score, raw distance, and approximate cosine similarity
            self._write(
                f"  rank {rank}: score={score:.3f} (distance={raw_distance:.3f}, cosine_sim≈{cosine_sim_approx:.3f})\n"
            )
            self._write(f"  span: >>>{text}<<<\n\n")

        # Retriever (Reranked Results)
        self._write(f"\n{BOLD}Retriever (Reranked Results):{RESET}\n")
        for rank, result in enumerate(top_5_reranked[:5], 1):
            # Use rerank_score if available, otherwise use original score
            rerank_score = result.get("rerank_score", result.get("score", 0.0))
            # Display raw rerank score from CrossEncoder - no normalization
            # CrossEncoder scores vary by model and are not necessarily in [-1, 1]
            text = result.get("text", "")
            self._write(f"  rank {rank}: score={rerank_score:.3f}\n")
            self._write(f"  span: >>>{text}<<<\n\n")

    def log_keyword_matches(
        self, criterion_id: str, keyword_result: dict[str, Any]
    ) -> None:
        """Log keyword matching results.

        Args:
            criterion_id: Criterion identifier.
            keyword_result: Result from compute_keyword_score().

        """
        if not self.enabled:
            return

        self._write(
            f"\n{BOLD}{BLUE}=== Keyword Analysis for {criterion_id} ==={RESET}\n"
        )

        found = keyword_result.get("found_keywords", [])
        missing = keyword_result.get("missing_keywords", [])
        score = keyword_result.get("keyword_score", 0.0)

        self._write(f"Keyword Score: {GREEN}{score:.3f}{RESET}\n\n")

        self._write(f"{BOLD}Found Keywords:{RESET}\n")
        for kw in found:
            self._write(f"  {GREEN}✓{RESET} {kw}\n")

        self._write(f"\n{BOLD}Missing Keywords:{RESET}\n")
        for kw in missing:
            self._write(f"  {RED}✗{RESET} {kw}\n")

    def log_semantic_scores(
        self, criterion_id: str, semantic_result: dict[str, Any]
    ) -> None:
        """Log semantic similarity scores.

        Args:
            criterion_id: Criterion identifier.
            semantic_result: Result from compute_semantic_score().

        """
        if not self.enabled:
            return

        self._write(
            f"\n{BOLD}{BLUE}=== Semantic Analysis for {criterion_id} ==={RESET}\n"
        )

        score = semantic_result.get("semantic_score", 0.0)
        normalized = semantic_result.get("normalized_scores", [])
        weights = semantic_result.get("weights", [])

        self._write(f"Semantic Score: {GREEN}{score:.3f}{RESET}\n\n")

        self._write(f"{BOLD}Evidence Chunk Scores:{RESET}\n")
        for i, (norm, weight) in enumerate(zip(normalized, weights), 1):
            self._write(
                f"  {i}. Normalized: {GREEN}{norm:.3f}{RESET}, "
                f"Weight: {YELLOW}{weight:.3f}{RESET}\n"
            )

    def _write(self, text: str) -> None:
        """Write text to log file and stdout in unbuffered mode."""
        print(text, end="", flush=True)
        if self.handle:
            # Write immediately (unbuffered mode)
            self.handle.write(text)
            self.handle.flush()  # Ensure immediate write even in unbuffered mode

    def close(self) -> None:
        """Close log file."""
        if self.handle:
            self.handle.close()
