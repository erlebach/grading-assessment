"""v2 ordering benchmark driver.

For each requested question, runs the v2 pipeline (answer generation →
rubric generation → Karpathy refinement) and records whether the
Karpathy loop converged. Convergence == no `good > less_good > wrong`
ordering violations on both training and held-out validation answers.

Source material is the full text of
``grading_pipeline/sources/slides_data_type_quality.pdf``.

Compares against the v1 T4.3 baseline (per ``t4_3_report.md``):
``good > less_good > wrong`` held only for q01 and q04; q02, q03, q05
failed.

Usage:
    .venv/bin/python scripts/run_v2_benchmark.py --questions q01
    .venv/bin/python scripts/run_v2_benchmark.py --all
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from pypdf import PdfReader

from config.llm_config import configure_llm_for_tier
from v2.answer_generator import AnswerGenerator, AnswerGeneratorConfig
from v2.judge import ConceptJudge, EvaluationMode
from v2.karpathy_loop import KarpathyConfig, KarpathyLoop
from v2.rubric_critic import RubricCritic
from v2.rubric_generator import RubricGeneratorConfig, RubricGeneratorV2
from v2.scoring import compute_grade

PDF_PATH = REPO_ROOT / "grading_pipeline" / "sources" / "slides_data_type_quality.pdf"
RESULTS_DIR = REPO_ROOT / "results"

QUESTIONS: dict[str, dict[str, str]] = {
    "q01": {
        "type": "distinction",
        "text": (
            "In the context of a data table, precisely distinguish an 'object' from "
            "an 'attribute,' and give two alternative names for each (as used in "
            "data mining practice)."
        ),
    },
    "q02": {
        "type": "application",
        "text": (
            "The slides emphasize that an attribute's properties — not the apparent "
            "data type of its stored values — determine valid analyses and "
            "transformations. Explain this principle using the zip code example, "
            "and state one analysis that would be inappropriate if you mistakenly "
            "treated zip codes as numeric."
        ),
    },
    "q03": {
        "type": "enumeration",
        "text": (
            "Nominal, ordinal, interval, and ratio attributes differ by which "
            "operations are 'meaningful.' For each type, list which of the "
            "following are meaningful: distinctness (=, ≠), order (<, >), "
            "differences (+, −), ratios (×, ÷)."
        ),
    },
    "q04": {
        "type": "mechanism",
        "text": (
            "Why is it not physically meaningful to say that 10° is 'twice as warm' "
            "as 5° on the Celsius or Fahrenheit scales, but it is meaningful on "
            "the Kelvin scale? State the key role played by the zero point."
        ),
    },
    "q05": {
        "type": "definition",
        "text": (
            "A measurement scale can preserve only ordering or can preserve ordering "
            "plus additivity. Explain what 'preserving only ordering' means, and "
            "describe one practical consequence for computations you should (or "
            "should not) perform."
        ),
    },
}


@dataclass
class QuestionResult:
    question_id: str
    question_type: str
    converged: bool
    iterations_used: int
    violation_count: int
    violations: list[dict] = field(default_factory=list)
    error: str | None = None


def extract_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def build_components(tier: str = "foundational") -> dict[str, Any]:
    llm = configure_llm_for_tier(tier)
    answer_gen = AnswerGenerator(llm=llm, config=AnswerGeneratorConfig(variants_per_level=3))
    rubric_gen = RubricGeneratorV2(llm=llm, config=RubricGeneratorConfig())
    critic = RubricCritic(llm=llm)
    judge = ConceptJudge(llm=llm, mode=EvaluationMode.SINGLE)

    def scorer(**kw):
        evals = judge.evaluate(
            answer_text=kw["answer_text"], rubric=kw["rubric"], evidence_context=""
        )
        return compute_grade(
            grade_id=f"{kw['student_id']}_{kw['question_id']}",
            question_id=kw["question_id"],
            student_id=kw["student_id"],
            rubric=kw["rubric"],
            check_evaluations=evals,
        )

    loop = KarpathyLoop(
        judge=judge,
        scorer=scorer,
        critic=critic,
        rubric_generator=rubric_gen,
        config=KarpathyConfig(max_iterations=5, train_per_level=2, val_per_level=1),
    )
    return {
        "answer_gen": answer_gen,
        "rubric_gen": rubric_gen,
        "critic": critic,
        "judge": judge,
        "loop": loop,
    }


def run_one(question_id: str, components: dict, source_material: str) -> QuestionResult:
    q = QUESTIONS[question_id]
    logging.info("\n=== %s (%s) ===", question_id, q["type"])

    try:
        answers = components["answer_gen"].generate(
            question_id=question_id,
            question_text=q["text"],
            question_type=q["type"],
            source_material=source_material,
        )
        logging.info("  generated %d synthetic answers", len(answers))

        initial_rubric = components["rubric_gen"].generate(
            question_id=question_id,
            question_text=q["text"],
            question_type=q["type"],
            source_material=source_material,
            synthetic_answers=answers,
            version=1,
        )
        logging.info("  initial rubric: %d criteria", len(initial_rubric.criteria))

        result = components["loop"].run(
            initial_rubric=initial_rubric,
            answers=answers,
            question_id=question_id,
            question_text=q["text"],
            question_type=q["type"],
            source_material=source_material,
        )
        status = "CONVERGED" if result.converged else "did NOT converge"
        logging.info(
            "  %s in %d iterations (%d violations seen)",
            status,
            result.iterations_used,
            len(result.all_violations),
        )

        return QuestionResult(
            question_id=question_id,
            question_type=q["type"],
            converged=result.converged,
            iterations_used=result.iterations_used,
            violation_count=len(result.all_violations),
            violations=[
                {
                    "criterion_id": v.criterion_id,
                    "bad_pair": list(v.bad_pair),
                    "bad_scores": list(v.bad_scores),
                    "description": v.description,
                }
                for v in result.all_violations
            ],
        )
    except Exception as e:
        logging.exception("  failure on %s: %s", question_id, e)
        return QuestionResult(
            question_id=question_id,
            question_type=q["type"],
            converged=False,
            iterations_used=0,
            violation_count=0,
            error=f"{type(e).__name__}: {e}",
        )


def write_report(results: list[QuestionResult], path: Path) -> None:
    ts = datetime.now().isoformat(timespec="seconds")
    total = len(results)
    converged = sum(1 for r in results if r.converged)
    errored = sum(1 for r in results if r.error)

    lines = [
        "# v2 Ordering Benchmark — Report",
        "",
        f"*Generated: {ts}*",
        "",
        "## Summary",
        "",
        f"- Questions attempted: **{total}**",
        f"- Karpathy loop converged (good > less_good > wrong on train+val): **{converged}/{total}**",
        f"- Errored: **{errored}**",
        "",
        "## v1 baseline (T4.3, per t4_3_report.md)",
        "",
        "`good > less_good > wrong` held for **q01, q04**; failed for **q02, q03, q05**.",
        "",
        "## Per-question results",
        "",
        "| qid | type | converged | iterations | violations seen | error |",
        "|-----|------|-----------|------------|-----------------|-------|",
    ]
    for r in results:
        lines.append(
            f"| {r.question_id} | {r.question_type} | "
            f"{'✅' if r.converged else '❌'} | {r.iterations_used} | "
            f"{r.violation_count} | {r.error or ''} |"
        )

    lines.append("")
    lines.append("## Violation details (per question)")
    lines.append("")
    for r in results:
        lines.append(f"### {r.question_id}")
        lines.append("")
        if r.error:
            lines.append(f"- error: `{r.error}`")
        elif not r.violations:
            lines.append("- no ordering violations recorded.")
        else:
            for v in r.violations:
                lines.append(f"- `{v['criterion_id']}`: {v['description']}")
        lines.append("")

    path.write_text("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--questions",
        nargs="+",
        choices=list(QUESTIONS),
        help="Question IDs to run (e.g. --questions q01 q02).",
    )
    parser.add_argument("--all", action="store_true", help="Run all 5 questions.")
    parser.add_argument(
        "--tier",
        choices=["foundational", "oss", "mixed"],
        default="oss",
        help="LLM tier from config/rubric_generation.yaml (default: oss).",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=RESULTS_DIR / "v2_benchmark_report.md",
        help="Path to markdown report (default: results/v2_benchmark_report.md).",
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=None,
        help="Optional path for machine-readable JSON dump.",
    )
    args = parser.parse_args()

    qs = list(QUESTIONS) if args.all else (args.questions or [])
    if not qs:
        parser.error("specify --questions Q [Q ...] or --all")

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    RESULTS_DIR.mkdir(exist_ok=True)

    source = extract_pdf_text(PDF_PATH)
    logging.info("PDF source loaded: %d chars from %s", len(source), PDF_PATH.name)
    logging.info("LLM tier: %s", args.tier)

    components = build_components(tier=args.tier)
    results = [run_one(qid, components, source) for qid in qs]

    write_report(results, args.report)
    if args.json:
        args.json.write_text(json.dumps([asdict(r) for r in results], indent=2))
    print(f"\nReport: {args.report}")


if __name__ == "__main__":
    main()
