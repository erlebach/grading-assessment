# Task 19 — validate_run CLI + smoke fixture

**Plan:** §Task 19 — **Status:** Complete — **Date:** 2026-05-13

## Commits

| SHA | Message |
|---|---|
| `c4d861e` | `feat(grading-plugin): validate_run CLI + hand-crafted smoke fixture run folder` |

## Files

- Created (Python): `plugins/grading/python/validate_run.py`
- Created (tests): `plugins/grading/python/tests/test_validate_run.py`, `plugins/grading/python/tests/test_smoke_fixture.py`
- Created (15 fixture files): under `plugins/grading/python/tests/fixtures/run_smoke/` covering inputs, sources, types, rubrics, synthetic answers, grades, run metadata, config, REPRODUCE doc, and a 2-event trace timeline. `config.yaml` is a byte-identical copy of `plugins/grading/config/pipeline.yaml`.

## Symbols introduced

- `RunValidationReport` — dataclass: `run_dir`, `errors: list[str]`, and an `ok` property (`not errors`). Mutable so helpers can append errors as they discover them.
- `_load_yaml_or_record(path, errors)` — defensive YAML load; on missing file or parse error it appends to `errors` and returns `None`.
- `_validate_universal_rubrics(run_dir, errors)` — walks `<run>/types/<TYPE>/universal_rubric.yaml`, returns `dict[type_name, UniversalRubric]`.
- `_validate_per_question_rubrics_and_grades(run_dir, universals, errors)` — walks `<run>/rubrics/<course>/<qid>/rubric.yaml`, then the matching `<run>/grades/<course>/<qid>/grades.yaml`, validating each against the universal rubric.
- `validate_run_folder(run_dir) -> RunValidationReport` — library entrypoint. Wraps the helpers and seeds an error if no universals were found.
- `main(argv) -> int` — CLI entrypoint. Mutually-exclusive `--run-dir` vs `--runs-root` (required group); optional `--run <prefix>` resolves via `run_resolution.resolve_run`; absence falls back to `most_recent_run`. Prints `OK: <path>` (exit 0) or `FAIL: <path>` with bullet errors (exit 1). `if __name__ == "__main__": sys.exit(main())` at the bottom.

## Tests

7 new tests passing:
- **Smoke (5):** all 15 fixture paths exist; universal rubric validates; per-question rubric validates against it; grades validate against both; timeline.jsonl is well-formed (matching `name` between `start` and `end` phases).
- **Validate-run CLI (2):** positive case on the smoke fixture returns `ok=True`; negative case (a `tmp_path` run with only a per-question rubric and no `types/`) reports a missing `universal_rubric.yaml` error.

Full plugin suite: 92 passing.

Manual CLI smoke: `python -m plugins.grading.python.validate_run --run-dir plugins/grading/python/tests/fixtures/run_smoke` prints `OK: …` and exits 0.

## Reviewers

- Implementer (haiku): DONE.
- Spec-compliance reviewer (haiku): ✅ — exactly 18 files in commit, `validate_run.py` matches plan line-by-line, fixture YAMLs verbatim, `config.yaml` byte-identical to `pipeline.yaml`, timeline.jsonl has matching start/end names.
- Code-quality reviewer (haiku): ✅ Approved — clean helper decomposition, error-accumulation pattern is consistent (no exceptions surface through `validate_run_folder`), `main` returns int (testable; `sys.exit` confined to the `__main__` block).

## Notes

This is the first artifact in the plugin that materializes the **on-disk run-folder schema** (§§4–6 of the design). Subsequent stages (calibrate_types, generate_rubric, gold_grade) will write into this exact shape, and `validate_run` becomes the gate that says "the run is internally consistent" — independent of LLM correctness. The hand-crafted fixture is also the seed for downstream regression tests: any change to a schema validator that breaks `test_smoke_fixture.py` immediately reveals incompatibility with existing artifact shapes.
