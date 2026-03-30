"""T2.5 — Integrate full rubric generation pipeline.

Chains: LLM generate → extract checks → validate categories → deduplicate.
Stores all intermediate artifacts for debugging and reproducibility.

Public API
----------
generate_complete_rubric(
    question_id, question_text, source_content,
    llm=None, output_dir=None, config_path=None,
    on_invalid="default", dedup_threshold=0.85,
    similarity_fn=None, max_retries=3, version=1,
) -> GenerationResult
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .categorization import validate_categories
from .check_extraction import extract_checks
from .deduplication import DeduplicationResult, deduplicate_checks
from .models import Rubric

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default paths
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent
_TEMPLATE_PATH = Path(__file__).parent / "rubric_generator_template.txt"
_DEFAULT_OUTPUT_DIR = _REPO_ROOT / "data" / "rubrics"


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class GenerationResult:
    """Result of a complete rubric generation run."""

    rubric: Rubric
    question_id: str
    version: int
    raw_llm_response: str
    rubric_after_extraction: Rubric
    rubric_after_categorization: Rubric
    deduplication_result: DeduplicationResult
    artifacts_dir: Path | None = None
    warnings: list[str] = field(default_factory=list)

    @property
    def checks_removed(self) -> int:
        return self.deduplication_result.duplicates_removed

    @property
    def final_check_count(self) -> int:
        return len(self.rubric.checks)


# ---------------------------------------------------------------------------
# LLM call helper
# ---------------------------------------------------------------------------

def _build_prompt(question_text: str, source_content: str) -> str:
    """Fill in the rubric generation template."""
    template = _TEMPLATE_PATH.read_text()
    return template.replace("{QUESTION_TEXT}", question_text).replace(
        "{SOURCE_FILE_CONTENT}", source_content
    )


def _call_llm(prompt: str, llm: Any, max_retries: int = 3) -> str:
    """Call the LLM and return its raw text response, with retries."""
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            response = llm.complete(prompt)
            raw = response.text
            if raw.strip():
                return raw
            raise ValueError("LLM returned empty response")
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning("LLM call attempt %d/%d failed: %s", attempt + 1, max_retries, exc)
            if attempt < max_retries - 1:
                prompt += (
                    f"\n\nPrevious attempt failed: {exc}\n"
                    "Please return a valid JSON response."
                )
    raise ValueError(f"LLM call failed after {max_retries} attempts") from last_exc


# ---------------------------------------------------------------------------
# Artifact storage
# ---------------------------------------------------------------------------

def _save_artifact(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    logger.debug("Saved artifact: %s", path)


def _rubric_to_json(rubric: Rubric) -> str:
    return rubric.model_dump_json(indent=2)


def _save_artifacts(
    output_dir: Path,
    question_id: str,
    version: int,
    raw_llm: str,
    rubric_extracted: Rubric,
    rubric_categorized: Rubric,
    dedup_result: DeduplicationResult,
) -> None:
    base = output_dir / question_id / f"v{version}"
    _save_artifact(base / "01_raw_llm_response.txt", raw_llm)
    _save_artifact(base / "02_extracted.json", _rubric_to_json(rubric_extracted))
    _save_artifact(base / "03_categorized.json", _rubric_to_json(rubric_categorized))
    _save_artifact(base / "04_deduplicated.json", _rubric_to_json(dedup_result.rubric))
    _save_artifact(
        base / "04_dedup_metadata.json",
        json.dumps(
            {
                "duplicates_removed": dedup_result.duplicates_removed,
                "removed_pairs": dedup_result.removed_pairs,
            },
            indent=2,
        ),
    )
    logger.info("Artifacts saved to %s", base)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_complete_rubric(
    question_id: str,
    question_text: str,
    source_content: str,
    llm: Any = None,
    output_dir: Path | str | None = None,
    config_path: Path | str | None = None,
    on_invalid: str = "default",
    dedup_threshold: float = 0.85,
    similarity_fn: Callable[[str, str], float] | None = None,
    max_retries: int = 3,
    version: int = 1,
) -> GenerationResult:
    """Generate a complete, validated, deduplicated rubric for a question.

    Steps
    -----
    1. Build prompt from template + inputs.
    2. Call LLM (with retries) → raw JSON string.
    3. extract_checks()         → Rubric with Check objects.
    4. validate_categories()    → categories validated/corrected.
    5. deduplicate_checks()     → duplicate checks removed.
    6. Persist all intermediate artifacts under ``output_dir``.

    Args:
        question_id:    Identifier for the question (e.g. "q01").
        question_text:  The question text shown to students.
        source_content: Source material used to generate the rubric.
        llm:            LlamaIndex-compatible LLM instance.  If None, a
                        default Ollama instance is created (requires Ollama
                        running locally with the ``gpt-oss:20b`` model).
        output_dir:     Root directory for artifact storage.
                        Defaults to ``data/rubrics/``.
        config_path:    Path to grading_categories.yaml.
                        Defaults to the project config directory.
        on_invalid:     Category fallback strategy: "error", "default", "fuzzy".
        dedup_threshold: Similarity threshold for deduplication (0-1).
        similarity_fn:  Optional custom ``(text_a, text_b) -> float`` function.
        max_retries:    LLM call retry limit.
        version:        Rubric version number (used in artifact filenames).

    Returns:
        GenerationResult with the final Rubric and all intermediate artifacts.

    Raises:
        ValueError: If LLM generation or validation fails after retries.
    """
    warnings: list[str] = []

    # ------------------------------------------------------------------
    # 0. Resolve LLM
    # ------------------------------------------------------------------
    if llm is None:
        try:
            from config.llm_config import configure_llm  # type: ignore[import]
            llm = configure_llm("ollama")
            logger.info("Using default Ollama LLM instance")
        except Exception as exc:  # noqa: BLE001
            raise ValueError(
                "No LLM provided and default Ollama setup failed. "
                "Pass an explicit llm= argument."
            ) from exc

    # ------------------------------------------------------------------
    # 1. Build prompt & call LLM
    # ------------------------------------------------------------------
    logger.info("Generating rubric for question %s (version %d)", question_id, version)
    prompt = _build_prompt(question_text, source_content)
    raw_llm = _call_llm(prompt, llm, max_retries=max_retries)
    logger.debug("Raw LLM response (%d chars)", len(raw_llm))

    # ------------------------------------------------------------------
    # 2. Extract checks
    # ------------------------------------------------------------------
    rubric_id = f"{question_id}_rubric_v{version}"
    rubric_extracted = extract_checks(raw_llm, question_id=question_id, rubric_id=rubric_id, version=version)
    logger.info("Extracted %d checks from LLM response", len(rubric_extracted.checks))

    # ------------------------------------------------------------------
    # 3. Validate / fix categories
    # ------------------------------------------------------------------
    if config_path is not None:
        config_path = Path(config_path)
    rubric_categorized = validate_categories(
        rubric_extracted, config_path=config_path, on_invalid=on_invalid
    )
    n_fixed = sum(
        1
        for a, b in zip(rubric_extracted.checks, rubric_categorized.checks)
        if a.category != b.category
    )
    if n_fixed:
        w = f"{n_fixed} check(s) had invalid categories and were corrected"
        warnings.append(w)
        logger.warning(w)

    # ------------------------------------------------------------------
    # 4. Deduplicate
    # ------------------------------------------------------------------
    dedup_result = deduplicate_checks(
        rubric_categorized, similarity_fn=similarity_fn, threshold=dedup_threshold
    )
    if dedup_result.duplicates_removed:
        w = f"Removed {dedup_result.duplicates_removed} duplicate check(s): {dedup_result.removed_pairs}"
        warnings.append(w)
        logger.info(w)

    final_rubric = dedup_result.rubric
    logger.info(
        "Final rubric has %d checks (removed %d duplicates)",
        len(final_rubric.checks),
        dedup_result.duplicates_removed,
    )

    # ------------------------------------------------------------------
    # 5. Persist artifacts
    # ------------------------------------------------------------------
    resolved_output_dir = Path(output_dir) if output_dir is not None else _DEFAULT_OUTPUT_DIR
    try:
        _save_artifacts(
            resolved_output_dir,
            question_id,
            version,
            raw_llm,
            rubric_extracted,
            rubric_categorized,
            dedup_result,
        )
        artifacts_dir = resolved_output_dir / question_id / f"v{version}"
    except OSError as exc:
        w = f"Could not save artifacts to {resolved_output_dir}: {exc}"
        warnings.append(w)
        logger.warning(w)
        artifacts_dir = None

    return GenerationResult(
        rubric=final_rubric,
        question_id=question_id,
        version=version,
        raw_llm_response=raw_llm,
        rubric_after_extraction=rubric_extracted,
        rubric_after_categorization=rubric_categorized,
        deduplication_result=dedup_result,
        artifacts_dir=artifacts_dir,
        warnings=warnings,
    )
