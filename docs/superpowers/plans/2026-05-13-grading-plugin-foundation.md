# Grading Plugin Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lay the foundation for the `grading` Claude Code plugin at `plugins/grading/`: full plugin scaffold (manifest, configs, skill/command/hook stubs) plus fully-implemented Python helpers (schema validators §3.6, aggregation §3.3, run resolution, snapshot, diff, pdf_render, subagent contract schemas, validate_run CLI) with unit + property + smoke tests.

**Architecture:** Plugin discovered by Claude Code at `plugins/grading/`. Slash commands invoked as `/grading:<command>`. Skills invoked as `grading:<skill-name>`. All LLM work eventually happens via Claude Code subagents; this plan ships zero LLM-calling code. Python helpers live at `plugins/grading/python/` and provide every deterministic computation the later per-stage plans will need. Each stage's `SKILL.md` is a body-stub in this plan; subsequent per-stage plans (Stage 0–4) fill those in.

**Tech Stack:** Python 3.11; pydantic 2.x (already a dep); pyyaml (already a dep); pymupdf (added in Task 1); pytest 9.x (already a dep); hypothesis (added in Task 1); JSON for manifest + traces; YAML for artifacts + configs.

**Spec reference:** `docs/superpowers/specs/2026-05-13-grading-plugin-design.md`. Sections cited as §N.M throughout.

**Plugin format corrections (against spec §8):** The real Claude Code plugin format differs from the spec illustration. Authoritative shape used in this plan:
- Manifest: `.claude-plugin/plugin.json` (JSON, not `plugin.yaml`).
- Skills: `skills/<skill-name>/SKILL.md` (each skill is a directory).
- Commands: `commands/<name>.md` (flat).
- Hooks: `hooks/hooks.json` (config) + script files.
- Optional `agents/<name>.md` for plugin-bundled subagent profiles.

---

## File Structure

This plan creates:

```
plugins/
  __init__.py
  grading/
    __init__.py
    .claude-plugin/
      plugin.json                    # manifest
    README.md                        # quick-start, slash-command summary
    config/
      pipeline.yaml                  # tunable knobs (§4 knobs aggregated)
      tier_dispatch.yaml             # role → tier mapping (§8.4)
      role_catalog.yaml              # canonical role list (§8.1)
    skills/
      translate-sources/SKILL.md     # Stage 0 stub
      prepare-seed-questions/SKILL.md
      review-seeds/SKILL.md
      calibrate-types/SKILL.md
      test-universal/SKILL.md
      generate-rubric/SKILL.md
      gold-grade/SKILL.md
      run-course/SKILL.md
    commands/
      translate.md                   # /grading:translate <source>
      seeds.md                       # /grading:seeds
      review-seeds.md
      calibrate.md
      test-universal.md
      question.md
      gold-grade.md
      course.md
      status.md
      diff.md
    hooks/
      hooks.json
      post_subagent_validate.sh
    python/
      __init__.py
      schema.py                      # pydantic models + §3.6 validators
      aggregation.py                 # §3.3 formula
      run_resolution.py              # --run <prefix> matching
      snapshot.py                    # src_snapshot.tar.gz
      diff.py                        # semantic diff
      pdf_render.py                  # pymupdf page rendering
      contracts.py                   # subagent output schemas
      validate_run.py                # CLI entry: validate a run folder
      tests/
        __init__.py
        conftest.py
        test_plugin_manifest.py
        test_role_catalog.py
        test_tier_dispatch.py
        test_pipeline_config.py
        test_schema.py
        test_validators.py
        test_aggregation.py
        test_aggregation_invariant.py
        test_run_resolution.py
        test_snapshot.py
        test_pdf_render.py
        test_diff.py
        test_validate_run.py
        test_smoke_fixture.py
        contracts/
          __init__.py
          test_judge_output_schema.py
          test_critic_output_schema.py
          test_materialize_seed_output_schema.py
          test_seed_gen_output_schema.py
        fixtures/
          run_smoke/                  # hand-crafted minimal run folder
            inputs/...
            sources/...
            seed_questions/...
            types/...
            rubrics/...
            synthetic_answers/...
            grades/...
            traces/...
            run_meta.yaml
            config.yaml
            REPRODUCE.md
          tiny.pdf                    # 2-page PDF fixture for pdf_render test
```

And modifies:
- `pyproject.toml` — adds `pymupdf`, `hypothesis` to dev deps; adds `[tool.pytest.ini_options]`.
- `CLAUDE.md` (both project and autograder) — extends the "Test Pipeline" command to include `plugins/grading/python/tests/`.

---

## Conventions used throughout this plan

- **Working directory:** every shell command runs from `/Users/erlebach/src/2026/grading_assessment/autograder/` unless stated otherwise.
- **Python entrypoint:** `.venv/bin/python` (matches CLAUDE.md). When a command needs to be run, use the venv binary explicitly.
- **Test runner invocation:** `.venv/bin/python -m pytest plugins/grading/python/tests/<file>::<test> -v`.
- **Git:** `.git` lives at `autograder/.git` per the autograder-local `CLAUDE.md`. Run `git` directly, no `-C` flag. Branch is `version2-self-contained-benchmark`.
- **Commit messages:** `<type>: <subject>` where type ∈ {feat, test, docs, chore}. Bundle test + code + scaffold for a single task in one commit.
- **No emojis** in code, docs, or commit messages.
- **No `git add -A` or `git add .`** — stage explicit files.

---

## Task 1: Add dependencies and configure pytest

**Files:**
- Modify: `pyproject.toml`
- Verify: `.venv/bin/python -c "import pymupdf, hypothesis"`

- [ ] **Step 1: Add a temporary import test that fails today**

Create `plugins/grading/python/tests/test_deps_smoke.py` (will be deleted in Step 5):

```python
def test_pymupdf_importable():
    import pymupdf  # noqa: F401

def test_hypothesis_importable():
    import hypothesis  # noqa: F401
```

(The plugin directories don't exist yet — `mkdir -p plugins/grading/python/tests` first.)

- [ ] **Step 2: Run to confirm the test fails (import error)**

```bash
mkdir -p plugins/grading/python/tests
.venv/bin/python -m pytest plugins/grading/python/tests/test_deps_smoke.py -v
```

Expected: collection error or `ModuleNotFoundError: No module named 'pymupdf'` / `'hypothesis'`.

- [ ] **Step 3: Edit `pyproject.toml`**

Modify the `[dependency-groups]` `dev` array (the second one — pytest 9.x group near the bottom of the file). Replace:

```toml
[dependency-groups]
dev = [
    "pytest>=9.0.2",
    "pytest-cov>=7.1.0",
]
```

with:

```toml
[dependency-groups]
dev = [
    "pytest>=9.0.2",
    "pytest-cov>=7.1.0",
    "pymupdf>=1.24",
    "hypothesis>=6.100",
]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests", "plugins/grading/python/tests"]
```

- [ ] **Step 4: Resolve and install via uv**

The project uses `uv` (`uv.lock` is checked in). Do **not** use `pip install` directly — it would install into the venv without updating `uv.lock`, causing drift.

```bash
uv lock        # resolves pyproject.toml and updates uv.lock
uv sync        # installs the locked versions into .venv
```

Then rerun the smoke test:

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/test_deps_smoke.py -v
```

Expected: 2 passed. After `uv lock`, `uv.lock` will list `pymupdf` and `hypothesis` entries — verify with `grep -E '^name = "(pymupdf|hypothesis)"' uv.lock`.

- [ ] **Step 5: Delete the smoke test (no longer needed)**

```bash
rm plugins/grading/python/tests/test_deps_smoke.py
```

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml
git commit -m "chore: add pymupdf + hypothesis dev deps and pytest config for grading plugin"
```

---

## Task 2: Plugin directory scaffold and manifest

**Files:**
- Create: `plugins/__init__.py` (empty)
- Create: `plugins/grading/__init__.py` (empty)
- Create: `plugins/grading/python/__init__.py` (empty)
- Create: `plugins/grading/python/tests/__init__.py` (empty)
- Create: `plugins/grading/python/tests/contracts/__init__.py` (empty)
- Create: `plugins/grading/python/tests/conftest.py`
- Create: `plugins/grading/.claude-plugin/plugin.json`
- Create: `plugins/grading/README.md`
- Test: `plugins/grading/python/tests/test_plugin_manifest.py`

- [ ] **Step 1: Write the failing test**

```python
# plugins/grading/python/tests/test_plugin_manifest.py
import json
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"


def test_manifest_file_exists():
    assert MANIFEST.is_file(), f"missing manifest at {MANIFEST}"


def test_manifest_is_valid_json():
    json.loads(MANIFEST.read_text())


def test_manifest_required_fields():
    data = json.loads(MANIFEST.read_text())
    assert data["name"] == "grading"
    assert isinstance(data["description"], str) and data["description"]
    # semver-ish: three dot-separated integers
    version = data["version"]
    parts = version.split(".")
    assert len(parts) == 3 and all(p.isdigit() for p in parts), version


def test_manifest_author_present():
    data = json.loads(MANIFEST.read_text())
    assert "author" in data
```

- [ ] **Step 2: Run the test to confirm it fails**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/test_plugin_manifest.py -v
```

Expected: FAIL (file not found) for all four tests.

- [ ] **Step 3: Create the package skeleton**

Create empty files (all literally empty; their presence makes them importable packages):

- `plugins/__init__.py`
- `plugins/grading/__init__.py`
- `plugins/grading/python/__init__.py`
- `plugins/grading/python/tests/__init__.py`
- `plugins/grading/python/tests/contracts/__init__.py`

Create `plugins/grading/python/tests/conftest.py` with:

```python
"""Test configuration for the grading plugin's Python helpers.

Adds the repo root to sys.path so tests can `from plugins.grading.python...`.
This is redundant with the pyproject pytest pythonpath setting but makes
direct file invocations work too.
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
```

- [ ] **Step 4: Write the manifest**

Create `plugins/grading/.claude-plugin/plugin.json`:

```json
{
  "name": "grading",
  "description": "Gold preprocessing benchmark for the autograder. Produces frozen rubrics, synthetic answers, gold concept coverage, and gold reference scores via Claude Code subagents under MAX.",
  "version": "0.1.0",
  "author": {
    "name": "Gordon Erlebach"
  },
  "license": "Proprietary",
  "keywords": [
    "grading",
    "rubrics",
    "preprocessing",
    "benchmark"
  ]
}
```

- [ ] **Step 5: Write the README**

Create `plugins/grading/README.md`:

```markdown
# grading plugin

Gold-standard preprocessing benchmark for the autograder. See the spec at
`docs/superpowers/specs/2026-05-13-grading-plugin-design.md` for full design.

## Slash commands

| Command | Purpose |
|---|---|
| `/grading:translate <source>` | Stage 0 — translate a PDF or markdown source into canonical form. |
| `/grading:seeds` | Stage 1 — build the cross-topic seed-question pool. |
| `/grading:review-seeds` | Interactive review gate for seed questions. |
| `/grading:calibrate` | Stage 2 — calibrate universal-layer rubrics per question type. |
| `/grading:test-universal` | Ad-hoc test pass against fresh Claude-generated seeds. |
| `/grading:question --course <c> --question <q>` | Stage 3 — generate per-question rubric + synthetic answers. |
| `/grading:gold-grade --course <c> --question <q>` | Stage 4 — Claude judge applies rubric, writes gold reference scores. |
| `/grading:course <course_id>` | Orchestrator — runs Stages 3 + 4 across every question in a course. |
| `/grading:status` | Inspect current run state. |
| `/grading:diff <run_a> <run_b>` | Semantic diff between two runs. |

## MAX quota note

Every LLM operation runs through Claude Code subagents under the user's MAX
subscription. No Anthropic API key is read or required. Roles map to tiers via
`config/tier_dispatch.yaml`.

## Repo layout

See `docs/superpowers/specs/2026-05-13-grading-plugin-design.md` §8.

## Python helpers

`python/` contains deterministic helpers (schema validation, aggregation,
diff, snapshot, run resolution, pdf render). No LLM code. Run tests:

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/ -v
```
```

- [ ] **Step 6: Run the test to verify it passes**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/test_plugin_manifest.py -v
```

Expected: 4 passed.

- [ ] **Step 7: Commit**

```bash
git add plugins/__init__.py plugins/grading/__init__.py plugins/grading/python/__init__.py plugins/grading/python/tests/__init__.py plugins/grading/python/tests/contracts/__init__.py plugins/grading/python/tests/conftest.py plugins/grading/.claude-plugin/plugin.json plugins/grading/README.md plugins/grading/python/tests/test_plugin_manifest.py
git commit -m "feat(grading-plugin): scaffold plugin manifest, package layout, README"
```

---

## Task 3: role_catalog.yaml

**Files:**
- Create: `plugins/grading/config/role_catalog.yaml`
- Test: `plugins/grading/python/tests/test_role_catalog.py`

The 10 roles come from spec §4.0 and §4.2–§4.5. Locked set: `pdf_translator, seed_gen, seed_validator, materialize_seed, axis_criterion_drafter, judge, critic, overlay_critic, question_workup, gold_annotator`.

- [ ] **Step 1: Write the failing test**

```python
# plugins/grading/python/tests/test_role_catalog.py
from pathlib import Path

import yaml

CATALOG = Path(__file__).resolve().parents[2] / "config" / "role_catalog.yaml"

EXPECTED_ROLES = {
    "pdf_translator",
    "seed_gen",
    "seed_validator",
    "materialize_seed",
    "axis_criterion_drafter",
    "judge",
    "critic",
    "overlay_critic",
    "question_workup",
    "gold_annotator",
}


def test_catalog_exists():
    assert CATALOG.is_file()


def test_catalog_has_all_expected_roles():
    data = yaml.safe_load(CATALOG.read_text())
    declared = {r["name"] for r in data["roles"]}
    assert declared == EXPECTED_ROLES, declared.symmetric_difference(EXPECTED_ROLES)


def test_every_role_has_description():
    data = yaml.safe_load(CATALOG.read_text())
    for role in data["roles"]:
        assert role.get("description"), role["name"]
```

- [ ] **Step 2: Run to confirm failure**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/test_role_catalog.py -v
```

Expected: FAIL (file not found).

- [ ] **Step 3: Write the catalog**

Create `plugins/grading/config/role_catalog.yaml`:

```yaml
# Canonical list of subagent roles dispatched by the grading plugin's stages.
# Every operation tagged with `role:` must appear here.
# tier_dispatch.yaml binds each role to a model.

roles:
  - name: pdf_translator
    description: Translates a PDF (rendered page images) into canonical markdown with figure markers. Stage 0.
  - name: seed_gen
    description: Generates a batch of seed questions for one type, spanning >= J topical domains, in one structured JSON response. Stage 1.
  - name: seed_validator
    description: Receives a batch of seeds, returns per-seed well_formed = yes / no / borderline + rationale. Stage 1, optional pass.
  - name: materialize_seed
    description: For one seed, generates 9 quality answers + axis-perturbation answers + a throwaway 2-5 concept overlay + gold per-concept-axis coverage, in one structured JSON response. Stage 2.
  - name: axis_criterion_drafter
    description: Drafts initial score-level criteria (full / partial / none) for every axis of one type. Stage 2 initialization.
  - name: judge
    description: For one question's batch of answers, classifies each (answer, concept, axis) coverage as full / partial / none with a 1-2 sentence rationale. Stage 2 iterations + Stage 4 gold grade.
  - name: critic
    description: Sees the current rubric + criterion outcomes + concrete train-set failures, proposes weight/criterion revisions. Stage 2.
  - name: overlay_critic
    description: Proposes refinements to a per-question concept overlay only (weights and relevant_axes). Universal layer is untouchable. Stage 3.
  - name: question_workup
    description: For one assessment question, materializes synthetic answers + axis perturbations + the per-question concept overlay + gold coverage. Stage 3.
  - name: gold_annotator
    description: Annotates gold per-concept-axis coverage on a synthetic answer. May be merged into materialize_seed / question_workup or dispatched standalone, depending on stage. Used in Stages 2 and 3.
```

- [ ] **Step 4: Run to verify pass**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/test_role_catalog.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/grading/config/role_catalog.yaml plugins/grading/python/tests/test_role_catalog.py
git commit -m "feat(grading-plugin): role catalog with 10 declared subagent roles"
```

---

## Task 4: tier_dispatch.yaml

**Files:**
- Create: `plugins/grading/config/tier_dispatch.yaml`
- Test: `plugins/grading/python/tests/test_tier_dispatch.py`

- [ ] **Step 1: Write the failing test**

```python
# plugins/grading/python/tests/test_tier_dispatch.py
from pathlib import Path

import yaml

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
TIER_DISPATCH = CONFIG_DIR / "tier_dispatch.yaml"
ROLE_CATALOG = CONFIG_DIR / "role_catalog.yaml"

SUPPORTED_TIERS = {
    "claude-opus-4-7",
    "claude-sonnet-4-6",
    "claude-haiku-4-5",
}


def _roles_in_catalog() -> set[str]:
    data = yaml.safe_load(ROLE_CATALOG.read_text())
    return {r["name"] for r in data["roles"]}


def test_default_tier_supported():
    data = yaml.safe_load(TIER_DISPATCH.read_text())
    assert data["default_tier"] in SUPPORTED_TIERS


def test_every_role_in_catalog_is_mapped():
    data = yaml.safe_load(TIER_DISPATCH.read_text())
    mapped = set(data["roles"].keys())
    catalog = _roles_in_catalog()
    missing = catalog - mapped
    assert not missing, f"unmapped roles: {missing}"


def test_every_mapped_role_exists_in_catalog():
    data = yaml.safe_load(TIER_DISPATCH.read_text())
    mapped = set(data["roles"].keys())
    catalog = _roles_in_catalog()
    orphans = mapped - catalog
    assert not orphans, f"orphan role mappings: {orphans}"


def test_every_mapped_tier_supported():
    data = yaml.safe_load(TIER_DISPATCH.read_text())
    for role, tier in data["roles"].items():
        assert tier in SUPPORTED_TIERS, f"role {role!r} -> unsupported tier {tier!r}"
```

- [ ] **Step 2: Run to confirm failure**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/test_tier_dispatch.py -v
```

Expected: FAIL (file not found).

- [ ] **Step 3: Write the config (matches spec §8.4)**

Create `plugins/grading/config/tier_dispatch.yaml`:

```yaml
# Maps subagent role -> tier (model). role_catalog.yaml is the canonical
# list of declared roles; this file binds each to a tier.
# Tier names must be Claude Code-resolvable model identifiers.

default_tier: claude-sonnet-4-6

roles:
  pdf_translator:           claude-opus-4-7
  seed_gen:                 claude-sonnet-4-6
  seed_validator:           claude-haiku-4-5
  materialize_seed:         claude-opus-4-7
  axis_criterion_drafter:   claude-sonnet-4-6
  judge:                    claude-opus-4-7
  critic:                   claude-opus-4-7
  overlay_critic:           claude-sonnet-4-6
  question_workup:          claude-opus-4-7
  gold_annotator:           claude-opus-4-7

# Future: Ollama Gemma4 entries below once integrated.
# gold_annotator: ollama:gemma4-26b
```

- [ ] **Step 4: Run to verify pass**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/test_tier_dispatch.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/grading/config/tier_dispatch.yaml plugins/grading/python/tests/test_tier_dispatch.py
git commit -m "feat(grading-plugin): tier_dispatch.yaml binding all 10 roles to Claude tiers"
```

---

## Task 5: pipeline.yaml

**Files:**
- Create: `plugins/grading/config/pipeline.yaml`
- Test: `plugins/grading/python/tests/test_pipeline_config.py`

Knobs come from spec §4 (across all stages).

- [ ] **Step 1: Write the failing test**

```python
# plugins/grading/python/tests/test_pipeline_config.py
from pathlib import Path

import yaml

PIPELINE = Path(__file__).resolve().parents[2] / "config" / "pipeline.yaml"


def test_pipeline_exists():
    assert PIPELINE.is_file()


def test_seeds_per_type_composition_sums_to_total():
    data = yaml.safe_load(PIPELINE.read_text())
    spt = data["seeds_per_type"]
    total = spt["default"]
    comp = spt["composition"]
    assert comp["from_user_curated"] + comp["from_source"] + comp["from_claude_knowledge"] == total


def test_score_bands_present_and_ordered():
    data = yaml.safe_load(PIPELINE.read_text())
    bands = data["score_bands"]
    for name in ("good", "less_good", "wrong"):
        lo, hi = bands[name]
        assert 0.0 <= lo < hi <= 1.0, name
    assert bands["wrong"][1] < bands["less_good"][0]
    assert bands["less_good"][1] < bands["good"][0]


def test_calibration_thresholds_present():
    data = yaml.safe_load(PIPELINE.read_text())
    c = data["calibration"]
    assert 0.0 < c["concept_vote_agreement_min"] <= 1.0
    assert 0.0 < c["score_band_satisfaction_min"] <= 1.0
    assert 0.0 < c["axis_discrimination_delta_min"] <= 1.0
    assert c["max_iterations"] >= 1


def test_parallelism_knobs_present():
    data = yaml.safe_load(PIPELINE.read_text())
    p = data["parallelism"]
    assert p["max_parallel_questions"] >= 1
    assert p["max_parallel_seeds"] >= 1
```

- [ ] **Step 2: Run to confirm failure**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/test_pipeline_config.py -v
```

Expected: FAIL (file not found).

- [ ] **Step 3: Write the config**

Create `plugins/grading/config/pipeline.yaml`:

```yaml
# Tunable knobs for the grading plugin's preprocessing pipeline.
# Every value here is overridable per-run via config.yaml in the run folder.
# Defaults reflect spec §4.

seeds_per_type:
  default: 8
  topical_domains_min: 6     # J in spec §4.2
  composition:
    from_user_curated: 2
    from_source: 2
    from_claude_knowledge: 4
  validation_pass_enabled: true

calibration:
  max_iterations: 6
  split:
    train: 0.60
    val: 0.20
    test: 0.20
  concept_vote_agreement_min: 0.85
  score_band_satisfaction_min: 0.90
  axis_discrimination_delta_min: 0.25
  proceed_on_warning: false

score_bands:
  good:      [0.85, 1.00]
  less_good: [0.40, 0.70]
  wrong:     [0.00, 0.30]

generate_rubric:
  good_count: 3
  less_good_count: 3
  wrong_count: 3
  axis_perturbation_count_per_axis: 1
  overlay_refinement_iterations: 3

parallelism:
  max_parallel_questions: 3
  max_parallel_seeds: 4

retries:
  max_redispatches: 2
```

- [ ] **Step 4: Run to verify pass**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/test_pipeline_config.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/grading/config/pipeline.yaml plugins/grading/python/tests/test_pipeline_config.py
git commit -m "feat(grading-plugin): pipeline.yaml knobs (seeds, calibration, bands, parallelism)"
```

---

## Task 6: Schema — type catalog and TypeName enum

**Files:**
- Create: `plugins/grading/python/schema.py`
- Test: `plugins/grading/python/tests/test_schema.py`

Spec §3.1 fixes the 10 type names. Spec §3.5 defines `inputs/type_catalog.yaml` as `{description, candidate_axes}` per type.

- [ ] **Step 1: Write the failing test**

```python
# plugins/grading/python/tests/test_schema.py
import pytest

from plugins.grading.python.schema import TypeName, TypeCatalog, TypeCatalogEntry


def test_type_name_has_ten_values():
    assert len(list(TypeName)) == 10


def test_type_name_expected_set():
    expected = {
        "DEFINITION",
        "DISTINCTION",
        "MECHANISM",
        "CLASSIFICATION",
        "ENUMERATION",
        "EXAMPLE_GENERATION",
        "ERROR_IDENTIFICATION",
        "COMPARISON",
        "APPLICATION",
        "PROOF_OR_ARGUMENT",
    }
    assert {t.value for t in TypeName} == expected


def test_type_catalog_round_trip():
    raw = {
        "types": [
            {
                "name": "MECHANISM",
                "description": "How a process unfolds.",
                "candidate_axes": ["causal_chain_correctness", "temporal_ordering"],
            }
        ]
    }
    catalog = TypeCatalog.model_validate(raw)
    assert catalog.types[0].name is TypeName.MECHANISM
    assert catalog.types[0].candidate_axes == ["causal_chain_correctness", "temporal_ordering"]


def test_type_catalog_rejects_unknown_type():
    raw = {"types": [{"name": "MADE_UP", "description": "x", "candidate_axes": ["a"]}]}
    with pytest.raises(Exception):
        TypeCatalog.model_validate(raw)


def test_type_catalog_rejects_empty_axes():
    raw = {"types": [{"name": "MECHANISM", "description": "x", "candidate_axes": []}]}
    with pytest.raises(Exception):
        TypeCatalog.model_validate(raw)
```

- [ ] **Step 2: Run to confirm failure**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/test_schema.py -v
```

Expected: ImportError on `plugins.grading.python.schema`.

- [ ] **Step 3: Implement the schema module (start with TypeName + TypeCatalog)**

Create `plugins/grading/python/schema.py`:

```python
"""Pydantic models + invariant validators for every grading-plugin artifact.

Spec reference: docs/superpowers/specs/2026-05-13-grading-plugin-design.md §3.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


WEIGHT_EPSILON = 1e-6


class TypeName(str, Enum):
    DEFINITION = "DEFINITION"
    DISTINCTION = "DISTINCTION"
    MECHANISM = "MECHANISM"
    CLASSIFICATION = "CLASSIFICATION"
    ENUMERATION = "ENUMERATION"
    EXAMPLE_GENERATION = "EXAMPLE_GENERATION"
    ERROR_IDENTIFICATION = "ERROR_IDENTIFICATION"
    COMPARISON = "COMPARISON"
    APPLICATION = "APPLICATION"
    PROOF_OR_ARGUMENT = "PROOF_OR_ARGUMENT"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TypeCatalogEntry(_Strict):
    name: TypeName
    description: str = Field(min_length=1)
    candidate_axes: list[str] = Field(min_length=1)

    @field_validator("candidate_axes")
    @classmethod
    def axes_nonempty_strings(cls, v: list[str]) -> list[str]:
        if any((not isinstance(a, str)) or not a.strip() for a in v):
            raise ValueError("candidate_axes entries must be non-empty strings")
        if len(set(v)) != len(v):
            raise ValueError("candidate_axes must be unique within a type")
        return v


class TypeCatalog(_Strict):
    types: list[TypeCatalogEntry] = Field(min_length=1)

    @field_validator("types")
    @classmethod
    def names_unique(cls, v: list[TypeCatalogEntry]) -> list[TypeCatalogEntry]:
        names = [t.name for t in v]
        if len(set(names)) != len(names):
            raise ValueError("type names must be unique")
        return v
```

- [ ] **Step 4: Run to verify pass**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/test_schema.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/grading/python/schema.py plugins/grading/python/tests/test_schema.py
git commit -m "feat(grading-plugin): TypeName enum and TypeCatalog schema"
```

---

## Task 7: Schema — UniversalRubric + validate_universal_rubric

**Files:**
- Modify: `plugins/grading/python/schema.py`
- Modify: `plugins/grading/python/tests/test_schema.py`
- Create: `plugins/grading/python/tests/test_validators.py`

Spec §3.2(a) and §3.6 first bullet.

- [ ] **Step 1: Append tests to test_schema.py**

Append to `plugins/grading/python/tests/test_schema.py`:

```python
from plugins.grading.python.schema import (
    ScoreLevels,
    AxisDef,
    UniversalRubric,
    UniversalRubricStatus,
    Aggregate,
)


def _good_axis(name="a", weight=1.0):
    return {
        "name": name,
        "description": "x",
        "weight": weight,
        "score_levels": {
            "full":    {"value": 1.0, "criterion": "all"},
            "partial": {"value": 0.5, "criterion": "some"},
            "none":    {"value": 0.0, "criterion": "none"},
        },
    }


def test_universal_rubric_round_trip():
    raw = {
        "type": "MECHANISM",
        "status": "frozen",
        "axes": [_good_axis("causal", 0.6), _good_axis("temporal", 0.4)],
        "aggregate": {"method": "weighted_mean", "out_of": 10.0},
    }
    r = UniversalRubric.model_validate(raw)
    assert r.type is TypeName.MECHANISM
    assert len(r.axes) == 2


def test_universal_rubric_status_values():
    assert {s.value for s in UniversalRubricStatus} == {
        "frozen",
        "warning_test_marginal",
        "failed_to_converge",
    }


def test_score_level_value_constants():
    sl = ScoreLevels.model_validate({
        "full":    {"value": 1.0, "criterion": "x"},
        "partial": {"value": 0.5, "criterion": "x"},
        "none":    {"value": 0.0, "criterion": "x"},
    })
    assert sl.full.value == 1.0 and sl.partial.value == 0.5 and sl.none.value == 0.0
```

- [ ] **Step 2: Create the validator-specific tests**

Create `plugins/grading/python/tests/test_validators.py`:

```python
import pytest

from plugins.grading.python.schema import (
    validate_universal_rubric,
)


def _axis(name, weight, full=1.0, partial=0.5, none=0.0):
    return {
        "name": name,
        "description": "x",
        "weight": weight,
        "score_levels": {
            "full":    {"value": full,    "criterion": "x"},
            "partial": {"value": partial, "criterion": "x"},
            "none":    {"value": none,    "criterion": "x"},
        },
    }


def _good_rubric():
    return {
        "type": "MECHANISM",
        "status": "frozen",
        "axes": [_axis("a", 0.5), _axis("b", 0.5)],
        "aggregate": {"method": "weighted_mean", "out_of": 10.0},
    }


def test_validate_universal_rubric_accepts_good():
    validate_universal_rubric(_good_rubric())


def test_validate_universal_rubric_rejects_negative_weight():
    raw = _good_rubric()
    raw["axes"][0]["weight"] = -0.1
    with pytest.raises(ValueError, match="weight"):
        validate_universal_rubric(raw)


def test_validate_universal_rubric_rejects_weights_not_summing_to_one():
    raw = _good_rubric()
    raw["axes"][0]["weight"] = 0.4
    raw["axes"][1]["weight"] = 0.4
    with pytest.raises(ValueError, match="sum"):
        validate_universal_rubric(raw)


def test_validate_universal_rubric_rejects_non_monotone_levels():
    raw = _good_rubric()
    # partial > full violates monotonicity
    raw["axes"][0]["score_levels"]["partial"]["value"] = 0.99
    raw["axes"][0]["score_levels"]["full"]["value"] = 0.5
    with pytest.raises(ValueError, match="monoton"):
        validate_universal_rubric(raw)


def test_validate_universal_rubric_rejects_zero_out_of():
    raw = _good_rubric()
    raw["aggregate"]["out_of"] = 0.0
    with pytest.raises(ValueError, match="out_of"):
        validate_universal_rubric(raw)


def test_validate_universal_rubric_rejects_duplicate_axes():
    raw = _good_rubric()
    raw["axes"][1]["name"] = raw["axes"][0]["name"]
    with pytest.raises(ValueError, match="duplicate"):
        validate_universal_rubric(raw)
```

- [ ] **Step 3: Run to confirm failures**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/test_schema.py plugins/grading/python/tests/test_validators.py -v
```

Expected: ImportErrors / NameErrors for the new symbols.

- [ ] **Step 4: Extend schema.py**

Append to `plugins/grading/python/schema.py`:

```python
class ScoreLevelEntry(_Strict):
    value: float
    criterion: str = Field(min_length=1)


class ScoreLevels(_Strict):
    full: ScoreLevelEntry
    partial: ScoreLevelEntry
    none: ScoreLevelEntry


class AxisDef(_Strict):
    name: str = Field(min_length=1)
    description: str = ""
    weight: float = Field(ge=0.0)
    score_levels: ScoreLevels


class Aggregate(_Strict):
    method: str = Field(min_length=1)
    out_of: float = Field(gt=0.0)


class UniversalRubricStatus(str, Enum):
    FROZEN = "frozen"
    WARNING_TEST_MARGINAL = "warning_test_marginal"
    FAILED_TO_CONVERGE = "failed_to_converge"


class UniversalRubric(_Strict):
    type: TypeName
    status: UniversalRubricStatus
    axes: list[AxisDef] = Field(min_length=1)
    aggregate: Aggregate


def validate_universal_rubric(raw: dict) -> UniversalRubric:
    """Apply §3.6 first bullet's invariants.

    Returns the validated model. Raises ValueError with a useful message on
    any invariant violation.
    """
    rubric = UniversalRubric.model_validate(raw)

    names = [a.name for a in rubric.axes]
    if len(set(names)) != len(names):
        raise ValueError(f"duplicate axis names: {names}")

    total = sum(a.weight for a in rubric.axes)
    if abs(total - 1.0) > WEIGHT_EPSILON:
        raise ValueError(f"axis weights must sum to 1.0; got {total}")

    for axis in rubric.axes:
        sl = axis.score_levels
        if not (sl.full.value > sl.partial.value > sl.none.value):
            raise ValueError(
                f"axis {axis.name!r}: score_levels not monotone "
                f"(full={sl.full.value}, partial={sl.partial.value}, none={sl.none.value})"
            )

    return rubric
```

- [ ] **Step 5: Run to verify pass**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/test_schema.py plugins/grading/python/tests/test_validators.py -v
```

Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add plugins/grading/python/schema.py plugins/grading/python/tests/test_schema.py plugins/grading/python/tests/test_validators.py
git commit -m "feat(grading-plugin): UniversalRubric schema + validate_universal_rubric"
```

---

## Task 8: Schema — PerQuestionRubric + validate_per_question_rubric

**Files:**
- Modify: `plugins/grading/python/schema.py`
- Modify: `plugins/grading/python/tests/test_validators.py`

Spec §3.2(b) and §3.6 second bullet.

- [ ] **Step 1: Append validator tests**

Append to `plugins/grading/python/tests/test_validators.py`:

```python
from plugins.grading.python.schema import validate_per_question_rubric, UniversalRubric


def _universal_for_test():
    return UniversalRubric.model_validate({
        "type": "MECHANISM",
        "status": "frozen",
        "axes": [_axis("a", 0.6), _axis("b", 0.4)],
        "aggregate": {"method": "weighted_mean", "out_of": 10.0},
    })


def _good_pqr():
    return {
        "question_id": "Q03",
        "course": "data_quality",
        "type": "MECHANISM",
        "universal_rubric_ref": "types/MECHANISM/universal_rubric.yaml",
        "concept_overlay": [
            {"id": "c1", "text": "...", "weight": 0.6, "relevant_axes": ["a"]},
            {"id": "c2", "text": "...", "weight": 0.4, "relevant_axes": ["a", "b"]},
        ],
        "status": "frozen",
    }


def test_validate_pqr_accepts_good():
    validate_per_question_rubric(_good_pqr(), universal=_universal_for_test())


def test_validate_pqr_rejects_weights_not_summing_to_one():
    raw = _good_pqr()
    raw["concept_overlay"][0]["weight"] = 0.3
    with pytest.raises(ValueError, match="sum"):
        validate_per_question_rubric(raw, universal=_universal_for_test())


def test_validate_pqr_rejects_empty_relevant_axes():
    raw = _good_pqr()
    raw["concept_overlay"][0]["relevant_axes"] = []
    with pytest.raises(ValueError, match="relevant_axes"):
        validate_per_question_rubric(raw, universal=_universal_for_test())


def test_validate_pqr_rejects_relevant_axes_outside_universal():
    raw = _good_pqr()
    raw["concept_overlay"][0]["relevant_axes"] = ["nonexistent_axis"]
    with pytest.raises(ValueError, match="relevant_axes"):
        validate_per_question_rubric(raw, universal=_universal_for_test())


def test_validate_pqr_rejects_type_mismatch_with_universal():
    raw = _good_pqr()
    raw["type"] = "DEFINITION"
    with pytest.raises(ValueError, match="type"):
        validate_per_question_rubric(raw, universal=_universal_for_test())


def test_validate_pqr_rejects_duplicate_concept_ids():
    raw = _good_pqr()
    raw["concept_overlay"][1]["id"] = raw["concept_overlay"][0]["id"]
    with pytest.raises(ValueError, match="duplicate"):
        validate_per_question_rubric(raw, universal=_universal_for_test())
```

- [ ] **Step 2: Run to confirm failure**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/test_validators.py -v
```

Expected: ImportError on `validate_per_question_rubric`.

- [ ] **Step 3: Extend schema.py**

Append to `plugins/grading/python/schema.py`:

```python
class ConceptOverlayEntry(_Strict):
    id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    weight: float = Field(ge=0.0)
    relevant_axes: list[str] = Field(min_length=1)


class PerQuestionRubricStatus(str, Enum):
    FROZEN = "frozen"
    DEGRADED = "degraded"


class PerQuestionRubric(_Strict):
    question_id: str = Field(min_length=1)
    course: str = Field(min_length=1)
    type: TypeName
    universal_rubric_ref: str = Field(min_length=1)
    concept_overlay: list[ConceptOverlayEntry] = Field(min_length=1)
    status: PerQuestionRubricStatus


def validate_per_question_rubric(
    raw: dict,
    *,
    universal: UniversalRubric,
) -> PerQuestionRubric:
    """Apply §3.6 second bullet's invariants."""
    pqr = PerQuestionRubric.model_validate(raw)

    if pqr.type != universal.type:
        raise ValueError(
            f"type mismatch: per-question rubric says {pqr.type}, "
            f"universal rubric says {universal.type}"
        )

    ids = [c.id for c in pqr.concept_overlay]
    if len(set(ids)) != len(ids):
        raise ValueError(f"duplicate concept ids: {ids}")

    total = sum(c.weight for c in pqr.concept_overlay)
    if abs(total - 1.0) > WEIGHT_EPSILON:
        raise ValueError(f"concept weights must sum to 1.0; got {total}")

    universal_axis_names = {a.name for a in universal.axes}
    for c in pqr.concept_overlay:
        if not c.relevant_axes:
            raise ValueError(f"concept {c.id!r}: relevant_axes empty")
        bad = set(c.relevant_axes) - universal_axis_names
        if bad:
            raise ValueError(
                f"concept {c.id!r}: relevant_axes {sorted(bad)} not in universal axes"
            )

    return pqr
```

- [ ] **Step 4: Run to verify pass**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/test_validators.py -v
```

Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add plugins/grading/python/schema.py plugins/grading/python/tests/test_validators.py
git commit -m "feat(grading-plugin): PerQuestionRubric schema + validate_per_question_rubric"
```

---

## Task 9: Schema — Grades + validate_grade

**Files:**
- Modify: `plugins/grading/python/schema.py`
- Modify: `plugins/grading/python/tests/test_validators.py`

Spec §3.2(c) and §3.6 third bullet.

- [ ] **Step 1: Append validator tests**

Append to `plugins/grading/python/tests/test_validators.py`:

```python
from plugins.grading.python.schema import validate_grade


def _good_grades(universal, pqr):
    return {
        "question_id": "Q03",
        "rubric_ref": "rubrics/data_quality/Q03/rubric.yaml",
        "universal_rubric_ref": "types/MECHANISM/universal_rubric.yaml",
        "grades": [
            {
                "answer_id": "good_1",
                "per_concept": {
                    "c1": {"a": "full"},
                    "c2": {"a": "full", "b": "full"},
                },
                "aggregate": 1.0,
                "aggregate_x10": 10.0,
            },
        ],
        "summary": {
            "mean_by_quality": {"good": 1.0, "less_good": 0.5, "wrong": 0.0},
            "ordering_preserved": True,
            "bands_satisfied": True,
            "axis_discrimination_passed": True,
        },
    }


def test_validate_grade_accepts_good():
    universal = _universal_for_test()
    pqr = validate_per_question_rubric(_good_pqr(), universal=universal)
    validate_grade(_good_grades(universal, pqr), rubric=pqr, universal=universal)


def test_validate_grade_rejects_aggregate_out_of_range():
    universal = _universal_for_test()
    pqr = validate_per_question_rubric(_good_pqr(), universal=universal)
    raw = _good_grades(universal, pqr)
    raw["grades"][0]["aggregate"] = 1.5
    with pytest.raises(ValueError, match="aggregate"):
        validate_grade(raw, rubric=pqr, universal=universal)


def test_validate_grade_rejects_x10_inconsistent_with_aggregate():
    universal = _universal_for_test()
    pqr = validate_per_question_rubric(_good_pqr(), universal=universal)
    raw = _good_grades(universal, pqr)
    raw["grades"][0]["aggregate_x10"] = 5.0   # but aggregate = 1.0 -> should be 10.0
    with pytest.raises(ValueError, match="aggregate_x10"):
        validate_grade(raw, rubric=pqr, universal=universal)


def test_validate_grade_rejects_missing_concept_axis_pair():
    universal = _universal_for_test()
    pqr = validate_per_question_rubric(_good_pqr(), universal=universal)
    raw = _good_grades(universal, pqr)
    # c2 has relevant_axes [a, b] but per_concept only supplies a
    raw["grades"][0]["per_concept"]["c2"] = {"a": "full"}
    with pytest.raises(ValueError, match="missing"):
        validate_grade(raw, rubric=pqr, universal=universal)


def test_validate_grade_rejects_unknown_level():
    universal = _universal_for_test()
    pqr = validate_per_question_rubric(_good_pqr(), universal=universal)
    raw = _good_grades(universal, pqr)
    raw["grades"][0]["per_concept"]["c1"]["a"] = "maybe"
    with pytest.raises(ValueError, match="level"):
        validate_grade(raw, rubric=pqr, universal=universal)
```

- [ ] **Step 2: Run to confirm failure**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/test_validators.py -v
```

Expected: ImportError on `validate_grade`.

- [ ] **Step 3: Extend schema.py**

Append to `plugins/grading/python/schema.py`:

```python
class Level(str, Enum):
    FULL = "full"
    PARTIAL = "partial"
    NONE = "none"


class AnswerGrade(_Strict):
    answer_id: str = Field(min_length=1)
    per_concept: dict[str, dict[str, Level]]
    aggregate: float = Field(ge=0.0, le=1.0)
    aggregate_x10: float = Field(ge=0.0, le=10.0)
    target_axis_drop_observed: float | None = None


class GradesSummary(_Strict):
    mean_by_quality: dict[str, float]
    ordering_preserved: bool
    bands_satisfied: bool
    axis_discrimination_passed: bool


class Grades(_Strict):
    question_id: str = Field(min_length=1)
    rubric_ref: str = Field(min_length=1)
    universal_rubric_ref: str = Field(min_length=1)
    grades: list[AnswerGrade] = Field(min_length=1)
    summary: GradesSummary


def validate_grade(
    raw: dict,
    *,
    rubric: PerQuestionRubric,
    universal: UniversalRubric,
) -> Grades:
    """Apply §3.6 third bullet's invariants."""
    grades = Grades.model_validate(raw)

    if grades.question_id != rubric.question_id:
        raise ValueError(
            f"question_id mismatch: grades={grades.question_id}, "
            f"rubric={rubric.question_id}"
        )

    expected_pairs: set[tuple[str, str]] = set()
    for c in rubric.concept_overlay:
        for axis in c.relevant_axes:
            expected_pairs.add((c.id, axis))

    for g in grades.grades:
        present_pairs: set[tuple[str, str]] = set()
        for concept_id, axis_map in g.per_concept.items():
            for axis_name in axis_map:
                present_pairs.add((concept_id, axis_name))
        missing = expected_pairs - present_pairs
        if missing:
            raise ValueError(f"answer {g.answer_id!r}: missing (concept,axis) pairs: {sorted(missing)}")
        extras = present_pairs - expected_pairs
        if extras:
            raise ValueError(f"answer {g.answer_id!r}: unexpected (concept,axis) pairs: {sorted(extras)}")

        if abs(g.aggregate_x10 - g.aggregate * 10.0) > WEIGHT_EPSILON:
            raise ValueError(
                f"answer {g.answer_id!r}: aggregate_x10 ({g.aggregate_x10}) "
                f"!= aggregate ({g.aggregate}) * 10"
            )

    return grades
```

- [ ] **Step 4: Run to verify pass**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/test_validators.py -v
```

Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add plugins/grading/python/schema.py plugins/grading/python/tests/test_validators.py
git commit -m "feat(grading-plugin): Grades schema + validate_grade"
```

---

## Task 10: Schema — SeedQuestion, Question, SourceMeta

**Files:**
- Modify: `plugins/grading/python/schema.py`
- Modify: `plugins/grading/python/tests/test_schema.py`

Spec §3.0 (taxonomy of inputs/outputs) and §3.5.

- [ ] **Step 1: Append tests**

Append to `plugins/grading/python/tests/test_schema.py`:

```python
from plugins.grading.python.schema import (
    SeedQuestion,
    Question,
    SourceMeta,
    SourceFormat,
)


def test_seed_question_minimal():
    sq = SeedQuestion.model_validate({
        "seed_id": "MECHANISM_001",
        "type": "MECHANISM",
        "topic": "physics",
        "source": "claude_knowledge",
        "text": "How does evaporation cool a liquid?",
        "generated_by": "claude-sonnet-4-6",
        "user_review": {"approved": True},
    })
    assert sq.user_review.approved is True


def test_question_minimal():
    q = Question.model_validate({
        "question_id": "Q03",
        "course": "data_quality",
        "type": "MECHANISM",
        "text": "Describe how schema drift develops.",
        "sources": ["data_quality_lecture_01"],
    })
    assert q.type is TypeName.MECHANISM


def test_source_meta_pdf():
    sm = SourceMeta.model_validate({
        "format": "pdf",
        "courses": ["data_quality"],
        "topics": ["data quality"],
        "extraction": {"role": "pdf_translator", "tier": "claude-opus-4-7", "ts": "2026-05-13T00:00:00Z"},
        "content_sha": "deadbeef" * 8,
        "figure_count": 5,
        "page_count": 12,
    })
    assert sm.format is SourceFormat.PDF


def test_source_meta_markdown_no_figures():
    sm = SourceMeta.model_validate({
        "format": "markdown",
        "courses": ["data_quality"],
        "topics": [],
        "extraction": None,
        "content_sha": "abc" * 22,   # 66 chars, fine
        "figure_count": 0,
        "page_count": 0,
    })
    assert sm.format is SourceFormat.MARKDOWN
```

- [ ] **Step 2: Run to confirm failure**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/test_schema.py -v
```

Expected: ImportErrors.

- [ ] **Step 3: Extend schema.py**

Append to `plugins/grading/python/schema.py`:

```python
class UserReview(_Strict):
    approved: bool
    note: str | None = None


class SeedQuestion(_Strict):
    seed_id: str = Field(min_length=1)
    type: TypeName
    topic: str = Field(min_length=1)
    source: str = Field(min_length=1)         # "curated" | "source:<name>" | "claude_knowledge"
    text: str = Field(min_length=1)
    generated_by: str = Field(min_length=1)   # tier id at generation time
    user_review: UserReview


class Question(_Strict):
    question_id: str = Field(min_length=1)
    course: str = Field(min_length=1)
    type: TypeName
    text: str = Field(min_length=1)
    sources: list[str] = Field(default_factory=list)
    notes: str | None = None


class SourceFormat(str, Enum):
    PDF = "pdf"
    MARKDOWN = "markdown"


class ExtractionMeta(_Strict):
    role: str
    tier: str
    ts: str


class SourceMeta(_Strict):
    format: SourceFormat
    courses: list[str]
    topics: list[str]
    extraction: ExtractionMeta | None
    content_sha: str = Field(min_length=8)
    figure_count: int = Field(ge=0)
    page_count: int = Field(ge=0)
```

- [ ] **Step 4: Run to verify pass**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/test_schema.py -v
```

Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add plugins/grading/python/schema.py plugins/grading/python/tests/test_schema.py
git commit -m "feat(grading-plugin): SeedQuestion, Question, SourceMeta schemas"
```

---

## Task 11: Schema — RunMeta, RunConfig, CalibrationMeta, SyntheticAnswers, GoldConceptCoverage, TimelineEvent

**Files:**
- Modify: `plugins/grading/python/schema.py`
- Modify: `plugins/grading/python/tests/test_schema.py`

Spec §3.5 + §5.6 (timeline events).

- [ ] **Step 1: Append tests**

Append to `plugins/grading/python/tests/test_schema.py`:

```python
from plugins.grading.python.schema import (
    RunMeta,
    RunConfig,
    CalibrationMeta,
    SyntheticAnswerSet,
    AnswerQuality,
    GoldConceptCoverage,
    TimelineEvent,
    TimelineEventType,
)


def test_run_meta_minimal():
    rm = RunMeta.model_validate({
        "run_id": "2026-05-13_13-15-00Z__abc1",
        "started_at": "2026-05-13T13:15:00Z",
        "ended_at": "2026-05-13T14:00:00Z",
        "git_sha": "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
        "git_dirty": False,
        "status": "success",
        "stages_run": ["calibrate_types"],
    })
    assert rm.run_id.startswith("2026-05-13")


def test_synthetic_answer_qualities():
    assert {q.value for q in AnswerQuality} == {
        "good", "less_good", "wrong", "axis_perturbation",
    }


def test_synthetic_answer_set_axis_perturbation_requires_target_axis():
    raw = {
        "question_id": "Q03",
        "answers": [
            {
                "answer_id": "ap_1",
                "quality": "axis_perturbation",
                "text": "...",
                "target_axis": None,   # missing
            }
        ],
    }
    with pytest.raises(Exception):
        SyntheticAnswerSet.model_validate(raw)


def test_synthetic_answer_set_good_requires_no_target_axis():
    SyntheticAnswerSet.model_validate({
        "question_id": "Q03",
        "answers": [
            {"answer_id": "good_1", "quality": "good", "text": "..."},
        ],
    })


def test_timeline_event_event_types():
    assert {e.value for e in TimelineEventType} == {
        "stage", "iteration", "subagent_dispatch",
        "python_helper_call", "gate_decision", "error",
    }


def test_timeline_event_round_trip():
    ev = TimelineEvent.model_validate({
        "ts": "2026-05-13T16:15:33.214Z",
        "event_type": "subagent_dispatch",
        "actor": "main_agent",
        "name": "materialize_seed:MECHANISM_seed_001",
        "phase": "start",
        "details": {"role": "materialize_seed"},
    })
    assert ev.phase == "start"
```

- [ ] **Step 2: Run to confirm failure**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/test_schema.py -v
```

Expected: ImportErrors.

- [ ] **Step 3: Extend schema.py**

Append to `plugins/grading/python/schema.py`:

```python
class RunStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class RunMeta(_Strict):
    run_id: str = Field(min_length=1)
    started_at: str
    ended_at: str | None = None
    git_sha: str | None = None
    git_dirty: bool = False
    status: RunStatus
    stages_run: list[str] = Field(default_factory=list)


class RunConfig(_Strict):
    """The config that drove a run; mirror of pipeline.yaml plus overrides."""
    seeds_per_type: dict
    calibration: dict
    score_bands: dict
    generate_rubric: dict
    parallelism: dict
    retries: dict


class CalibrationMeta(_Strict):
    type: TypeName
    seed_ids_train: list[str]
    seed_ids_val: list[str]
    seed_ids_test: list[str]
    iterations: list[dict]
    final_criterion_outcomes: dict
    limitation_notes: str | None = None


class AnswerQuality(str, Enum):
    GOOD = "good"
    LESS_GOOD = "less_good"
    WRONG = "wrong"
    AXIS_PERTURBATION = "axis_perturbation"


class SyntheticAnswer(_Strict):
    answer_id: str = Field(min_length=1)
    quality: AnswerQuality
    text: str = Field(min_length=1)
    target_axis: str | None = None

    @field_validator("target_axis")
    @classmethod
    def axis_perturbation_requires_target(cls, v, info):
        # Field-level validators in pydantic v2 see other values via info.data
        quality = info.data.get("quality")
        if quality is AnswerQuality.AXIS_PERTURBATION and not v:
            raise ValueError("axis_perturbation answers must specify target_axis")
        if quality is not AnswerQuality.AXIS_PERTURBATION and v:
            raise ValueError(f"non-axis_perturbation answer must not set target_axis (got {v})")
        return v


class SyntheticAnswerSet(_Strict):
    question_id: str = Field(min_length=1)
    answers: list[SyntheticAnswer] = Field(min_length=1)


class GoldConceptCoverage(_Strict):
    """Per-answer-per-concept-per-axis Claude-annotated gold labels."""
    question_id: str
    coverage: dict[str, dict[str, dict[str, Level]]]
    # coverage[answer_id][concept_id][axis_name] = level
    target_axis_weakness: dict[str, str] = Field(default_factory=dict)
    # target_axis_weakness[answer_id] = axis name (for axis_perturbation answers)


class TimelineEventType(str, Enum):
    STAGE = "stage"
    ITERATION = "iteration"
    SUBAGENT_DISPATCH = "subagent_dispatch"
    PYTHON_HELPER_CALL = "python_helper_call"
    GATE_DECISION = "gate_decision"
    ERROR = "error"


class TimelineEventPhase(str, Enum):
    START = "start"
    END = "end"


class TimelineEvent(_Strict):
    ts: str
    event_type: TimelineEventType
    actor: str
    name: str
    phase: TimelineEventPhase
    details: dict = Field(default_factory=dict)
```

- [ ] **Step 4: Run to verify pass**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/test_schema.py -v
```

Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add plugins/grading/python/schema.py plugins/grading/python/tests/test_schema.py
git commit -m "feat(grading-plugin): RunMeta/Config/Calibration/Answers/Coverage/Timeline schemas"
```

---

## Task 12: Aggregation §3.3 — worked example + implementation

**Files:**
- Create: `plugins/grading/python/aggregation.py`
- Create: `plugins/grading/python/tests/test_aggregation.py`

Spec §3.3.

- [ ] **Step 1: Write the failing test (Q03 worked example)**

Create `plugins/grading/python/tests/test_aggregation.py`:

```python
import math

import pytest

from plugins.grading.python.aggregation import (
    JudgeVote,
    AggregateResult,
    LEVEL_VALUES,
    compute_aggregate,
)


def test_level_values_match_spec():
    assert LEVEL_VALUES == {"full": 1.0, "partial": 0.5, "none": 0.0}


def test_q03_worked_example():
    """Spec §3.3 worked example.

    Universal axis weights: causal=0.35, temporal=0.25, completeness=0.25, deps=0.15
    Concept weights: C1=0.30, C2=0.25, C3=0.20, C4=0.25
    Per-concept scores from votes (back-computed to match spec):
      C1 (relevant=[causal]):                causal=full         -> 1.0
      C2 (relevant=[temporal,completeness]): both full           -> 1.0
      C3 (relevant=[causal,completeness]):   causal=partial,
                                              completeness=full  -> 0.7083
      C4 (relevant=[temporal,deps]):         temporal=full,
                                              deps=partial       -> 0.8125
    aggregate = 0.30*1 + 0.25*1 + 0.20*0.7083 + 0.25*0.8125 = 0.8948
    """
    axis_weights = {
        "causal": 0.35,
        "temporal": 0.25,
        "completeness": 0.25,
        "deps": 0.15,
    }
    concept_weights = {"C1": 0.30, "C2": 0.25, "C3": 0.20, "C4": 0.25}
    concept_relevant_axes = {
        "C1": ["causal"],
        "C2": ["temporal", "completeness"],
        "C3": ["causal", "completeness"],
        "C4": ["temporal", "deps"],
    }
    votes = [
        JudgeVote("C1", "causal", "full"),
        JudgeVote("C2", "temporal", "full"),
        JudgeVote("C2", "completeness", "full"),
        JudgeVote("C3", "causal", "partial"),
        JudgeVote("C3", "completeness", "full"),
        JudgeVote("C4", "temporal", "full"),
        JudgeVote("C4", "deps", "partial"),
    ]
    result = compute_aggregate(
        axis_weights=axis_weights,
        concept_weights=concept_weights,
        concept_relevant_axes=concept_relevant_axes,
        votes=votes,
    )
    assert math.isclose(result.per_concept_score["C1"], 1.0)
    assert math.isclose(result.per_concept_score["C2"], 1.0)
    assert math.isclose(result.per_concept_score["C3"], 0.425 / 0.60)
    assert math.isclose(result.per_concept_score["C4"], 0.325 / 0.40)
    assert math.isclose(result.aggregate, 0.8948, abs_tol=1e-3)
    assert math.isclose(result.aggregate_x10, 8.948, abs_tol=1e-2)


def test_all_full_gives_one():
    axis_weights = {"a": 0.5, "b": 0.5}
    concept_weights = {"C": 1.0}
    relevant = {"C": ["a", "b"]}
    votes = [JudgeVote("C", "a", "full"), JudgeVote("C", "b", "full")]
    r = compute_aggregate(
        axis_weights=axis_weights,
        concept_weights=concept_weights,
        concept_relevant_axes=relevant,
        votes=votes,
    )
    assert r.aggregate == 1.0 and r.aggregate_x10 == 10.0


def test_all_none_gives_zero():
    axis_weights = {"a": 1.0}
    concept_weights = {"C": 1.0}
    relevant = {"C": ["a"]}
    votes = [JudgeVote("C", "a", "none")]
    r = compute_aggregate(
        axis_weights=axis_weights,
        concept_weights=concept_weights,
        concept_relevant_axes=relevant,
        votes=votes,
    )
    assert r.aggregate == 0.0 and r.aggregate_x10 == 0.0


def test_missing_vote_raises():
    with pytest.raises(KeyError):
        compute_aggregate(
            axis_weights={"a": 1.0},
            concept_weights={"C": 1.0},
            concept_relevant_axes={"C": ["a"]},
            votes=[],
        )
```

- [ ] **Step 2: Run to confirm failure**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/test_aggregation.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement aggregation.py**

Create `plugins/grading/python/aggregation.py`:

```python
"""Aggregation formula from spec §3.3.

Single source of truth: aggregate_x10 = aggregate * 10 with aggregate ∈ [0, 1].
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


LEVEL_VALUES: dict[str, float] = {"full": 1.0, "partial": 0.5, "none": 0.0}


@dataclass(frozen=True)
class JudgeVote:
    concept_id: str
    axis: str
    level: str   # "full" | "partial" | "none"


@dataclass(frozen=True)
class AggregateResult:
    per_concept_score: Mapping[str, float]
    aggregate: float       # [0, 1]
    aggregate_x10: float   # [0, 10]


def compute_aggregate(
    *,
    axis_weights: Mapping[str, float],
    concept_weights: Mapping[str, float],
    concept_relevant_axes: Mapping[str, list[str]],
    votes: list[JudgeVote],
) -> AggregateResult:
    """Apply §3.3 formula.

    Inputs are assumed pre-validated (weights non-negative, etc.).
    Raises KeyError if a (concept, axis) pair declared in
    `concept_relevant_axes` has no matching vote.
    """
    vote_by_pair: dict[tuple[str, str], str] = {
        (v.concept_id, v.axis): v.level for v in votes
    }

    per_concept: dict[str, float] = {}
    for concept_id, axes in concept_relevant_axes.items():
        num = 0.0
        den = 0.0
        for axis in axes:
            weight = axis_weights[axis]
            level = vote_by_pair[(concept_id, axis)]
            num += weight * LEVEL_VALUES[level]
            den += weight
        per_concept[concept_id] = num / den if den > 0 else 0.0

    total_num = sum(concept_weights[c] * per_concept[c] for c in concept_weights)
    total_den = sum(concept_weights[c] for c in concept_weights)
    agg = total_num / total_den if total_den > 0 else 0.0

    return AggregateResult(
        per_concept_score=per_concept,
        aggregate=agg,
        aggregate_x10=agg * 10.0,
    )
```

- [ ] **Step 4: Run to verify pass**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/test_aggregation.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/grading/python/aggregation.py plugins/grading/python/tests/test_aggregation.py
git commit -m "feat(grading-plugin): aggregation formula (§3.3) with Q03 worked-example test"
```

---

## Task 13: Aggregation property tests (hypothesis)

**Files:**
- Create: `plugins/grading/python/tests/test_aggregation_invariant.py`

Spec §6.1: "property-based (hypothesis): random rubrics + random level inputs ⇒ aggregate ∈ [0, 1], …"

- [ ] **Step 1: Write the property tests**

Create `plugins/grading/python/tests/test_aggregation_invariant.py`:

```python
import math

from hypothesis import given, settings
from hypothesis import strategies as st

from plugins.grading.python.aggregation import (
    JudgeVote,
    LEVEL_VALUES,
    compute_aggregate,
)


def _normalize(weights: list[float]) -> list[float]:
    total = sum(weights)
    return [w / total for w in weights] if total > 0 else [1.0 / len(weights)] * len(weights)


@st.composite
def rubric_strategy(draw):
    n_axes = draw(st.integers(min_value=1, max_value=5))
    n_concepts = draw(st.integers(min_value=1, max_value=5))

    raw_axis_weights = draw(st.lists(
        st.floats(min_value=0.01, max_value=1.0, allow_nan=False, allow_infinity=False),
        min_size=n_axes, max_size=n_axes,
    ))
    axis_names = [f"a{i}" for i in range(n_axes)]
    axis_weights = dict(zip(axis_names, _normalize(raw_axis_weights), strict=True))

    raw_concept_weights = draw(st.lists(
        st.floats(min_value=0.01, max_value=1.0, allow_nan=False, allow_infinity=False),
        min_size=n_concepts, max_size=n_concepts,
    ))
    concept_names = [f"c{i}" for i in range(n_concepts)]
    concept_weights = dict(zip(concept_names, _normalize(raw_concept_weights), strict=True))

    concept_relevant_axes: dict[str, list[str]] = {}
    for c in concept_names:
        k = draw(st.integers(min_value=1, max_value=n_axes))
        chosen = draw(st.lists(st.sampled_from(axis_names), min_size=k, max_size=k, unique=True))
        concept_relevant_axes[c] = chosen

    levels: list[JudgeVote] = []
    for c, axes in concept_relevant_axes.items():
        for a in axes:
            level = draw(st.sampled_from(list(LEVEL_VALUES.keys())))
            levels.append(JudgeVote(c, a, level))

    return axis_weights, concept_weights, concept_relevant_axes, levels


@given(rubric_strategy())
@settings(max_examples=200, deadline=None)
def test_aggregate_in_unit_interval(payload):
    axis_w, concept_w, rel, votes = payload
    r = compute_aggregate(
        axis_weights=axis_w,
        concept_weights=concept_w,
        concept_relevant_axes=rel,
        votes=votes,
    )
    assert 0.0 <= r.aggregate <= 1.0


@given(rubric_strategy())
@settings(max_examples=200, deadline=None)
def test_aggregate_x10_consistent(payload):
    axis_w, concept_w, rel, votes = payload
    r = compute_aggregate(
        axis_weights=axis_w,
        concept_weights=concept_w,
        concept_relevant_axes=rel,
        votes=votes,
    )
    assert math.isclose(r.aggregate_x10, r.aggregate * 10.0, abs_tol=1e-9)
    assert 0.0 <= r.aggregate_x10 <= 10.0


@given(rubric_strategy())
@settings(max_examples=200, deadline=None)
def test_no_nan(payload):
    axis_w, concept_w, rel, votes = payload
    r = compute_aggregate(
        axis_weights=axis_w,
        concept_weights=concept_w,
        concept_relevant_axes=rel,
        votes=votes,
    )
    assert not math.isnan(r.aggregate)
    for score in r.per_concept_score.values():
        assert not math.isnan(score)
```

- [ ] **Step 2: Run to verify pass**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/test_aggregation_invariant.py -v
```

Expected: 3 passed (each runs 200 examples).

- [ ] **Step 3: Commit**

```bash
git add plugins/grading/python/tests/test_aggregation_invariant.py
git commit -m "test(grading-plugin): property-based invariants for aggregation"
```

---

## Task 14: Run resolution (--run prefix matching)

**Files:**
- Create: `plugins/grading/python/run_resolution.py`
- Create: `plugins/grading/python/tests/test_run_resolution.py`

Spec §2 "CLI run resolution".

- [ ] **Step 1: Write the failing test**

Create `plugins/grading/python/tests/test_run_resolution.py`:

```python
from pathlib import Path

import pytest

from plugins.grading.python.run_resolution import (
    AmbiguousRunPrefix,
    NoRunMatch,
    resolve_run,
    most_recent_run,
)


@pytest.fixture
def runs_dir(tmp_path):
    base = tmp_path / "runs"
    for name in [
        "2026-05-13_13-15-00Z__abc1",
        "2026-05-13_14-22-00Z__def6",
        "2026-05-14_09-22-31Z__beef",
    ]:
        (base / name).mkdir(parents=True)
    return base


def test_exact_match(runs_dir):
    r = resolve_run("2026-05-13_13-15-00Z__abc1", runs_dir)
    assert r.name == "2026-05-13_13-15-00Z__abc1"


def test_partial_match_unique(runs_dir):
    r = resolve_run("2026-05-13_13-15-00Z", runs_dir)
    assert r.name == "2026-05-13_13-15-00Z__abc1"


def test_partial_match_ambiguous(runs_dir):
    with pytest.raises(AmbiguousRunPrefix) as exc:
        resolve_run("2026-05-13", runs_dir)
    assert "abc1" in str(exc.value)
    assert "def6" in str(exc.value)


def test_no_match(runs_dir):
    with pytest.raises(NoRunMatch):
        resolve_run("1999-01-01", runs_dir)


def test_most_recent_run(runs_dir):
    r = most_recent_run(runs_dir)
    assert r.name == "2026-05-14_09-22-31Z__beef"


def test_most_recent_run_empty(tmp_path):
    (tmp_path / "runs").mkdir()
    with pytest.raises(NoRunMatch):
        most_recent_run(tmp_path / "runs")
```

- [ ] **Step 2: Run to confirm failure**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/test_run_resolution.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement run_resolution.py**

Create `plugins/grading/python/run_resolution.py`:

```python
"""--run <prefix> resolution per spec §2.

Resolution semantics:
- Exact match wins.
- Otherwise, prefix-match against directory names sorted descending.
- Exactly one match: return it.
- Zero matches: NoRunMatch.
- Two or more matches: AmbiguousRunPrefix with the candidate list.
"""

from __future__ import annotations

from pathlib import Path


class NoRunMatch(LookupError):
    pass


class AmbiguousRunPrefix(LookupError):
    def __init__(self, prefix: str, candidates: list[str]) -> None:
        self.prefix = prefix
        self.candidates = candidates
        super().__init__(
            f"prefix {prefix!r} matches {len(candidates)} runs: "
            + ", ".join(candidates)
        )


def _list_run_dirs(runs_dir: Path) -> list[Path]:
    if not runs_dir.is_dir():
        return []
    return sorted([p for p in runs_dir.iterdir() if p.is_dir()])


def resolve_run(prefix: str, runs_dir: Path) -> Path:
    candidates = _list_run_dirs(runs_dir)
    exact = [p for p in candidates if p.name == prefix]
    if exact:
        return exact[0]

    prefix_hits = [p for p in candidates if p.name.startswith(prefix)]
    if not prefix_hits:
        raise NoRunMatch(f"no run matched prefix {prefix!r} under {runs_dir}")
    if len(prefix_hits) > 1:
        raise AmbiguousRunPrefix(prefix, [p.name for p in prefix_hits])
    return prefix_hits[0]


def most_recent_run(runs_dir: Path) -> Path:
    candidates = _list_run_dirs(runs_dir)
    if not candidates:
        raise NoRunMatch(f"no runs in {runs_dir}")
    return candidates[-1]
```

- [ ] **Step 4: Run to verify pass**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/test_run_resolution.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/grading/python/run_resolution.py plugins/grading/python/tests/test_run_resolution.py
git commit -m "feat(grading-plugin): --run prefix resolution helper"
```

---

## Task 15: Source snapshot (src_snapshot.tar.gz)

**Files:**
- Create: `plugins/grading/python/snapshot.py`
- Create: `plugins/grading/python/tests/test_snapshot.py`

Spec §2 "Reproducibility — two independent paths" first item.

- [ ] **Step 1: Write the failing test**

Create `plugins/grading/python/tests/test_snapshot.py`:

```python
import tarfile
from pathlib import Path

from plugins.grading.python.snapshot import create_snapshot, EXCLUDED_TOP_LEVEL


def _build_fake_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname='x'\n")
    (repo / ".python-version").write_text("3.11\n")
    (repo / "plugins" / "grading" / "python").mkdir(parents=True)
    (repo / "plugins" / "grading" / "python" / "schema.py").write_text("x = 1\n")
    # Excluded top-level dirs:
    (repo / ".git" / "objects").mkdir(parents=True)
    (repo / ".git" / "objects" / "stuff").write_text("...")
    (repo / ".venv" / "bin").mkdir(parents=True)
    (repo / ".venv" / "bin" / "python").write_text("...")
    (repo / "runs" / "2026-05-13_00-00-00Z__test").mkdir(parents=True)
    (repo / "runs" / "2026-05-13_00-00-00Z__test" / "f").write_text("...")
    (repo / ".specstory" / "history").mkdir(parents=True)
    (repo / ".specstory" / "history" / "log.md").write_text("...")
    # Excluded nested __pycache__:
    (repo / "plugins" / "grading" / "python" / "__pycache__").mkdir()
    (repo / "plugins" / "grading" / "python" / "__pycache__" / "x.pyc").write_bytes(b"bytecode")
    return repo


def test_excluded_top_level_set():
    assert EXCLUDED_TOP_LEVEL == frozenset({".git", ".venv", ".specstory", "runs"})


def test_snapshot_contains_expected_files(tmp_path):
    repo = _build_fake_repo(tmp_path)
    out = tmp_path / "snapshot.tar.gz"
    create_snapshot(repo, out)
    assert out.is_file()
    with tarfile.open(out, "r:gz") as tf:
        names = set(tf.getnames())
    assert any(n.endswith("pyproject.toml") for n in names)
    assert any(n.endswith(".python-version") for n in names)
    assert any(n.endswith("plugins/grading/python/schema.py") for n in names)


def test_snapshot_excludes_top_level(tmp_path):
    repo = _build_fake_repo(tmp_path)
    out = tmp_path / "snapshot.tar.gz"
    create_snapshot(repo, out)
    with tarfile.open(out, "r:gz") as tf:
        names = tf.getnames()
    for ex in EXCLUDED_TOP_LEVEL:
        assert not any(f"/{ex}/" in n or n.endswith(f"/{ex}") for n in names), ex


def test_snapshot_excludes_pycache(tmp_path):
    repo = _build_fake_repo(tmp_path)
    out = tmp_path / "snapshot.tar.gz"
    create_snapshot(repo, out)
    with tarfile.open(out, "r:gz") as tf:
        names = tf.getnames()
    assert not any("__pycache__" in n for n in names)
```

- [ ] **Step 2: Run to confirm failure**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/test_snapshot.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement snapshot.py**

Create `plugins/grading/python/snapshot.py`:

```python
"""Source snapshot helper per spec §2.

Produces a `src_snapshot.tar.gz` of the working tree at run time, excluding
runtime/build artifacts. Reproduction:

    tar xzf src_snapshot.tar.gz -C /tmp/rerun
    cd /tmp/rerun && uv sync
"""

from __future__ import annotations

import tarfile
from pathlib import Path


EXCLUDED_TOP_LEVEL: frozenset[str] = frozenset({
    ".git", ".venv", ".specstory", "runs",
})

EXCLUDED_ANY: frozenset[str] = frozenset({"__pycache__"})


def _should_skip(member_relpath: Path) -> bool:
    parts = member_relpath.parts
    if not parts:
        return False
    if parts[0] in EXCLUDED_TOP_LEVEL:
        return True
    return any(p in EXCLUDED_ANY for p in parts)


def create_snapshot(repo_root: Path, output: Path) -> None:
    repo_root = repo_root.resolve()
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    def filter_fn(tarinfo: tarfile.TarInfo) -> tarfile.TarInfo | None:
        rel = Path(tarinfo.name)
        if rel.parts and rel.parts[0] == repo_root.name:
            rel = Path(*rel.parts[1:])
        if _should_skip(rel):
            return None
        return tarinfo

    with tarfile.open(output, "w:gz") as tf:
        tf.add(repo_root, arcname=repo_root.name, filter=filter_fn)
```

- [ ] **Step 4: Run to verify pass**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/test_snapshot.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/grading/python/snapshot.py plugins/grading/python/tests/test_snapshot.py
git commit -m "feat(grading-plugin): src_snapshot.tar.gz creation with exclusions"
```

---

## Task 16: PDF render (pymupdf)

**Files:**
- Create: `plugins/grading/python/pdf_render.py`
- Create: `plugins/grading/python/tests/test_pdf_render.py`
- Create: `plugins/grading/python/tests/fixtures/tiny.pdf` (generated by the test)

Spec §4.1 (Stage 0 PDF rendering).

- [ ] **Step 1: Write the failing test**

Create `plugins/grading/python/tests/test_pdf_render.py`:

```python
from pathlib import Path

import pymupdf
import pytest

from plugins.grading.python.pdf_render import render_pages, PageRenderResult


@pytest.fixture
def two_page_pdf(tmp_path):
    """Generate a tiny 2-page PDF via pymupdf so tests don't need a binary fixture."""
    doc = pymupdf.open()
    for i in range(2):
        page = doc.new_page(width=200, height=200)
        page.insert_text((20, 50), f"page {i + 1}")
    out = tmp_path / "tiny.pdf"
    doc.save(out)
    doc.close()
    return out


def test_render_pages_produces_one_png_per_page(tmp_path, two_page_pdf):
    out_dir = tmp_path / "figures"
    result = render_pages(two_page_pdf, out_dir)
    assert isinstance(result, PageRenderResult)
    assert result.page_count == 2
    assert (out_dir / "page_001.png").is_file()
    assert (out_dir / "page_002.png").is_file()
    assert result.figure_paths == [out_dir / "page_001.png", out_dir / "page_002.png"]


def test_render_pages_zero_pads_to_three_digits(tmp_path, two_page_pdf):
    out_dir = tmp_path / "figures"
    render_pages(two_page_pdf, out_dir)
    names = sorted(p.name for p in out_dir.iterdir())
    assert names == ["page_001.png", "page_002.png"]


def test_render_pages_makes_output_dir(tmp_path, two_page_pdf):
    out_dir = tmp_path / "deep" / "nested" / "figures"
    assert not out_dir.exists()
    render_pages(two_page_pdf, out_dir)
    assert out_dir.is_dir()
```

- [ ] **Step 2: Run to confirm failure**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/test_pdf_render.py -v
```

Expected: ImportError on `plugins.grading.python.pdf_render`.

- [ ] **Step 3: Implement pdf_render.py**

Create `plugins/grading/python/pdf_render.py`:

```python
"""PDF page rendering via pymupdf per spec §4.1.

One PNG per page, written to <out_dir>/page_NNN.png with 3-digit zero padding.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pymupdf


@dataclass(frozen=True)
class PageRenderResult:
    pdf_path: Path
    out_dir: Path
    page_count: int
    figure_paths: list[Path]


def render_pages(pdf_path: Path, out_dir: Path, *, dpi: int = 150) -> PageRenderResult:
    pdf_path = pdf_path.resolve()
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    paths: list[Path] = []
    with pymupdf.open(pdf_path) as doc:
        for i, page in enumerate(doc, start=1):
            pix = page.get_pixmap(dpi=dpi)
            target = out_dir / f"page_{i:03d}.png"
            pix.save(target)
            paths.append(target)

    return PageRenderResult(
        pdf_path=pdf_path,
        out_dir=out_dir,
        page_count=len(paths),
        figure_paths=paths,
    )
```

- [ ] **Step 4: Run to verify pass**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/test_pdf_render.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/grading/python/pdf_render.py plugins/grading/python/tests/test_pdf_render.py
git commit -m "feat(grading-plugin): pymupdf-based page rendering for Stage 0"
```

---

## Task 17: Semantic diff between two run folders

**Files:**
- Create: `plugins/grading/python/diff.py`
- Create: `plugins/grading/python/tests/test_diff.py`

Spec §2 "Comparison tooling".

- [ ] **Step 1: Write the failing test**

Create `plugins/grading/python/tests/test_diff.py`:

```python
from pathlib import Path

import yaml

from plugins.grading.python.diff import (
    diff_runs,
    RunDiff,
    RubricDiff,
    GradesDiff,
)


def _write_universal(path: Path, weights: dict[str, float]):
    path.parent.mkdir(parents=True, exist_ok=True)
    axes = [
        {
            "name": name,
            "description": "",
            "weight": w,
            "score_levels": {
                "full":    {"value": 1.0, "criterion": "x"},
                "partial": {"value": 0.5, "criterion": "x"},
                "none":    {"value": 0.0, "criterion": "x"},
            },
        }
        for name, w in weights.items()
    ]
    yaml.safe_dump(
        {
            "type": "MECHANISM",
            "status": "frozen",
            "axes": axes,
            "aggregate": {"method": "weighted_mean", "out_of": 10.0},
        },
        path.open("w"),
    )


def _write_grades(path: Path, aggregates: dict[str, float]):
    path.parent.mkdir(parents=True, exist_ok=True)
    grades = [
        {
            "answer_id": aid,
            "per_concept": {"c1": {"a": "full"}},
            "aggregate": agg,
            "aggregate_x10": agg * 10,
        }
        for aid, agg in aggregates.items()
    ]
    yaml.safe_dump(
        {
            "question_id": "Q",
            "rubric_ref": "rubrics/c/Q/rubric.yaml",
            "universal_rubric_ref": "types/MECHANISM/universal_rubric.yaml",
            "grades": grades,
            "summary": {
                "mean_by_quality": {"good": 1.0, "less_good": 0.5, "wrong": 0.0},
                "ordering_preserved": True,
                "bands_satisfied": True,
                "axis_discrimination_passed": True,
            },
        },
        path.open("w"),
    )


def test_diff_identical_runs(tmp_path):
    for label in ("a", "b"):
        root = tmp_path / label
        _write_universal(root / "types" / "MECHANISM" / "universal_rubric.yaml", {"a": 0.5, "b": 0.5})
        _write_grades(root / "grades" / "c" / "Q" / "grades.yaml", {"good_1": 1.0})
    d = diff_runs(tmp_path / "a", tmp_path / "b")
    assert isinstance(d, RunDiff)
    assert d.is_identical()


def test_diff_axis_weight_change(tmp_path):
    _write_universal(tmp_path / "a" / "types" / "MECHANISM" / "universal_rubric.yaml", {"a": 0.5, "b": 0.5})
    _write_universal(tmp_path / "b" / "types" / "MECHANISM" / "universal_rubric.yaml", {"a": 0.7, "b": 0.3})
    d = diff_runs(tmp_path / "a", tmp_path / "b")
    rubric_diff = d.universal_rubrics["MECHANISM"]
    assert isinstance(rubric_diff, RubricDiff)
    assert rubric_diff.weight_deltas == {"a": 0.2, "b": -0.2}


def test_diff_grade_score_change(tmp_path):
    _write_universal(tmp_path / "a" / "types" / "MECHANISM" / "universal_rubric.yaml", {"a": 1.0})
    _write_universal(tmp_path / "b" / "types" / "MECHANISM" / "universal_rubric.yaml", {"a": 1.0})
    _write_grades(tmp_path / "a" / "grades" / "c" / "Q" / "grades.yaml", {"good_1": 1.0, "less_good_1": 0.5})
    _write_grades(tmp_path / "b" / "grades" / "c" / "Q" / "grades.yaml", {"good_1": 0.9, "less_good_1": 0.5})
    d = diff_runs(tmp_path / "a", tmp_path / "b")
    gd = d.grades["c/Q"]
    assert isinstance(gd, GradesDiff)
    assert gd.aggregate_deltas == {"good_1": -0.1, "less_good_1": 0.0}
```

- [ ] **Step 2: Run to confirm failure**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/test_diff.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement diff.py**

Create `plugins/grading/python/diff.py`:

```python
"""Semantic diff between two run folders per spec §2.

Compares like artifacts (universal rubrics, per-question rubrics, grades, …)
and returns a structured RunDiff. Stage-level coverage in this initial
implementation: universal rubrics, per-question rubrics, grades. Other
artifact types (sources, seed questions, synthetic answers) raise NotImplementedError
for now; they get added as the per-stage plans need them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class RubricDiff:
    type_name: str
    weight_deltas: dict[str, float]            # axis_name -> delta
    axes_added: list[str] = field(default_factory=list)
    axes_removed: list[str] = field(default_factory=list)
    status_changed: tuple[str, str] | None = None

    def is_identical(self) -> bool:
        return (
            not self.weight_deltas
            and not self.axes_added
            and not self.axes_removed
            and self.status_changed is None
        )


@dataclass(frozen=True)
class GradesDiff:
    question_path: str
    aggregate_deltas: dict[str, float]         # answer_id -> delta

    def is_identical(self) -> bool:
        return all(d == 0.0 for d in self.aggregate_deltas.values())


@dataclass(frozen=True)
class RunDiff:
    run_a: Path
    run_b: Path
    universal_rubrics: dict[str, RubricDiff]
    grades: dict[str, GradesDiff]

    def is_identical(self) -> bool:
        return (
            all(r.is_identical() for r in self.universal_rubrics.values())
            and all(g.is_identical() for g in self.grades.values())
        )


def _load_yaml(path: Path) -> dict | None:
    if not path.is_file():
        return None
    return yaml.safe_load(path.read_text())


def _diff_universal(a: dict, b: dict, type_name: str) -> RubricDiff:
    axes_a = {x["name"]: x for x in a["axes"]}
    axes_b = {x["name"]: x for x in b["axes"]}
    added = sorted(set(axes_b) - set(axes_a))
    removed = sorted(set(axes_a) - set(axes_b))
    weight_deltas: dict[str, float] = {}
    for name in set(axes_a) | set(axes_b):
        wa = axes_a.get(name, {}).get("weight", 0.0)
        wb = axes_b.get(name, {}).get("weight", 0.0)
        delta = round(wb - wa, 9)
        if delta != 0.0 or name in added or name in removed:
            weight_deltas[name] = delta
    status_changed = None
    if a.get("status") != b.get("status"):
        status_changed = (a.get("status"), b.get("status"))
    return RubricDiff(
        type_name=type_name,
        weight_deltas=weight_deltas,
        axes_added=added,
        axes_removed=removed,
        status_changed=status_changed,
    )


def _diff_grades(a: dict, b: dict, qpath: str) -> GradesDiff:
    by_a = {g["answer_id"]: g["aggregate"] for g in a["grades"]}
    by_b = {g["answer_id"]: g["aggregate"] for g in b["grades"]}
    deltas: dict[str, float] = {}
    for aid in set(by_a) | set(by_b):
        deltas[aid] = round(by_b.get(aid, 0.0) - by_a.get(aid, 0.0), 9)
    return GradesDiff(question_path=qpath, aggregate_deltas=deltas)


def diff_runs(run_a: Path, run_b: Path) -> RunDiff:
    universal_rubrics: dict[str, RubricDiff] = {}
    types_a = run_a / "types"
    types_b = run_b / "types"
    type_dirs = set()
    for base in (types_a, types_b):
        if base.is_dir():
            type_dirs.update(p.name for p in base.iterdir() if p.is_dir())
    for t in sorted(type_dirs):
        a = _load_yaml(types_a / t / "universal_rubric.yaml") or {"axes": [], "status": None}
        b = _load_yaml(types_b / t / "universal_rubric.yaml") or {"axes": [], "status": None}
        universal_rubrics[t] = _diff_universal(a, b, t)

    grades: dict[str, GradesDiff] = {}
    grades_a = run_a / "grades"
    grades_b = run_b / "grades"
    seen_qs: set[str] = set()
    for base in (grades_a, grades_b):
        if base.is_dir():
            for course_dir in base.iterdir():
                if not course_dir.is_dir():
                    continue
                for q_dir in course_dir.iterdir():
                    if (q_dir / "grades.yaml").is_file():
                        seen_qs.add(f"{course_dir.name}/{q_dir.name}")
    for qpath in sorted(seen_qs):
        course, q = qpath.split("/", 1)
        a = _load_yaml(grades_a / course / q / "grades.yaml") or {"grades": []}
        b = _load_yaml(grades_b / course / q / "grades.yaml") or {"grades": []}
        grades[qpath] = _diff_grades(a, b, qpath)

    return RunDiff(
        run_a=run_a, run_b=run_b,
        universal_rubrics=universal_rubrics, grades=grades,
    )
```

- [ ] **Step 4: Run to verify pass**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/test_diff.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/grading/python/diff.py plugins/grading/python/tests/test_diff.py
git commit -m "feat(grading-plugin): semantic diff between run folders (universal rubrics + grades)"
```

---

## Task 18: Subagent output contract schemas

**Files:**
- Create: `plugins/grading/python/contracts.py`
- Create: `plugins/grading/python/tests/contracts/test_judge_output_schema.py`
- Create: `plugins/grading/python/tests/contracts/test_critic_output_schema.py`
- Create: `plugins/grading/python/tests/contracts/test_materialize_seed_output_schema.py`
- Create: `plugins/grading/python/tests/contracts/test_seed_gen_output_schema.py`

Spec §6.2.

- [ ] **Step 1: Write the failing tests (all four contract tests at once)**

Create `plugins/grading/python/tests/contracts/test_judge_output_schema.py`:

```python
import pytest

from plugins.grading.python.contracts import JudgeOutput, JudgeRow


def test_judge_output_accepts_well_formed():
    raw = {
        "rows": [
            {
                "answer_id": "good_1", "concept_id": "c1", "axis": "causal",
                "level": "full", "rationale": "explicit causes.",
            },
        ]
    }
    out = JudgeOutput.model_validate(raw)
    assert out.rows[0].level == "full"


def test_judge_output_rejects_bad_level():
    raw = {"rows": [
        {"answer_id": "a", "concept_id": "c", "axis": "x",
         "level": "MAYBE", "rationale": "..."}
    ]}
    with pytest.raises(Exception):
        JudgeOutput.model_validate(raw)


def test_judge_output_rejects_missing_rationale():
    raw = {"rows": [
        {"answer_id": "a", "concept_id": "c", "axis": "x", "level": "full"}
    ]}
    with pytest.raises(Exception):
        JudgeOutput.model_validate(raw)
```

Create `plugins/grading/python/tests/contracts/test_critic_output_schema.py`:

```python
import pytest

from plugins.grading.python.contracts import CriticOutput


def test_critic_output_accepts_weight_revision():
    raw = {
        "revisions": [
            {"kind": "weight", "axis": "causal", "new_weight": 0.4, "rationale": "..."},
        ],
        "rationale_summary": "...",
    }
    out = CriticOutput.model_validate(raw)
    assert out.revisions[0].kind == "weight"


def test_critic_output_accepts_criterion_revision():
    raw = {
        "revisions": [
            {"kind": "criterion", "axis": "causal", "level": "partial",
             "new_criterion": "...", "rationale": "..."},
        ],
        "rationale_summary": "...",
    }
    CriticOutput.model_validate(raw)


def test_critic_output_rejects_unknown_kind():
    raw = {"revisions": [{"kind": "purple", "rationale": "..."}], "rationale_summary": "x"}
    with pytest.raises(Exception):
        CriticOutput.model_validate(raw)
```

Create `plugins/grading/python/tests/contracts/test_materialize_seed_output_schema.py`:

```python
import pytest

from plugins.grading.python.contracts import MaterializeSeedOutput


def _good():
    return {
        "seed_id": "MECHANISM_001",
        "concept_overlay": [
            {"id": "c1", "text": "...", "weight": 0.6, "relevant_axes": ["a"]},
            {"id": "c2", "text": "...", "weight": 0.4, "relevant_axes": ["a"]},
        ],
        "answers": [
            {"answer_id": "good_1", "quality": "good", "text": "..."},
            {"answer_id": "ap_a", "quality": "axis_perturbation",
             "text": "...", "target_axis": "a"},
        ],
        "gold_coverage": {
            "good_1": {"c1": {"a": "full"}, "c2": {"a": "full"}},
            "ap_a":   {"c1": {"a": "partial"}, "c2": {"a": "partial"}},
        },
    }


def test_materialize_seed_accepts_good():
    MaterializeSeedOutput.model_validate(_good())


def test_materialize_seed_rejects_axis_perturbation_without_target():
    raw = _good()
    raw["answers"][1]["target_axis"] = None
    with pytest.raises(Exception):
        MaterializeSeedOutput.model_validate(raw)
```

Create `plugins/grading/python/tests/contracts/test_seed_gen_output_schema.py`:

```python
import pytest

from plugins.grading.python.contracts import SeedGenOutput


def test_seed_gen_accepts_good():
    raw = {
        "seeds": [
            {"topic": "physics", "text": "How does evaporation cool a liquid?", "rationale": "..."},
        ]
    }
    SeedGenOutput.model_validate(raw)


def test_seed_gen_rejects_missing_topic():
    raw = {"seeds": [{"text": "...", "rationale": "..."}]}
    with pytest.raises(Exception):
        SeedGenOutput.model_validate(raw)
```

- [ ] **Step 2: Run to confirm failures**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/contracts/ -v
```

Expected: ImportErrors on `plugins.grading.python.contracts`.

- [ ] **Step 3: Implement contracts.py**

Create `plugins/grading/python/contracts.py`:

```python
"""Subagent output schemas per spec §6.2.

These models validate the *shape* of structured JSON returned by subagent
roles. They do not call any LLM; they are exercised against fixture JSON
by the contract tests.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from plugins.grading.python.schema import (
    AnswerQuality,
    ConceptOverlayEntry,
    Level,
)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class JudgeRow(_Strict):
    answer_id: str = Field(min_length=1)
    concept_id: str = Field(min_length=1)
    axis: str = Field(min_length=1)
    level: Level
    rationale: str = Field(min_length=1)


class JudgeOutput(_Strict):
    rows: list[JudgeRow] = Field(min_length=1)


class CriticRevisionKind(str, Enum):
    WEIGHT = "weight"
    CRITERION = "criterion"


class CriticWeightRevision(_Strict):
    kind: Literal[CriticRevisionKind.WEIGHT] = CriticRevisionKind.WEIGHT
    axis: str = Field(min_length=1)
    new_weight: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(min_length=1)


class CriticCriterionRevision(_Strict):
    kind: Literal[CriticRevisionKind.CRITERION] = CriticRevisionKind.CRITERION
    axis: str = Field(min_length=1)
    level: Level
    new_criterion: str = Field(min_length=1)
    rationale: str = Field(min_length=1)


CriticRevision = CriticWeightRevision | CriticCriterionRevision


class CriticOutput(_Strict):
    revisions: list[CriticRevision] = Field(min_length=1)
    rationale_summary: str = Field(min_length=1)


class MaterializeSeedAnswer(_Strict):
    answer_id: str = Field(min_length=1)
    quality: AnswerQuality
    text: str = Field(min_length=1)
    target_axis: str | None = None


class MaterializeSeedOutput(_Strict):
    seed_id: str = Field(min_length=1)
    concept_overlay: list[ConceptOverlayEntry] = Field(min_length=1)
    answers: list[MaterializeSeedAnswer] = Field(min_length=1)
    gold_coverage: dict[str, dict[str, dict[str, Level]]]

    def model_post_init(self, _ctx) -> None:
        # Axis-perturbation answers must declare target_axis; others must not.
        for a in self.answers:
            if a.quality is AnswerQuality.AXIS_PERTURBATION and not a.target_axis:
                raise ValueError(
                    f"answer {a.answer_id!r}: axis_perturbation requires target_axis"
                )
            if a.quality is not AnswerQuality.AXIS_PERTURBATION and a.target_axis:
                raise ValueError(
                    f"answer {a.answer_id!r}: non-perturbation must not set target_axis"
                )


class SeedGenSeed(_Strict):
    topic: str = Field(min_length=1)
    text: str = Field(min_length=1)
    rationale: str = Field(min_length=1)


class SeedGenOutput(_Strict):
    seeds: list[SeedGenSeed] = Field(min_length=1)
```

- [ ] **Step 4: Run to verify pass**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/contracts/ -v
```

Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add plugins/grading/python/contracts.py plugins/grading/python/tests/contracts/
git commit -m "feat(grading-plugin): subagent output contract schemas (judge/critic/materialize_seed/seed_gen)"
```

---

## Task 19: validate_run.py CLI + smoke fixture

**Files:**
- Create: `plugins/grading/python/validate_run.py`
- Create: `plugins/grading/python/tests/fixtures/run_smoke/...` (hand-crafted minimal run folder)
- Create: `plugins/grading/python/tests/test_validate_run.py`
- Create: `plugins/grading/python/tests/test_smoke_fixture.py`

Spec §6.3 (fixture smoke) + §6.5 (validate-run CLI).

- [ ] **Step 1: Hand-craft the fixture run folder**

Create the following files under `plugins/grading/python/tests/fixtures/run_smoke/`:

`inputs/type_catalog.yaml`:
```yaml
types:
  - name: MECHANISM
    description: How a process unfolds.
    candidate_axes: [causal_chain_correctness, completeness]
```

`inputs/questions/fixture/Qfix01.yaml`:
```yaml
question_id: Qfix01
course: fixture
type: MECHANISM
text: Describe how X causes Y.
sources: [fixture_source]
```

`sources/fixture_source/content.md`:
```markdown
# Fixture source

X causes Y by mechanism M.
```

`sources/fixture_source/meta.yaml`:
```yaml
format: markdown
courses: [fixture]
topics: [fixture]
extraction: null
content_sha: 0000000000000000000000000000000000000000000000000000000000000000
figure_count: 0
page_count: 0
```

`types/MECHANISM/universal_rubric.yaml`:
```yaml
type: MECHANISM
status: frozen
axes:
  - name: causal_chain_correctness
    description: Are causes correctly linked to effects?
    weight: 0.6
    score_levels:
      full:    { value: 1.0, criterion: "All correct." }
      partial: { value: 0.5, criterion: "Some correct." }
      none:    { value: 0.0, criterion: "Incorrect." }
  - name: completeness
    description: Coverage of the mechanism.
    weight: 0.4
    score_levels:
      full:    { value: 1.0, criterion: "All present." }
      partial: { value: 0.5, criterion: "Some present." }
      none:    { value: 0.0, criterion: "Missing." }
aggregate:
  method: weighted_mean
  out_of: 10.0
```

`types/MECHANISM/calibration_meta.yaml`:
```yaml
type: MECHANISM
seed_ids_train: [seed_001]
seed_ids_val: [seed_002]
seed_ids_test: [seed_003]
iterations: []
final_criterion_outcomes:
  concept_vote_agreement: 0.95
  score_band_satisfaction: 1.0
  axis_discrimination_delta: 0.5
limitation_notes: fixture
```

`rubrics/fixture/Qfix01/rubric.yaml`:
```yaml
question_id: Qfix01
course: fixture
type: MECHANISM
universal_rubric_ref: types/MECHANISM/universal_rubric.yaml
concept_overlay:
  - id: c1
    text: X causes Y.
    weight: 1.0
    relevant_axes: [causal_chain_correctness, completeness]
status: frozen
```

`synthetic_answers/fixture/Qfix01/answers.yaml`:
```yaml
question_id: Qfix01
answers:
  - { answer_id: good_1,      quality: good,      text: "X causes Y via mechanism M." }
  - { answer_id: less_good_1, quality: less_good, text: "X causes Y." }
  - { answer_id: wrong_1,     quality: wrong,     text: "Y causes X." }
```

`synthetic_answers/fixture/Qfix01/gold_concept_coverage.yaml`:
```yaml
question_id: Qfix01
coverage:
  good_1:      { c1: { causal_chain_correctness: full,    completeness: full } }
  less_good_1: { c1: { causal_chain_correctness: full,    completeness: partial } }
  wrong_1:     { c1: { causal_chain_correctness: none,    completeness: none } }
target_axis_weakness: {}
```

`grades/fixture/Qfix01/grades.yaml`:
```yaml
question_id: Qfix01
rubric_ref: rubrics/fixture/Qfix01/rubric.yaml
universal_rubric_ref: types/MECHANISM/universal_rubric.yaml
grades:
  - answer_id: good_1
    per_concept: { c1: { causal_chain_correctness: full, completeness: full } }
    aggregate: 1.0
    aggregate_x10: 10.0
  - answer_id: less_good_1
    per_concept: { c1: { causal_chain_correctness: full, completeness: partial } }
    aggregate: 0.8
    aggregate_x10: 8.0
  - answer_id: wrong_1
    per_concept: { c1: { causal_chain_correctness: none, completeness: none } }
    aggregate: 0.0
    aggregate_x10: 0.0
summary:
  mean_by_quality: { good: 1.0, less_good: 0.8, wrong: 0.0 }
  ordering_preserved: true
  bands_satisfied: true
  axis_discrimination_passed: true
```

`run_meta.yaml`:
```yaml
run_id: 2026-05-13_00-00-00Z__smok
started_at: "2026-05-13T00:00:00Z"
ended_at: "2026-05-13T00:01:00Z"
git_sha: 0000000000000000000000000000000000000000
git_dirty: false
status: success
stages_run: [calibrate_types, generate_rubric, gold_grade]
```

`config.yaml` — paste the contents of `plugins/grading/config/pipeline.yaml` verbatim into here (the run records the config it used).

`REPRODUCE.md`:
```markdown
# Reproduction commands

This is a hand-crafted fixture run; not produced by an actual pipeline invocation.
```

`traces/calibrate_types/trace_summary.yaml`:
```yaml
stage: calibrate_types
total_subagents: 0
counts_by_role: {}
counts_by_status: {}
duration_ms: 0
```

`traces/calibrate_types/timeline.jsonl`:
```json
{"ts":"2026-05-13T00:00:00.000Z","event_type":"stage","actor":"main_agent","name":"calibrate_types:MECHANISM","phase":"start","details":{}}
{"ts":"2026-05-13T00:00:01.000Z","event_type":"stage","actor":"main_agent","name":"calibrate_types:MECHANISM","phase":"end","details":{}}
```

- [ ] **Step 2: Write the smoke fixture test**

Create `plugins/grading/python/tests/test_smoke_fixture.py`:

```python
import json
from pathlib import Path

import yaml

from plugins.grading.python.schema import (
    validate_universal_rubric,
    validate_per_question_rubric,
    validate_grade,
)

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "run_smoke"


def test_fixture_layout_present():
    for rel in [
        "inputs/type_catalog.yaml",
        "inputs/questions/fixture/Qfix01.yaml",
        "sources/fixture_source/content.md",
        "sources/fixture_source/meta.yaml",
        "types/MECHANISM/universal_rubric.yaml",
        "types/MECHANISM/calibration_meta.yaml",
        "rubrics/fixture/Qfix01/rubric.yaml",
        "synthetic_answers/fixture/Qfix01/answers.yaml",
        "synthetic_answers/fixture/Qfix01/gold_concept_coverage.yaml",
        "grades/fixture/Qfix01/grades.yaml",
        "run_meta.yaml",
        "config.yaml",
        "REPRODUCE.md",
        "traces/calibrate_types/trace_summary.yaml",
        "traces/calibrate_types/timeline.jsonl",
    ]:
        assert (FIXTURE / rel).is_file(), rel


def test_fixture_universal_rubric_validates():
    raw = yaml.safe_load((FIXTURE / "types/MECHANISM/universal_rubric.yaml").read_text())
    validate_universal_rubric(raw)


def test_fixture_per_question_rubric_validates():
    universal = validate_universal_rubric(
        yaml.safe_load((FIXTURE / "types/MECHANISM/universal_rubric.yaml").read_text())
    )
    pqr_raw = yaml.safe_load((FIXTURE / "rubrics/fixture/Qfix01/rubric.yaml").read_text())
    validate_per_question_rubric(pqr_raw, universal=universal)


def test_fixture_grades_validate():
    universal = validate_universal_rubric(
        yaml.safe_load((FIXTURE / "types/MECHANISM/universal_rubric.yaml").read_text())
    )
    pqr = validate_per_question_rubric(
        yaml.safe_load((FIXTURE / "rubrics/fixture/Qfix01/rubric.yaml").read_text()),
        universal=universal,
    )
    grades_raw = yaml.safe_load((FIXTURE / "grades/fixture/Qfix01/grades.yaml").read_text())
    validate_grade(grades_raw, rubric=pqr, universal=universal)


def test_fixture_timeline_well_formed():
    p = FIXTURE / "traces/calibrate_types/timeline.jsonl"
    lines = [ln for ln in p.read_text().splitlines() if ln.strip()]
    starts = ends = 0
    names_start: set[str] = set()
    names_end: set[str] = set()
    for ln in lines:
        ev = json.loads(ln)
        assert {"ts", "event_type", "actor", "name", "phase"} <= set(ev.keys())
        if ev["phase"] == "start":
            starts += 1
            names_start.add(ev["name"])
        else:
            ends += 1
            names_end.add(ev["name"])
    assert starts == ends and names_start == names_end
```

- [ ] **Step 3: Run smoke test (should already pass — uses helpers already implemented)**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/test_smoke_fixture.py -v
```

Expected: 5 passed.

- [ ] **Step 4: Write the validate_run CLI test**

Create `plugins/grading/python/tests/test_validate_run.py`:

```python
from pathlib import Path

from plugins.grading.python.validate_run import validate_run_folder, RunValidationReport


FIXTURE = Path(__file__).resolve().parent / "fixtures" / "run_smoke"


def test_validate_run_folder_passes_on_fixture():
    report = validate_run_folder(FIXTURE)
    assert isinstance(report, RunValidationReport)
    assert report.ok, report.errors


def test_validate_run_folder_reports_missing_universal_rubric(tmp_path):
    # Build a partial-fixture run missing the universal rubric.
    bad = tmp_path / "bad_run"
    (bad / "rubrics" / "fixture" / "Qfix01").mkdir(parents=True)
    (bad / "rubrics" / "fixture" / "Qfix01" / "rubric.yaml").write_text(
        (FIXTURE / "rubrics" / "fixture" / "Qfix01" / "rubric.yaml").read_text()
    )
    report = validate_run_folder(bad)
    assert not report.ok
    assert any("universal_rubric.yaml" in e for e in report.errors)
```

- [ ] **Step 5: Run to confirm failure**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/test_validate_run.py -v
```

Expected: ImportError.

- [ ] **Step 6: Implement validate_run.py**

Create `plugins/grading/python/validate_run.py`:

```python
"""CLI + library entrypoint: validate every artifact in a run folder.

Usage:

    python -m plugins.grading.python.validate_run --run-dir <path>
    python -m plugins.grading.python.validate_run --runs-root preprocessing/runs --run 2026-05-13
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from plugins.grading.python.run_resolution import (
    most_recent_run,
    resolve_run,
)
from plugins.grading.python.schema import (
    validate_universal_rubric,
    validate_per_question_rubric,
    validate_grade,
    UniversalRubric,
)


@dataclass
class RunValidationReport:
    run_dir: Path
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _load_yaml_or_record(path: Path, errors: list[str]) -> dict | None:
    if not path.is_file():
        errors.append(f"missing file: {path}")
        return None
    try:
        return yaml.safe_load(path.read_text())
    except Exception as exc:
        errors.append(f"YAML parse error in {path}: {exc}")
        return None


def _validate_universal_rubrics(run_dir: Path, errors: list[str]) -> dict[str, UniversalRubric]:
    out: dict[str, UniversalRubric] = {}
    types_dir = run_dir / "types"
    if not types_dir.is_dir():
        return out
    for type_dir in sorted(types_dir.iterdir()):
        rub_path = type_dir / "universal_rubric.yaml"
        raw = _load_yaml_or_record(rub_path, errors)
        if raw is None:
            continue
        try:
            out[type_dir.name] = validate_universal_rubric(raw)
        except Exception as exc:
            errors.append(f"invalid universal_rubric.yaml for {type_dir.name}: {exc}")
    return out


def _validate_per_question_rubrics_and_grades(
    run_dir: Path,
    universals: dict[str, UniversalRubric],
    errors: list[str],
) -> None:
    rub_root = run_dir / "rubrics"
    grades_root = run_dir / "grades"
    if not rub_root.is_dir():
        return
    for course_dir in sorted(rub_root.iterdir()):
        for q_dir in sorted(course_dir.iterdir()):
            rub_path = q_dir / "rubric.yaml"
            raw = _load_yaml_or_record(rub_path, errors)
            if raw is None:
                continue
            type_name = raw.get("type")
            universal = universals.get(type_name)
            if universal is None:
                errors.append(f"{rub_path}: references unknown type {type_name!r}")
                continue
            try:
                pqr = validate_per_question_rubric(raw, universal=universal)
            except Exception as exc:
                errors.append(f"invalid {rub_path}: {exc}")
                continue
            grades_path = grades_root / course_dir.name / q_dir.name / "grades.yaml"
            graw = _load_yaml_or_record(grades_path, errors)
            if graw is None:
                continue
            try:
                validate_grade(graw, rubric=pqr, universal=universal)
            except Exception as exc:
                errors.append(f"invalid {grades_path}: {exc}")


def validate_run_folder(run_dir: Path) -> RunValidationReport:
    report = RunValidationReport(run_dir=run_dir)
    universals = _validate_universal_rubrics(run_dir, report.errors)
    if not universals:
        report.errors.append(f"no universal rubrics found under {run_dir}/types/")
    _validate_per_question_rubrics_and_grades(run_dir, universals, report.errors)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="validate_run")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--run-dir", type=Path, help="absolute path to a single run folder")
    g.add_argument("--runs-root", type=Path, help="parent of runs/ ; pair with --run or default to most recent")
    parser.add_argument("--run", type=str, default=None, help="prefix to resolve under runs-root")
    args = parser.parse_args(argv)

    if args.run_dir is not None:
        run_dir = args.run_dir
    else:
        run_dir = resolve_run(args.run, args.runs_root) if args.run else most_recent_run(args.runs_root)

    report = validate_run_folder(run_dir)
    if report.ok:
        print(f"OK: {run_dir}")
        return 0
    print(f"FAIL: {run_dir}")
    for e in report.errors:
        print(f"  - {e}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 7: Run all new tests**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/test_validate_run.py plugins/grading/python/tests/test_smoke_fixture.py -v
```

Expected: 7 passed.

- [ ] **Step 8: Commit**

```bash
git add plugins/grading/python/validate_run.py plugins/grading/python/tests/test_validate_run.py plugins/grading/python/tests/test_smoke_fixture.py plugins/grading/python/tests/fixtures/run_smoke/
git commit -m "feat(grading-plugin): validate_run CLI + hand-crafted smoke fixture run folder"
```

---

## Task 20: Skill stubs (8 SKILL.md files)

**Files:**
- Create: `plugins/grading/skills/translate-sources/SKILL.md`
- Create: `plugins/grading/skills/prepare-seed-questions/SKILL.md`
- Create: `plugins/grading/skills/review-seeds/SKILL.md`
- Create: `plugins/grading/skills/calibrate-types/SKILL.md`
- Create: `plugins/grading/skills/test-universal/SKILL.md`
- Create: `plugins/grading/skills/generate-rubric/SKILL.md`
- Create: `plugins/grading/skills/gold-grade/SKILL.md`
- Create: `plugins/grading/skills/run-course/SKILL.md`
- Create: `plugins/grading/python/tests/test_skill_stubs.py`

Each skill is a directory with `SKILL.md`. The body is a stub: it states purpose, points at the spec section, and explicitly notes that orchestration is deferred to a per-stage plan.

- [ ] **Step 1: Write the failing test**

Create `plugins/grading/python/tests/test_skill_stubs.py`:

```python
import re
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = PLUGIN_ROOT / "skills"

EXPECTED_SKILLS = {
    "translate-sources",
    "prepare-seed-questions",
    "review-seeds",
    "calibrate-types",
    "test-universal",
    "generate-rubric",
    "gold-grade",
    "run-course",
}

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


def _frontmatter(text: str) -> dict[str, str]:
    m = FRONTMATTER_RE.match(text)
    assert m, "missing frontmatter"
    out: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def test_all_skill_dirs_present():
    actual = {p.name for p in SKILLS_DIR.iterdir() if p.is_dir()}
    assert actual == EXPECTED_SKILLS


def test_every_skill_has_SKILL_md():
    for name in EXPECTED_SKILLS:
        path = SKILLS_DIR / name / "SKILL.md"
        assert path.is_file(), name


def test_frontmatter_name_matches_dir():
    for name in EXPECTED_SKILLS:
        path = SKILLS_DIR / name / "SKILL.md"
        fm = _frontmatter(path.read_text())
        assert fm.get("name") == name, f"{name}: frontmatter name = {fm.get('name')!r}"


def test_frontmatter_has_description():
    for name in EXPECTED_SKILLS:
        path = SKILLS_DIR / name / "SKILL.md"
        fm = _frontmatter(path.read_text())
        assert fm.get("description"), name


def test_body_marks_stub_status():
    for name in EXPECTED_SKILLS:
        path = SKILLS_DIR / name / "SKILL.md"
        text = path.read_text()
        assert "Status: stub" in text, name
```

- [ ] **Step 2: Run to confirm failure**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/test_skill_stubs.py -v
```

Expected: collection-time or test-time failure (no skill dirs).

- [ ] **Step 3: Create the eight skill stubs**

For each skill, create `plugins/grading/skills/<name>/SKILL.md` with this template (filled in per skill):

`plugins/grading/skills/translate-sources/SKILL.md`:
```markdown
---
name: translate-sources
description: Stage 0 procedure — convert a PDF or markdown source into canonical content.md + figures + meta.yaml under the active run folder.
---

# translate-sources (Stage 0)

**Status: stub.** Full orchestration deferred to the per-stage plan for Stage 0.

## Spec reference

`docs/superpowers/specs/2026-05-13-grading-plugin-design.md` §4.1.

## Inputs read

- `inputs/sources_raw/<source>/<original>.{pdf,md}` in the active run folder
- `plugins/grading/config/pipeline.yaml` (`pdf_translator` knobs)
- `plugins/grading/config/tier_dispatch.yaml`

## Outputs written

- `sources/<source>/content.md`
- `sources/<source>/figures/page_NNN.png` (PDFs only)
- `sources/<source>/meta.yaml`
- `traces/translate_sources/<subagent_id>.json` per dispatched subagent
- `traces/translate_sources/timeline.jsonl` append-only

## Algorithm summary (implementation deferred)

1. Resolve active run folder via `python -m plugins.grading.python.run_resolution`.
2. For each source under `inputs/sources_raw/`:
   - If PDF: invoke `plugins/grading/python/pdf_render.py:render_pages` to emit `page_NNN.png`, then dispatch one `role: pdf_translator` subagent to produce `content.md`. Write `meta.yaml`.
   - If markdown: passthrough to `content.md`; write `meta.yaml`.
3. Emit a `python_helper_call` and `subagent_dispatch` timeline event around each operation.
4. Halt the stage if any artifact fails validation; surface to the user.

## Failure modes

- PDF render error → stage halts; trace records `error` event with the offending file path.
- pdf_translator subagent returns malformed markdown → one redispatch, then hard fail.
```

`plugins/grading/skills/prepare-seed-questions/SKILL.md`:
```markdown
---
name: prepare-seed-questions
description: Stage 1 procedure — build the cross-topic seed-question pool per type (curated + source-derived + Claude-knowledge).
---

# prepare-seed-questions (Stage 1)

**Status: stub.** Full orchestration deferred to the per-stage plan for Stage 1.

## Spec reference

`docs/superpowers/specs/2026-05-13-grading-plugin-design.md` §4.2.

## Inputs read

- `inputs/seed_questions_curated/<type>/*.yaml`
- `inputs/type_catalog.yaml`
- `sources/<source>/content.md` (for source-derived generation)
- `config/pipeline.yaml` (`seeds_per_type` composition + thresholds)

## Outputs written

- `seed_questions/<type>/<seed_id>.yaml` (one file per seed, normalized)
- `traces/prepare_seed_questions/<subagent_id>.json` + `timeline.jsonl`

## Algorithm summary (implementation deferred)

1. For each type in `inputs/type_catalog.yaml`:
   - Load curated seeds verbatim.
   - Dispatch one `role: seed_gen` subagent for the Claude-knowledge share.
   - Dispatch one `role: seed_gen` subagent per relevant translated source for the source-derived share.
   - Optionally dispatch one `role: seed_validator` subagent if `validation_pass_enabled`.
   - Normalize all seeds to the SeedQuestion schema and write to disk.
2. Flag seeds with `user_review.approved: null` for `/grading:review-seeds`.

## Failure modes

- seed_gen subagent returns invalid JSON → one redispatch, then mark batch as `partial`, continue with next type.
- Composition shortfall (curated < requested) → rebalance into Claude-knowledge bucket per spec §4.2.
```

`plugins/grading/skills/review-seeds/SKILL.md`:
```markdown
---
name: review-seeds
description: Interactive review gate for seed questions — main agent presents each unreviewed seed for user approve / reject / edit, writes user_review back to disk.
---

# review-seeds

**Status: stub.** Full orchestration deferred to the per-stage plan for Stage 1.

## Spec reference

`docs/superpowers/specs/2026-05-13-grading-plugin-design.md` §4.2 "User review gate".

## Inputs read

- `seed_questions/<type>/<seed_id>.yaml` with `user_review.approved` unset

## Outputs written

- Same files, with `user_review` populated.
- `traces/prepare_seed_questions/timeline.jsonl` append-only (`gate_decision` events).

## Algorithm summary (implementation deferred)

1. Iterate unreviewed seeds.
2. For each: show seed text + topic + source provenance.
3. Accept user input: approve / reject / edit.
4. Write `user_review.approved` and optional `note` back to the seed file.

## Failure modes

None at LLM level — pure interaction. Schema invariants enforced on write.
```

`plugins/grading/skills/calibrate-types/SKILL.md`:
```markdown
---
name: calibrate-types
description: Stage 2 procedure — calibrate per-type universal rubric via materialize_seed + judge + critic loop until concept-vote / score-band / axis-discrimination criteria all pass on val, then test on the held-out test set.
---

# calibrate-types (Stage 2)

**Status: stub.** Full orchestration deferred to the per-stage plan for Stage 2.

## Spec reference

`docs/superpowers/specs/2026-05-13-grading-plugin-design.md` §4.3.

## Inputs read

- `seed_questions/<type>/*.yaml` where `user_review.approved == true`
- `inputs/type_catalog.yaml`
- `config/pipeline.yaml` (`calibration.*`)

## Outputs written

- `types/<type>/universal_rubric.yaml` (frozen or warning)
- `types/<type>/calibration_meta.yaml`
- `types/<type>/test_results.yaml`
- `types/<type>/seed_artifacts/<seed_id>/{concept_overlay.yaml, synthetic_answers.yaml, gold_concept_coverage.yaml}`
- `types/<type>/iterations/iter_NN/{candidate_rubric.yaml, val_judge_outputs.yaml, val_criterion_outcomes.yaml, critic_proposal.yaml}`
- `traces/calibrate_types/<subagent_id>.json` + `timeline.jsonl`

## Algorithm summary (implementation deferred)

1. Initialize: load candidate axes, uniform weights; dispatch `axis_criterion_drafter` per type.
2. For each seed: dispatch `materialize_seed` (parallel up to `max_parallel_seeds`).
3. Split train / val / test deterministically by `SHA(seed_id)`.
4. Iterate up to `max_iterations`:
   - Dispatch `judge` per val seed.
   - Aggregate via `plugins/grading/python/aggregation.py`.
   - Check the three criteria.
   - If all pass: break.
   - Else: dispatch `critic` with train-set failures; apply revisions; persist `iter_NN/`.
5. Held-out test pass with frozen-candidate rubric.
6. Status tag: `frozen` (all pass), `warning_test_marginal` (val pass, test fail), or `failed_to_converge` (max_iterations hit).

## Failure modes

- judge / critic subagent malformed output → one redispatch, then hard fail on critic, soft fail on judge (mark val outcome `partial`).
- max_iterations without val pass → status `failed_to_converge`, halt run.
- val pass + test fail → status `warning_test_marginal`, halt at universal layer unless `--proceed-on-warning`.
```

`plugins/grading/skills/test-universal/SKILL.md`:
```markdown
---
name: test-universal
description: Ad-hoc Stage 2 test pass — dispatches fresh seed_gen + materialize_seed + judge against the frozen universal rubric for sanity-checking.
---

# test-universal

**Status: stub.** Full orchestration deferred to the per-stage plan for Stage 2.

## Spec reference

`docs/superpowers/specs/2026-05-13-grading-plugin-design.md` §4.3 step 8.

## Inputs read

- `types/<type>/universal_rubric.yaml` (frozen)

## Outputs written

- `types/<type>/adhoc_test_<timestamp>.yaml`
- `traces/calibrate_types/<subagent_id>.json` for the ad-hoc dispatches

## Algorithm summary (implementation deferred)

Fresh `seed_gen` (N seeds) → `materialize_seed` per seed → `judge` per seed → criterion check. Does **not** modify the frozen `status`.
```

`plugins/grading/skills/generate-rubric/SKILL.md`:
```markdown
---
name: generate-rubric
description: Stage 3 procedure — for one assessment question, generate synthetic answers + per-question concept overlay + gold coverage against the frozen universal rubric.
---

# generate-rubric (Stage 3)

**Status: stub.** Full orchestration deferred to the per-stage plan for Stage 3.

## Spec reference

`docs/superpowers/specs/2026-05-13-grading-plugin-design.md` §4.4.

## Inputs read

- `inputs/questions/<course>/<q>.yaml`
- `types/<type>/universal_rubric.yaml` (must be `status: frozen` or `--proceed-on-warning`)
- `sources/<source>/content.md` for the question's `sources`

## Outputs written

- `rubrics/<course>/<q>/rubric.yaml`
- `synthetic_answers/<course>/<q>/{answers.yaml, gold_concept_coverage.yaml}`
- `rubrics/<course>/<q>/iterations/iter_NN/` per overlay refinement iteration
- `traces/generate_rubric/<subagent_id>.json` + `timeline.jsonl`

## Algorithm summary (implementation deferred)

1. Pre-flight: refuse if universal status is `warning_test_marginal` (without override) or `failed_to_converge`.
2. Dispatch one `question_workup` subagent that emits answers + axis perturbations + overlay + gold coverage.
3. Sanity-check via `judge` subagent; if fail, dispatch `overlay_critic` and iterate up to `overlay_refinement_iterations`.
4. On exhaustion, status `degraded` (this question only; run continues for others).

## Failure modes

- Universal rubric not frozen → refuse (unless `--proceed-on-warning`).
- Overlay refinement exhausted → status `degraded`.
```

`plugins/grading/skills/gold-grade/SKILL.md`:
```markdown
---
name: gold-grade
description: Stage 4 procedure — apply Claude judge to all synthetic answers for one question, batched in one subagent dispatch, producing the gold reference scores.
---

# gold-grade (Stage 4)

**Status: stub.** Full orchestration deferred to the per-stage plan for Stage 4.

## Spec reference

`docs/superpowers/specs/2026-05-13-grading-plugin-design.md` §4.5.

## Inputs read

- `rubrics/<course>/<q>/rubric.yaml`
- `synthetic_answers/<course>/<q>/answers.yaml`
- `types/<type>/universal_rubric.yaml`

## Outputs written

- `grades/<course>/<q>/grades.yaml`
- `traces/gold_grade/<subagent_id>.json` + `timeline.jsonl`

## Algorithm summary (implementation deferred)

1. Dispatch one `judge` subagent per question, batching all answers × (concept, axis) pairs.
2. `plugins/grading/python/aggregation.py:compute_aggregate` per answer.
3. Emit per-question summary (`mean_by_quality`, `ordering_preserved`, `bands_satisfied`, `axis_discrimination_passed`).
4. Flag `degraded` if bands or ordering fail.

## Failure modes

- judge output malformed → one redispatch, then hard fail (this is the gold standard).
- bands_satisfied == false or ordering_preserved == false → question flagged `degraded`; run continues.
```

`plugins/grading/skills/run-course/SKILL.md`:
```markdown
---
name: run-course
description: Orchestrator skill — runs generate-rubric + gold-grade for every question in a course, in parallel up to max_parallel_questions, after verifying Stages 0–2 prerequisites.
---

# run-course

**Status: stub.** Full orchestration deferred to the per-stage plan for the orchestrator.

## Spec reference

`docs/superpowers/specs/2026-05-13-grading-plugin-design.md` §4.6.

## Inputs read

- `inputs/questions/<course>/*.yaml`
- All prerequisite Stage-0/1/2 artifacts in the active run folder

## Outputs written

- All Stage-3 and Stage-4 artifacts per question.
- `runs/<id>/summary_<course>.yaml`

## Algorithm summary (implementation deferred)

1. Verify prerequisites: refuse if `sources/`, `seed_questions/`, or `types/` is missing for any required type.
2. Dispatch per-question subagents in parallel (cap: `max_parallel_questions`). Each runs Stage 3 then Stage 4 sequentially.
3. After all complete: write `summary_<course>.yaml` (per-question status, aggregate-by-quality, dispatch counts, elapsed times).

## Failure modes

- Missing prerequisite → refuse with explicit message naming the missing artifact.
- Per-question failure → record `degraded` in summary; run continues.
```

- [ ] **Step 4: Run to verify pass**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/test_skill_stubs.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/grading/skills/ plugins/grading/python/tests/test_skill_stubs.py
git commit -m "feat(grading-plugin): SKILL.md stubs for all 8 preprocessing skills"
```

---

## Task 21: Command stubs (10 command files)

**Files:**
- Create: `plugins/grading/commands/translate.md`
- Create: `plugins/grading/commands/seeds.md`
- Create: `plugins/grading/commands/review-seeds.md`
- Create: `plugins/grading/commands/calibrate.md`
- Create: `plugins/grading/commands/test-universal.md`
- Create: `plugins/grading/commands/question.md`
- Create: `plugins/grading/commands/gold-grade.md`
- Create: `plugins/grading/commands/course.md`
- Create: `plugins/grading/commands/status.md`
- Create: `plugins/grading/commands/diff.md`
- Create: `plugins/grading/python/tests/test_command_stubs.py`

Each command body invokes the corresponding skill via the standard "Use the `grading:<skill>` skill" idiom.

- [ ] **Step 1: Write the failing test**

Create `plugins/grading/python/tests/test_command_stubs.py`:

```python
import re
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[2]
COMMANDS_DIR = PLUGIN_ROOT / "commands"

EXPECTED = {
    "translate": "translate-sources",
    "seeds": "prepare-seed-questions",
    "review-seeds": "review-seeds",
    "calibrate": "calibrate-types",
    "test-universal": "test-universal",
    "question": "generate-rubric",
    "gold-grade": "gold-grade",
    "course": "run-course",
    "status": None,           # no skill — direct python helper
    "diff": None,             # no skill — direct python helper
}

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


def _frontmatter(text: str) -> dict[str, str]:
    m = FRONTMATTER_RE.match(text)
    assert m, "missing frontmatter"
    out: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip().strip("'\"")
    return out


def test_all_command_files_present():
    actual = {p.stem for p in COMMANDS_DIR.glob("*.md")}
    assert actual == set(EXPECTED)


def test_each_command_has_description():
    for name in EXPECTED:
        fm = _frontmatter((COMMANDS_DIR / f"{name}.md").read_text())
        assert fm.get("description"), name


def test_each_command_references_its_skill_or_helper():
    for name, skill in EXPECTED.items():
        body = (COMMANDS_DIR / f"{name}.md").read_text()
        if skill:
            assert f"grading:{skill}" in body, f"{name} -> {skill}"
        else:
            assert "plugins/grading/python/" in body, name
```

- [ ] **Step 2: Run to confirm failure**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/test_command_stubs.py -v
```

Expected: failures (no command files).

- [ ] **Step 3: Create the 10 command files**

`plugins/grading/commands/translate.md`:
```markdown
---
description: "Stage 0 — translate a PDF or markdown source into canonical content.md + meta.yaml under the active run folder."
---

Use the `grading:translate-sources` skill.

## Arguments

- `<source_path>` — path to a `.pdf` or `.md` file inside `inputs/sources_raw/`
- `--name <source_name>` — override the auto-derived source name on collision
- `--run <prefix>` — target a specific run folder; defaults to most recent

## Status

Stub command. The skill itself is also a stub; full orchestration arrives in the Stage 0 plan.
```

`plugins/grading/commands/seeds.md`:
```markdown
---
description: "Stage 1 — build the cross-topic seed-question pool per type (curated + source-derived + Claude-knowledge)."
---

Use the `grading:prepare-seed-questions` skill.

## Arguments

- `--types <T1,T2,...>` — restrict to specific types; default is all types in `inputs/type_catalog.yaml`
- `--run <prefix>` — target a specific run folder

## Status

Stub.
```

`plugins/grading/commands/review-seeds.md`:
```markdown
---
description: "Interactive review gate — approve / reject / edit unreviewed seed questions."
---

Use the `grading:review-seeds` skill.

## Arguments

- `--type <T>` — restrict to one type
- `--accept-all` — non-interactive batch-approve mode
- `--run <prefix>` — target a specific run folder

## Status

Stub.
```

`plugins/grading/commands/calibrate.md`:
```markdown
---
description: "Stage 2 — calibrate the universal-layer rubric per type via concept-vote / score-band / axis-discrimination criteria."
---

Use the `grading:calibrate-types` skill.

## Arguments

- `--types <T1,T2,...>` — restrict to specific types
- `--proceed-on-warning` — allow downstream stages to consume a `warning_test_marginal` rubric
- `--run <prefix>` — target a specific run folder

## Status

Stub.
```

`plugins/grading/commands/test-universal.md`:
```markdown
---
description: "Run an ad-hoc Stage 2 test pass against fresh Claude-generated seeds for a calibrated universal rubric."
---

Use the `grading:test-universal` skill.

## Arguments

- `--type <T>` — type to test
- `--seeds <N>` — number of fresh seeds to generate
- `--run <prefix>` — target a specific run folder

## Status

Stub.
```

`plugins/grading/commands/question.md`:
```markdown
---
description: "Stage 3 — generate the per-question rubric, synthetic answers, and gold concept coverage for one question."
---

Use the `grading:generate-rubric` skill.

## Arguments

- `--course <course_id>` — required
- `--question <question_id>` — required
- `--run <prefix>` — target a specific run folder

## Status

Stub.
```

`plugins/grading/commands/gold-grade.md`:
```markdown
---
description: "Stage 4 — Claude judge applies the per-question rubric to all synthetic answers, writes gold reference scores."
---

Use the `grading:gold-grade` skill.

## Arguments

- `--course <course_id>` — required
- `--question <question_id>` — required
- `--run <prefix>` — target a specific run folder

## Status

Stub.
```

`plugins/grading/commands/course.md`:
```markdown
---
description: "Orchestrator — run Stages 3 + 4 for every question in a course, in parallel up to max_parallel_questions."
---

Use the `grading:run-course` skill.

## Arguments

- `<course_id>` — required, positional
- `--run <prefix>` — target a specific run folder

## Status

Stub.
```

`plugins/grading/commands/status.md`:
```markdown
---
description: "Print the current run's state: stage completion, pending questions, last error."
---

Run the Python helper:

```bash
.venv/bin/python -m plugins.grading.python.validate_run --runs-root preprocessing/runs
```

This will print `OK: <run_dir>` or `FAIL: <run_dir>` plus a list of failing artifacts.

## Arguments

- `--run <prefix>` — target a specific run folder; defaults to most recent

## Status

Stub.
```

`plugins/grading/commands/diff.md`:
```markdown
---
description: "Semantic diff between two run folders — universal rubrics, per-question rubrics, grades."
---

Run the Python helper:

```bash
.venv/bin/python -c "from plugins.grading.python.diff import diff_runs; from pathlib import Path; import sys; d = diff_runs(Path(sys.argv[1]), Path(sys.argv[2])); print(d)" -- <run_a> <run_b>
```

A user-facing CLI wrapper around `diff_runs` arrives in a later plan.

## Arguments

- `<run_a>` — first run prefix or path
- `<run_b>` — second run prefix or path

## Status

Stub.
```

- [ ] **Step 4: Run to verify pass**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/test_command_stubs.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/grading/commands/ plugins/grading/python/tests/test_command_stubs.py
git commit -m "feat(grading-plugin): slash-command stubs for /grading:* (10 commands)"
```

---

## Task 22: Hook scaffold

**Files:**
- Create: `plugins/grading/hooks/hooks.json`
- Create: `plugins/grading/hooks/post_subagent_validate.sh`
- Create: `plugins/grading/python/tests/test_hooks_scaffold.py`

The hook config wires a `PostToolUse` event matcher to a shell script that re-runs `validate_run` against the active run folder.

- [ ] **Step 1: Write the failing test**

Create `plugins/grading/python/tests/test_hooks_scaffold.py`:

```python
import json
import os
import stat
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[2]
HOOKS_DIR = PLUGIN_ROOT / "hooks"


def test_hooks_json_exists_and_parses():
    data = json.loads((HOOKS_DIR / "hooks.json").read_text())
    assert "hooks" in data
    assert isinstance(data["hooks"], dict)


def test_post_subagent_script_exists():
    p = HOOKS_DIR / "post_subagent_validate.sh"
    assert p.is_file()


def test_post_subagent_script_executable():
    p = HOOKS_DIR / "post_subagent_validate.sh"
    mode = p.stat().st_mode
    assert mode & stat.S_IXUSR, oct(mode)
```

- [ ] **Step 2: Run to confirm failure**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/test_hooks_scaffold.py -v
```

Expected: failures.

- [ ] **Step 3: Create the hook files**

`plugins/grading/hooks/hooks.json`:
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Task",
        "hooks": [
          {
            "type": "command",
            "command": "\"${CLAUDE_PLUGIN_ROOT}/hooks/post_subagent_validate.sh\"",
            "async": false
          }
        ]
      }
    ]
  }
}
```

`plugins/grading/hooks/post_subagent_validate.sh`:
```bash
#!/usr/bin/env bash
# Post-subagent validation hook.
# Re-runs validate_run against the most-recent run folder under preprocessing/runs.
# Exit 0 = OK; exit 1 = at least one artifact failed schema validation.
#
# Status: stub. The per-stage plan that introduces an active-run pointer will
# wire this to the actual active run folder rather than always picking the
# most recent one.

set -euo pipefail

if [[ ! -d "preprocessing/runs" ]]; then
  # No runs yet — nothing to validate.
  exit 0
fi

.venv/bin/python -m plugins.grading.python.validate_run \
  --runs-root preprocessing/runs
```

- [ ] **Step 4: Make the script executable**

```bash
chmod +x plugins/grading/hooks/post_subagent_validate.sh
```

- [ ] **Step 5: Run to verify pass**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/test_hooks_scaffold.py -v
```

Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add plugins/grading/hooks/ plugins/grading/python/tests/test_hooks_scaffold.py
git commit -m "feat(grading-plugin): hooks/hooks.json + post_subagent_validate.sh scaffold"
```

---

## Task 23: Update CLAUDE.md test pipeline

**Files:**
- Modify: `/Users/erlebach/src/2026/grading_assessment/autograder/CLAUDE.md`
- Modify: `/Users/erlebach/src/2026/grading_assessment/CLAUDE.md`

The current "Test Pipeline" snippet enumerates `tests/test_*.py` for the v1 grading pipeline. Add the grading-plugin tests as a second, equally-required invocation.

- [ ] **Step 1: Inspect current CLAUDE.md test-pipeline section**

```bash
grep -n "Test Pipeline" /Users/erlebach/src/2026/grading_assessment/autograder/CLAUDE.md
```

The block starts near the top of the file with the heading `## Test Pipeline (mandatory before every commit)`.

- [ ] **Step 2: Edit `autograder/CLAUDE.md`**

In `/Users/erlebach/src/2026/grading_assessment/autograder/CLAUDE.md`, locate this block:

```
**Run the full new-pipeline test suite:**

```bash
.venv/bin/python -m pytest tests/test_models.py tests/test_check_extraction.py tests/test_categorization.py tests/test_deduplication.py tests/test_rubric_generator.py tests/test_check_evaluation.py tests/test_scoring.py tests/test_grade_storage.py -v
```
```

Append (do not replace) immediately after that fenced block:

```
**Run the grading-plugin foundation test suite:**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/ -v
```

Both suites must be green before any commit that touches `grading_pipeline/`, `grading_dynamic_rubrics/`, or `plugins/grading/`.
```

- [ ] **Step 3: Apply the same change to the parent `CLAUDE.md`**

Apply the same insertion to `/Users/erlebach/src/2026/grading_assessment/CLAUDE.md`, which has a sibling "Test Pipeline" block.

- [ ] **Step 4: Sanity-run the combined suite**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/ -v
```

Expected: all green (this should already be the case from prior tasks).

- [ ] **Step 5: Commit**

```bash
git add /Users/erlebach/src/2026/grading_assessment/autograder/CLAUDE.md /Users/erlebach/src/2026/grading_assessment/CLAUDE.md
git commit -m "docs: extend Test Pipeline to include grading-plugin foundation tests"
```

---

## Task 24: Final pass — full test suite green + plan-completion handoff

**Files:**
- Read: every test file under `plugins/grading/python/tests/`

- [ ] **Step 1: Run the whole grading-plugin suite**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/ -v
```

Expected output: every test passes. If any test fails, treat as a bug in earlier tasks and fix in-place before continuing.

- [ ] **Step 2: Run the full repo test suite for regression check**

```bash
.venv/bin/python -m pytest tests/ plugins/grading/python/tests/ -v --ignore=tests/tmp_chroma_indexes
```

Expected: existing tests remain green; new tests all pass.

- [ ] **Step 3: Confirm the manifest, configs, skills, commands, hooks, and helpers are all in place**

```bash
ls plugins/grading/.claude-plugin/plugin.json plugins/grading/config/ plugins/grading/skills/ plugins/grading/commands/ plugins/grading/hooks/ plugins/grading/python/
```

Expected: all listed entries present.

- [ ] **Step 4: Stage and commit anything missed (should be no-op if every prior task committed cleanly)**

```bash
git status --short
```

If clean: nothing to commit. If not, investigate before deciding what to do — do **not** blanket `git add .`.

---

## Self-review notes

This plan covers:
- §0 framing — N/A (design only)
- §1 architecture — partial: skill/command names are locked here, but stage orchestration is deferred per the user's "foundation" scope choice
- §2 run isolation / reproducibility — partial: `snapshot.py` covers the tarball, `run_resolution.py` covers `--run <prefix>` resolution, the smoke fixture demonstrates the layout. `REPRODUCE.md` generation is part of stage-level orchestration → deferred to per-stage plans.
- §3 data model — **fully covered**: every schema in §3 has a model + validator + tests. Aggregation §3.3 has a worked-example test + property tests.
- §4 stage details — stage logic is **deliberately stubbed**: each `SKILL.md` is a section-mapped skeleton with explicit "Status: stub. Full orchestration deferred" markers and pointers back to the spec section.
- §5 tracing — partial: `TimelineEvent` schema is in place; subagent-summary JSON schema is defined; actual trace emission is part of stage orchestration → deferred.
- §6 testing — **fully covered**: schema/aggregation/validator/run-resolution/snapshot/pdf/diff/contracts/smoke tests all land in this plan.
- §7 open questions — resolved in this plan: plugin name (`grading`), short skill names, manifest is JSON at `.claude-plugin/plugin.json`. Other §7.2 items (parallelism defaults, retry policy specifics, hook scripting language → bash) are committed via `config/pipeline.yaml` and `hooks/post_subagent_validate.sh`.
- §8 plugin layout — **fully covered** for the foundation surface area.

Items deliberately out of scope of this foundation plan, to be addressed in follow-up plans (one per stage):
- Stage 0 — `translate-sources` subagent + pdf_translator role wiring
- Stage 1 — `prepare-seed-questions` + `review-seeds` subagent flows
- Stage 2 — calibration loop, iter_NN persistence, criterion logic on real judge output
- Stage 3 — per-question workup, overlay refinement loop
- Stage 4 — per-question batched judge dispatch + summary computation
- Orchestrator — `run-course` parallel dispatch + summary writing
- Stage-level `trace_summary.yaml` aggregation + `timeline.jsonl` emission helpers
- `REPRODUCE.md` generation
- Active-run pointer for hook script (so `post_subagent_validate.sh` validates the right run, not just the most recent)
- Source content-addressed cache (§2 "Future enhancement")
