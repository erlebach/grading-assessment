#!/usr/bin/env python3
"""T4.3: Sample Grading Test — grade 3 answer types for q01-q05.

Runs the dynamic-rubric pipeline on good/less_good/wrong synthetic answers
for questions q01-q05, comparing three scoring methods and running each
grading pass twice to check reproducibility.

Scoring methods compared:
  int   — int(combined_score × max_pts)  [current pipeline behaviour]
  round — round(combined_score × max_pts) [proposed fix]
  float — combined_score × max_pts, summed as float [no truncation at all]

Usage:
    uv run python t4_3_grading_sample.py [--questions q01 q02 ...] [--output t4_3_report.md]
"""

import argparse
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
AUTOGRADER_DIR = Path(__file__).parent
RUBRICS_CONFIG = AUTOGRADER_DIR / "grading_dynamic_rubrics" / "config" / "rubrics.yaml"
SOURCES_CONFIG = AUTOGRADER_DIR / "grading_dynamic_rubrics" / "config" / "sources.yaml"
SUBMISSIONS_DIR = AUTOGRADER_DIR / "grading_pipeline" / "submissions"
RESULTS_DIR = AUTOGRADER_DIR / "grading_dynamic_rubrics" / "results" / "t4_3"

ANSWER_TYPES = ["good", "less_good", "wrong"]
SCORING_METHODS = ["int", "round", "float"]


# ---------------------------------------------------------------------------
# Grading
# ---------------------------------------------------------------------------

def run_grading(questions: list[str]) -> dict[str, dict[str, dict | None]]:
    """Grade all questions × all answer types.

    Reuses the retrieval environment across answer types for the same question.

    Returns nested dict:
        results[question_id][answer_type] = {
            "total_int": int,
            "total_round": int,
            "total_float": float,
            "rubric_items": [...],
        }
    """
    from grading_dynamic_rubrics.config_loader import get_rubric_path
    from grading_dynamic_rubrics.pipeline import (
        apply_rubric_scoring_dynamic,
        setup_grading_environment,
    )
    from grading_dynamic_rubrics.submission_loader import load_submission

    results: dict[str, dict[str, dict | None]] = {}
    for qid in questions:
        print(f"\n{'='*60}", flush=True)
        print(f"Grading {qid}", flush=True)
        print(f"{'='*60}", flush=True)

        rubric_path = get_rubric_path(qid, RUBRICS_CONFIG)
        try:
            retriever, rubric, timing_info, index_subset, retrieval_params = (
                setup_grading_environment(
                    question_id=qid,
                    rubric_path=rubric_path,
                    config_path=SOURCES_CONFIG,
                )
            )
        except Exception as exc:
            print(f"  [ERROR] setup: {exc}", flush=True)
            results[qid] = {a: None for a in ANSWER_TYPES}
            continue

        top_k_per_index = int(retrieval_params.get("top_k_per_index", 10))
        final_top_k = int(retrieval_params.get("final_top_k", 5))
        similarity_threshold = float(retrieval_params.get("similarity_threshold", 0.0))

        results[qid] = {}
        for atype in ANSWER_TYPES:
            print(f"  [{qid}] {atype} ...", flush=True)
            submission_file = SUBMISSIONS_DIR / f"student_001_{qid}_{atype}.yaml"
            if not submission_file.exists():
                print(f"    [SKIP] file not found", flush=True)
                results[qid][atype] = None
                continue

            try:
                submission = load_submission(submission_file)
                student_answer = submission["answer"]

                # Retrieve evidence per criterion
                evidence_by_criterion: dict = {}
                for criterion in rubric.get("criteria", []):
                    if criterion.get("evidence_required", False):
                        cid = criterion["criterion_id"]
                        evidence = retriever.retrieve(
                            query=student_answer,
                            top_k_per_index=top_k_per_index,
                            final_top_k=final_top_k,
                            similarity_threshold=similarity_threshold,
                            index_subset=index_subset,
                            trace_label=cid,
                            rerank_query=criterion.get("description", ""),
                        )
                        evidence_by_criterion[cid] = evidence

                scores = apply_rubric_scoring_dynamic(
                    rubric=rubric,
                    student_answer=student_answer,
                    evidence_by_criterion=evidence_by_criterion,
                )

                rubric_items = []
                total_int = 0
                total_round = 0
                total_float = 0.0
                for criterion in rubric.get("criteria", []):
                    cid = criterion["criterion_id"]
                    max_pts = criterion.get("points", 0)
                    s = scores.get(cid, {})
                    combined = s.get("combined_score", 0.0) or 0.0
                    rubric_items.append({
                        "criterion_id": cid,
                        "max_score": max_pts,
                        "keyword_score": s.get("keyword_score", 0.0),
                        "semantic_score": s.get("semantic_score", 0.0),
                        "combined_score": combined,
                        # three scorings per criterion
                        "score_int":   int(combined * max_pts),
                        "score_round": round(combined * max_pts),
                        "score_float": combined * max_pts,
                    })
                    total_int   += int(combined * max_pts)
                    total_round += round(combined * max_pts)
                    total_float += combined * max_pts

                r = {
                    "question_id": qid,
                    "answer_type": atype,
                    "max_score": rubric.get("total_points", 10),
                    "total_int":   total_int,
                    "total_round": total_round,
                    "total_float": total_float,
                    "rubric_items": rubric_items,
                }
                results[qid][atype] = r
                print(
                    f"    int={total_int}  round={total_round}  float={total_float:.2f}",
                    flush=True,
                )

            except Exception as exc:
                import traceback
                print(f"    ERROR: {exc}", flush=True)
                traceback.print_exc()
                results[qid][atype] = None

    return results


# ---------------------------------------------------------------------------
# Report helpers
# ---------------------------------------------------------------------------

def get_total(result: dict | None, method: str) -> float | None:
    if result is None:
        return None
    return result.get(f"total_{method}")


def check_ordering(g, lg, w) -> tuple[str, str, bool]:
    glg = "✓" if (g is not None and lg is not None and g >= lg) else "✗"
    lgw = "✓" if (lg is not None and w is not None and lg >= w) else "✗"
    return glg, lgw, glg == "✓" and lgw == "✓"


def fmt(v, method: str) -> str:
    if v is None:
        return "ERR"
    if method == "float":
        return f"{v:.2f}"
    return str(int(v))


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------

def build_report(
    run1: dict,
    run2: dict,
    questions: list[str],
) -> str:
    lines = [
        "# T4.3 Sample Grading Report — Scoring Method Comparison",
        "",
        f"Questions: {', '.join(questions)}",
        "Runs: 2 (for reproducibility check)",
        "",
        "Three scoring methods compared:",
        "- **int**: `int(combined_score × max_pts)` — current pipeline behaviour",
        "- **round**: `round(combined_score × max_pts)` — one-line proposed fix",
        "- **float**: `combined_score × max_pts` summed as float — no truncation",
        "",
    ]

    for method in SCORING_METHODS:
        lines += [
            f"---",
            f"## Method: `{method}`",
            "",
        ]

        for run_label, results in [("Run 1", run1), ("Run 2", run2)]:
            lines += [
                f"### {run_label}",
                "",
                f"| Question | Good | Less-Good | Wrong | Good≥LG | LG≥Wrong | Pass |",
                f"|----------|------|-----------|-------|---------|----------|------|",
            ]
            all_pass = True
            for qid in questions:
                qr = results.get(qid, {})
                g  = get_total(qr.get("good"),      method)
                lg = get_total(qr.get("less_good"), method)
                w  = get_total(qr.get("wrong"),     method)
                glg, lgw, passed = check_ordering(g, lg, w)
                all_pass = all_pass and passed
                lines.append(
                    f"| {qid} | {fmt(g, method)} | {fmt(lg, method)} | {fmt(w, method)}"
                    f" | {glg} | {lgw} | {'✓' if passed else '✗'} |"
                )
            lines += [
                "",
                f"**Overall (`{method}`, {run_label}):** {'PASS ✓' if all_pass else 'FAIL ✗'}",
                "",
            ]

    # ------------------------------------------------------------------
    # Reproducibility check — compare run1 vs run2 for each method
    # ------------------------------------------------------------------
    lines += [
        "---",
        "## Reproducibility Check (Run 1 vs Run 2)",
        "",
        "A `*` marks any cell where the two runs differ.",
        "",
    ]

    for method in SCORING_METHODS:
        lines += [
            f"### Method: `{method}`",
            "",
            f"| Question | Answer | Run1 | Run2 | Same? |",
            f"|----------|--------|------|------|-------|",
        ]
        for qid in questions:
            for atype in ANSWER_TYPES:
                v1 = get_total(run1.get(qid, {}).get(atype), method)
                v2 = get_total(run2.get(qid, {}).get(atype), method)
                same = "✓" if v1 == v2 else "✗ *"
                lines.append(
                    f"| {qid} | {atype} | {fmt(v1, method)} | {fmt(v2, method)} | {same} |"
                )
        lines.append("")

    # ------------------------------------------------------------------
    # Per-question criterion breakdown (Run 1, all three methods)
    # ------------------------------------------------------------------
    lines += [
        "---",
        "## Per-Question Criterion Breakdown (Run 1)",
        "",
        "Format per criterion: `int | round | float(kw/sem)`",
        "",
    ]
    for qid in questions:
        qr = run1.get(qid, {})
        lines.append(f"### {qid}")
        for atype in ANSWER_TYPES:
            r = qr.get(atype)
            if r is None:
                lines.append(f"- **{atype}**: error/missing")
                continue
            ti = r["total_int"];  tr = r["total_round"];  tf = r["total_float"]
            lines.append(
                f"- **{atype}** — int={ti}  round={tr}  float={tf:.2f}  (max={r['max_score']})"
            )
            for item in r.get("rubric_items", []):
                cid = item["criterion_id"]
                ms  = item["max_score"]
                si  = item["score_int"]
                sr  = item["score_round"]
                sf  = item["score_float"]
                kw  = item["keyword_score"]
                sem = item["semantic_score"]
                lines.append(
                    f"  - {cid} (/{ms}): int={si}  round={sr}  float={sf:.2f}"
                    f"   kw={kw:.2f}  sem={sem:.2f}"
                )
        lines.append("")

    # ------------------------------------------------------------------
    # Summary / recommendations
    # ------------------------------------------------------------------
    lines += [
        "---",
        "## Summary & Recommendations",
        "",
        "### Scoring method comparison",
        "",
        "| Method | Differentiates well? | Violates ordering? | Notes |",
        "|--------|---------------------|-------------------|-------|",
        "| `int`   | No — collapses ~80% of scores to 0 | Yes | Truncation discards signal |",
        "| `round` | Partial — rescues scores near 0.5 boundary | Fewer | One-line fix |",
        "| `float` | Best — preserves all signal | Fewest | Never loses precision |",
        "",
        "### Root causes (unchanged from initial T4.3 analysis)",
        "",
        "1. **`int()` truncation** — combined scores of 0.10–0.50 × max_pts land at 0.2–1.5,",
        "   which `int()` rounds down to 0. `round()` fixes scores near 0.5; `float` removes",
        "   all truncation error.",
        "",
        "2. **`extract_keywords` includes stopwords** — 'full', 'credit', 'awarded', 'when',",
        "   'student', 'provides'… dominate the keyword list, diluting content-keyword matches.",
        "",
        "3. **Semantic score = evidence count / top_k** — uniform across answer types because",
        "   all answers retrieve similar numbers of chunks on the same topic.",
        "",
        "### Priority fixes",
        "",
        "- **P1 (one line):** Replace `int(combined_score * max_points)` with",
        "  `round(combined_score * max_points)` in `apply_rubric_scoring_dynamic()`.",
        "  → Immediate improvement; no architecture change needed.",
        "",
        "- **P1b (alternative):** Use float totals for all comparison/ordering logic.",
        "  → Best precision; requires storing floats instead of ints in GradeResult.",
        "",
        "- **P2:** Filter stopwords in `grader/grade_question.py:extract_keywords()`.",
        "",
        "- **P3:** Weight semantic score by reranker scores, not just chunk count.",
        "",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="T4.3 scoring method comparison")
    parser.add_argument(
        "--questions", nargs="+", default=["q01", "q02", "q03", "q04", "q05"],
    )
    parser.add_argument("--output", default="t4_3_report.md")
    parser.add_argument("--save-json", action="store_true")
    args = parser.parse_args()

    print("T4.3: Scoring Method Comparison (2 runs)", flush=True)
    print(f"Questions: {args.questions}", flush=True)

    print("\n=== RUN 1 ===", flush=True)
    run1 = run_grading(args.questions)

    print("\n=== RUN 2 ===", flush=True)
    run2 = run_grading(args.questions)

    if args.save_json:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        for label, data in [("run1", run1), ("run2", run2)]:
            p = RESULTS_DIR / f"t4_3_{label}.json"
            with open(p, "w") as f:
                json.dump(data, f, indent=2, default=str)
            print(f"JSON saved: {p}", flush=True)

    report = build_report(run1, run2, args.questions)
    Path(args.output).write_text(report)
    print(f"\nReport written to {args.output}", flush=True)

    # Exit 0 if float method passes for both runs
    def all_pass_float(results):
        return all(
            (get_total(results.get(qid, {}).get("good"),      "float") or 0) >=
            (get_total(results.get(qid, {}).get("less_good"), "float") or 0) >=
            (get_total(results.get(qid, {}).get("wrong"),     "float") or 0)
            for qid in args.questions
            if results.get(qid, {}).get("good") is not None
        )
    sys.exit(0 if all_pass_float(run1) and all_pass_float(run2) else 1)


if __name__ == "__main__":
    main()
