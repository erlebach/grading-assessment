"""T2.4 — Deduplication of extracted checks.

Removes semantically redundant checks from a Rubric, keeping the first
occurrence of each duplicate pair.

Public API
----------
deduplicate_checks(rubric, similarity_fn=None, threshold=0.85) -> DeduplicationResult

The ``similarity_fn`` must have signature ``(text_a: str, text_b: str) -> float``
and return a score in [0, 1]. Pairs with score >= threshold are considered
duplicates. When no function is provided, the default LLM-based similarity
is used (requires a running Ollama instance).

``DeduplicationResult`` carries:
  - ``rubric``           — new Rubric with duplicate checks removed
  - ``duplicates_removed``  — count of checks removed
  - ``removed_pairs``   — list of (kept_id, removed_id) tuples for audit
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .models import Check, Rubric

SimilarityFn = Callable[[str, str], float]


@dataclass
class DeduplicationResult:
    """Result of a deduplication pass."""

    rubric: Rubric
    duplicates_removed: int
    removed_pairs: list[tuple[str, str]] = field(default_factory=list)


def deduplicate_checks(
    rubric: Rubric,
    similarity_fn: SimilarityFn | None = None,
    threshold: float = 0.85,
) -> DeduplicationResult:
    """Remove duplicate checks from a Rubric.

    Args:
        rubric:        Input rubric (not mutated).
        similarity_fn: ``(text_a, text_b) -> float`` in [0, 1].
                       Defaults to ``_llm_similarity`` when None.
        threshold:     Pairs with similarity >= threshold are duplicates.
                       Default 0.85.

    Returns:
        DeduplicationResult with a new deduplicated Rubric and metadata.
    """
    if similarity_fn is None:
        similarity_fn = _llm_similarity

    checks: list[Check] = rubric.checks
    kept: list[Check] = []
    removed_pairs: list[tuple[str, str]] = []

    for candidate in checks:
        duplicate_of: Check | None = None
        for existing in kept:
            score = similarity_fn(candidate.text, existing.text)
            if score >= threshold:
                duplicate_of = existing
                break
        if duplicate_of is not None:
            removed_pairs.append((duplicate_of.id, candidate.id))
        else:
            kept.append(candidate)

    new_rubric = rubric.model_copy(update={"checks": kept})
    return DeduplicationResult(
        rubric=new_rubric,
        duplicates_removed=len(removed_pairs),
        removed_pairs=removed_pairs,
    )


# ---------------------------------------------------------------------------
# Default LLM-based similarity (Ollama)
# ---------------------------------------------------------------------------

def _llm_similarity(text_a: str, text_b: str) -> float:
    """Call Ollama to estimate semantic similarity between two check texts.

    Returns a float in [0, 1]. Requires a running Ollama instance with
    the configured model (see config/llm_config.py).

    This is the production default; inject a custom function for unit tests.
    """
    import json
    import urllib.request

    prompt = (
        "You are evaluating whether two grading checklist items are duplicates.\n"
        "Return ONLY a JSON object: {\"similarity\": <float between 0 and 1>}\n"
        "1.0 = identical meaning, 0.0 = completely different.\n\n"
        f"Check A: {text_a}\n"
        f"Check B: {text_b}\n"
    )

    payload = json.dumps({
        "model": "gpt-oss:20b",
        "prompt": prompt,
        "stream": False,
        "format": "json",
    }).encode()

    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            result = json.loads(data.get("response", "{}"))
            return float(result.get("similarity", 0.0))
    except Exception:
        # On any error, treat as not a duplicate (conservative)
        return 0.0
