# `scripts/run_v2_benchmark.py` — Flow

## Steps

1. **Parse args** (`--questions`, `--all`, `--tier`, `--report`, `--json`, `--log`).
2. **Set up logging** — console handler + unbuffered file handler at `<report>.log`.
3. **Load PDF source** via `extract_pdf_text(PDF_PATH)` → one shared `source_material` string.
4. **`build_components(tier)`** — instantiate one LLM and wire up:
    - `AnswerGenerator` (variants_per_level=3)
    - `RubricGeneratorV2`
    - `RubricCritic`
    - `ConceptJudge` (mode=SINGLE)
    - `scorer` closure (judge + `compute_grade`)
    - `KarpathyLoop` (max_iter=5, train=2/lvl, val=1/lvl)
5. **For each requested question** call `run_one(qid, components, source)`:
    1. Look up `QUESTIONS[qid]` → `{type, text}`.
    2. `answer_gen.generate(...)` → 9 `SyntheticAnswer` (3×3).
    3. `rubric_gen.generate(..., synthetic_answers=...)` → initial `RubricV2`.
    4. `loop.run(initial_rubric, answers, ...)` → `KarpathyResult` (converged?, iterations, violations).
    5. Wrap into `QuestionResult` (or `QuestionResult(error=...)` on exception).
6. **`write_report(results, path)`** — Markdown summary + per-question violation list.
7. **Optional JSON dump** if `--json` given (list of `QuestionResult` dicts).
8. Print `Report: <path>` to stdout.

## Flowchart

```
                 +--------------------+
                 |    main()          |
                 +---------+----------+
                           |
                           v
              +------------+------------+
              | parse args, set logging |
              +------------+------------+
                           |
                           v
              +------------+------------+
              | extract_pdf_text(PDF)   |
              +------------+------------+
                           |
                           v
              +------------+------------+
              | build_components(tier)  |
              | (one LLM, 5 components) |
              +------------+------------+
                           |
                           v
        +------------------+------------------+
        |  for each qid in --questions:        |
        |       run_one(qid, components, src)  |
        +------------------+------------------+
                           |
                           v
   +---------------------- run_one ----------------------+
   |                                                     |
   |   answer_gen.generate()                             |
   |        │  (9 LLM calls)                             |
   |        v                                            |
   |   rubric_gen.generate()                             |
   |        │  (1 LLM call)                              |
   |        v                                            |
   |   loop.run()                                        |
   |        │  (per iter: judge × 3 train,               |
   |        │   judge × 3 val if train clean,            |
   |        │   critic × 1 on violations;                |
   |        │   up to max_iterations)                    |
   |        v                                            |
   |   return QuestionResult(converged, iters,           |
   |          violations) OR QuestionResult(error=...)   |
   +---------------------+------------------------------+
                           |
                           v
              +------------+------------+
              | write_report(results)   |
              +------------+------------+
                           |
                           v
              +------------+------------+
              | optional --json dump    |
              +------------+------------+
                           |
                           v
                       print path
```
