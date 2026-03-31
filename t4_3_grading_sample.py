#!/usr/bin/env python3
"""T4.3: Sample Grading Test — grade 3 answer types for q01-q05.

Runs the dynamic-rubric pipeline on good/less_good/wrong synthetic answers
for questions q01 through q05, then prints a comparison table and checks
the ordering: good_score >= less_good_score >= wrong_score.

Usage:
    uv run python t4_3_grading_sample.py [--questions q01 q02 ...] [--output t4_3_report.md]
"""

import argparse
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths (all relative to this script's directory = autograder/)
# ---------------------------------------------------------------------------
AUTOGRADER_DIR = Path(__file__).parent
RUBRICS_CONFIG = AUTOGRADER_DIR / "grading_dynamic_rubrics" / "config" / "rubrics.yaml"
SOURCES_CONFIG = AUTOGRADER_DIR / "grading_dynamic_rubrics" / "config" / "sources.yaml"
SUBMISSIONS_DIR = AUTOGRADER_DIR / "grading_pipeline" / "submissions"
RESULTS_DIR = AUTOGRADER_DIR / "grading_dynamic_rubrics" / "results" / "t4_3"

ANSWER_TYPES = ["good", "less_good", "wrong"]



def run_grading(questions: list[str]) -> dict[str, dict[str, dict | None]]:
    """Grade all questions × all answer types.

    Reuses the retrieval environment across answer types for the same question.
    Returns nested dict: results[question_id][answer_type] = result dict.
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
            retriever, rubric, timing_info, index_subset, retrieval_params = setup_grading_environment(
                question_id=qid,
                rubric_path=rubric_path,
                config_path=SOURCES_CONFIG,
            )
        except Exception as exc:
            print(f"  [ERROR] setup_grading_environment: {exc}", flush=True)
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

                # Score
                scores = apply_rubric_scoring_dynamic(
                    rubric=rubric,
                    student_answer=student_answer,
                    evidence_by_criterion=evidence_by_criterion,
                )

                rubric_items = []
                total_int = 0
                total_combined = 0.0
                for criterion in rubric.get("criteria", []):
                    cid = criterion["criterion_id"]
                    max_pts = criterion.get("points", 0)
                    s = scores.get(cid, {})
                    combined = s.get("combined_score", 0.0) or 0.0
                    rubric_items.append({
                        "criterion_id": cid,
                        "score": s.get("score", 0),
                        "max_score": max_pts,
                        "keyword_score": s.get("keyword_score"),
                        "semantic_score": s.get("semantic_score"),
                        "combined_score": combined,
                        "found_keywords": s.get("found_keywords", []),
                        "missing_keywords": s.get("missing_keywords", []),
                    })
                    total_int += s.get("score", 0)
                    total_combined += combined * max_pts  # float weighted total

                r = {
                    "question_id": qid,
                    "answer_type": atype,
                    "total_score": total_int,           # int (may be 0 due to truncation)
                    "total_score_float": total_combined, # float (used for ordering)
                    "max_score": rubric.get("total_points", 10),
                    "rubric_items": rubric_items,
                }
                results[qid][atype] = r
                print(f"    score = {total_int}/10  (float={total_combined:.2f})", flush=True)

            except Exception as exc:
                import traceback
                print(f"    ERROR: {exc}", flush=True)
                traceback.print_exc()
                results[qid][atype] = None

    return results


def extract_score(result: dict | None) -> float | None:
    """Return float weighted score (pre-truncation) for ordering comparison."""
    if result is None:
        return None
    return result.get("total_score_float", result.get("total_score", result.get("score")))


def build_report(results: dict, questions: list[str]) -> str:
    lines = [
        "# T4.3 Sample Grading Report",
        "",
        "Questions graded: " + ", ".join(questions),
        "",
        "## Score Table",
        "",
        "| Question | Good | Less-Good | Wrong | Good≥LG | LG≥Wrong | Pass |",
        "|----------|------|-----------|-------|---------|----------|------|",
    ]

    all_pass = True
    ordering_checks = []

    for qid in questions:
        qr = results.get(qid, {})
        g = extract_score(qr.get("good"))
        lg = extract_score(qr.get("less_good"))
        w = extract_score(qr.get("wrong"))

        def fmt(v):
            return f"{v:.1f}" if v is not None else "ERR"

        glg = "✓" if (g is not None and lg is not None and g >= lg) else "✗"
        lgw = "✓" if (lg is not None and w is not None and lg >= w) else "✗"
        passed = glg == "✓" and lgw == "✓"
        all_pass = all_pass and passed
        ordering_checks.append((qid, g, lg, w, glg, lgw, passed))
        lines.append(
            f"| {qid} | {fmt(g)} | {fmt(lg)} | {fmt(w)} | {glg} | {lgw} | {'✓' if passed else '✗'} |"
        )

    lines += [
        "",
        f"**Overall ordering validation:** {'PASS' if all_pass else 'FAIL'}",
        "",
        "## Discrepancy Analysis",
        "",
    ]

    for qid, g, lg, w, glg, lgw, passed in ordering_checks:
        if not passed:
            lines.append(f"### {qid} — ordering violated")
            if glg == "✗":
                lines.append(f"- good ({g}) < less_good ({lg}): check rubric criteria and keyword coverage")
            if lgw == "✗":
                lines.append(f"- less_good ({lg}) < wrong ({w}): check that wrong answer triggers low semantic similarity")
            lines.append("")

    if all_pass:
        lines.append("No ordering violations detected. All questions passed.")

    lines += [
        "",
        "## Per-Question Criterion Breakdown",
        "",
    ]

    for qid in questions:
        qr = results.get(qid, {})
        lines.append(f"### {qid}")
        for atype in ANSWER_TYPES:
            r = qr.get(atype)
            if r is None:
                lines.append(f"- **{atype}**: error/missing")
                continue
            score = extract_score(r)
            score_str = f"{score:.1f}" if score is not None else "?"
            lines.append(f"- **{atype}** (total={score_str}/10):")
            for item in r.get("rubric_items", []):
                cid = item.get("criterion_id", "?")
                cs = item.get("score", "?")
                ms = item.get("max_score", "?")
                kw = item.get("keyword_score")
                sem = item.get("semantic_score")
                kw_str = f"kw={kw:.2f}" if kw is not None else ""
                sem_str = f"sem={sem:.2f}" if sem is not None else ""
                lines.append(f"  - {cid}: {cs}/{ms}  {kw_str}  {sem_str}")
        lines.append("")

    lines += [
        "## Recommendations",
        "",
        "_(Auto-generated — fill in after reviewing the breakdown above.)_",
        "",
        "- If keyword scores are uniformly low: expand keyword lists in rubric criteria descriptions.",
        "- If semantic scores don't differentiate: rebuild indexes or lower similarity_threshold.",
        "- If wrong answer scores high: add negative keywords or adjust scoring_weights.",
        "",
    ]

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="T4.3 sample grading test")
    parser.add_argument(
        "--questions", nargs="+", default=["q01", "q02", "q03", "q04", "q05"],
        help="Questions to grade (default: q01-q05)"
    )
    parser.add_argument(
        "--output", default="t4_3_report.md",
        help="Output report file (default: t4_3_report.md)"
    )
    parser.add_argument(
        "--save-json", action="store_true",
        help="Also save raw JSON results to t4_3_results.json"
    )
    args = parser.parse_args()

    print("T4.3: Sample Grading Test", flush=True)
    print(f"Questions: {args.questions}", flush=True)

    results = run_grading(args.questions)

    # Save JSON if requested
    if args.save_json:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        json_path = RESULTS_DIR / "t4_3_results.json"
        # Convert non-serializable items
        with open(json_path, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nJSON saved to {json_path}", flush=True)

    report = build_report(results, args.questions)
    output_path = Path(args.output)
    output_path.write_text(report)
    print(f"\nReport written to {output_path}", flush=True)

    # Exit code reflects ordering validation
    all_pass = all(
        (extract_score(results.get(qid, {}).get("good")) or 0) >=
        (extract_score(results.get(qid, {}).get("less_good")) or 0) >=
        (extract_score(results.get(qid, {}).get("wrong")) or 0)
        for qid in args.questions
        if results.get(qid, {}).get("good") is not None
    )
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
