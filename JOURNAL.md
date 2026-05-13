---

## 2026-05-13 16:07 — Labeling cleanup: drop V1/V2 in favor of "earlier draft" / "Option D" + autograder-v3 framing

The 2026-05-13 specs had been calling themselves V1/V2, which collided
with the autograder's existing v1 (legacy keyword pipeline) and v2
(concept-check pipeline under `v2/`, `version2/`). Both 2026-05-13
specs are drafts of the autograder's **v3** direction (gold
preprocessing benchmark); the earlier one (SDK-driven) was superseded
same-day by the plugin design (Option D). Header-only cleanup, no
substantive design changes:

- `2026-05-13-grading-plugin-design.md` header: replaced "V1 spec" / "V2"
  labels with "earlier same-day draft" / "this design"; added paragraph
  clarifying that both 2026-05-13 specs are drafts of the autograder's
  broader v3 direction.
- `2026-05-13-preprocessing-benchmark-design.md` header: status switched
  from "DRAFT — brainstorming in progress" to "SUPERSEDED same-day" with
  a forward pointer to the plugin design; preserved as historical
  record of the considered SDK approach.
- SNAPSHOT.md: same labeling cleanup applied to the v3 bullet.

Earlier today's JOURNAL entries (15:35, 16:00) still use "V1/V2" — those
are kept as written so the timeline remains lossless; future readers
should map "V1 spec" → "2026-05-13 SDK draft" and "V2 spec" → "2026-05-13
plugin design / Option D."

---

## 2026-05-13 16:00 — Rewrote V2 spec under Option D (Claude Code grading plugin)

Rewrote `docs/superpowers/specs/2026-05-13-grading-plugin-design.md` from
the byte-identical V1 copy into the full V2 / Option D design. §1
invocation switched to `/grade:*` slash commands; §4 stage algorithms
rewritten as subagent dispatches (with explicit `role:` tags) plus
Python helper calls, with LLM operations batched aggressively (one
subagent per seed in Stage 2's `materialize_seed`; one per question in
Stage 4's `judge`). §5 tracing replaced with per-subagent JSON summaries
pointing into `.specstory/` for full transcripts. §6 testing dropped
cassettes in favor of pure-Python tests plus a fixture-driven structural
smoke. §7.2 implementation-time questions updated; new §8 added with the
full `plugins/grading/` plugin layout (manifest, skills, commands,
hooks, Python helpers, role/tier-dispatch config). §§0, 2, 3 (schemas +
aggregation), 7.1/7.3/7.4 unchanged — architecture-independent. V1 spec
preserved as historical record.

### Details

**Section-by-section rewrites in `2026-05-13-grading-plugin-design.md`:**

- **Header**: title now "Design (Option D: Claude Code Grading Plugin)";
  added "Diverges from" pointer to V1 spec; preamble lists what carries
  over vs. what changes.
- **§1 Pipeline architecture**: invocation block rewritten as the
  `/grade:*` command surface (`/grade:translate`, `/grade:seeds`,
  `/grade:review-seeds`, `/grade:calibrate`, `/grade:test-universal`,
  `/grade:question`, `/grade:gold-grade`, `/grade:course`,
  `/grade:status`, `/grade:diff`). Added paragraph on the
  skill → subagent dispatch → Python helper → role-tier-dispatch
  layering.
- **§4.0 Universal contracts**: trace mechanism reworded — JSON summary
  per subagent at `traces/<stage>/<subagent_id>.json`; full transcripts
  via Claude Code session history; explicit `role` tag taxonomy
  (`pdf_translator`, `seed_gen`, `seed_validator`, `materialize_seed`,
  `judge`, `critic`, `gold_annotator`, …).
- **§4.1 Stage 0**: PDF rendering moved to a Python helper (`pdf_render.py`
  using `pymupdf`); the LLM extraction is a single `pdf_translator`
  subagent dispatch.
- **§4.2 Stage 1**: each generation operation is now a `seed_gen` (and
  optional `seed_validator`) subagent batched per type. User-review CLI
  switched to `/grade:review-seeds`.
- **§4.3 Stage 2**: per-seed scoring set produced by a single
  `materialize_seed` subagent (9 answers + axis perturbations + throwaway
  overlay + gold coverage in one batched JSON). Iteration loop dispatches
  one `judge` subagent per val seed plus one `critic` subagent per
  refinement. Standalone test command switched to `/grade:test-universal`.
- **§4.4 Stage 3**: per-question scoring set materialized by one
  `question_workup` subagent (answers + concept overlay + gold coverage
  in one batched response). Sanity-check refines only the overlay via an
  `overlay_critic` subagent.
- **§4.5 Stage 4**: one `judge` subagent per question, batching all
  answers × all (concept, axis) pairs in a single structured JSON.
  Per-question parallelism is achieved at the *between-question* level by
  the `/grade:course` wrapper.
- **§4.6 `/grade:course`**: parallelism knob is `max_parallel_questions`
  (default 3, tuned to MAX rate limits).
- **§5 Tracing & retry**: full rewrite. Per-subagent JSON summary schema
  (call_id, role, tier, inputs, outputs, status, session_transcript_ref).
  Retry strategy is "Claude Code handles transient HTTP; main agent
  re-dispatches on subagent `status: error` up to `max_redispatches`."
  Per-stage `trace_summary.yaml` aggregates dispatches across roles.
- **§6 Testing**: cassettes dropped. New: Python-helper unit tests,
  subagent-output schema contract tests (independent of live LLM),
  fixture-driven structural smoke test, live end-to-end manual workflow,
  plugin-manifest validation, tier-dispatch config validation.
- **§7.2**: removed cassette/API-key items; added role catalog,
  parallelism limits, plugin-manifest schema, hook scripting language
  as remaining implementation-time questions.
- **§7.4**: refreshed audit-trail commitments to reference the new
  Option D trace mechanism (session transcripts under `.specstory/` plus
  per-subagent JSON summaries).
- **§8 NEW**: plugin layout — full directory tree under
  `plugins/grading/`, plugin.yaml manifest sketch, skill conventions,
  example `tier_dispatch.yaml` showing role → model mapping, install
  steps.

**Next session:**

- Invoke `superpowers:writing-plans` to produce a step-by-step
  implementation plan from this V2 spec.
- Scaffold `plugins/grading/` directory (manifest, skill stubs, command
  stubs, Python helper modules with NotImplementedError bodies).

---

## 2026-05-13 15:35 — Brainstormed gold preprocessing benchmark; mid-session pivot to Option D (Claude Code plugin)

Brainstormed via `/superpowers:brainstorming` a gold-preprocessing pipeline
that produces frozen rubrics, synthetic answers, gold concept coverage, and
gold reference scores — these artifacts become a benchmark for future
cheap grading approaches (OSS judges, retrieval-only, etc.). V1 spec
written at `docs/superpowers/specs/2026-05-13-preprocessing-benchmark-design.md`
(7 sections: framing, 5-stage pipeline, run isolation, data model +
schemas + aggregation, stage details, tracing, testing, open questions).
Mid-session pivot to **Option D** on user pushback: V1 assumed Python +
Anthropic SDK, which would duplicate billing on top of Claude MAX.
Option D re-architects everything as a Claude Code plugin at
`plugins/grading/`, all LLM work via subagents under MAX, with aggressive
batching collapsing the earlier "thousands of calls" estimate to ~450/run.
V1 spec preserved as historical record; an empty byte-identical copy is
already on disk at `2026-05-13-grading-plugin-design.md` ready for the
Option D rewrite next session.

### Details

**Key design decisions (ratified in conversation, architecture-independent):**

- **Two-layer rubric:** 10 universal type-level rubrics (axes + weights fixed
  per type) + per-question concept overlay (concepts with weights and
  `relevant_axes` referencing the type's axes).
- **Universal layer is cross-topic** — calibrated with seeds spanning ≥ J
  topical domains (Claude-knowledge + curated + source-derived). Never
  bootstrapped on a single course (user vetoed an earlier recommendation).
- **Calibration criterion:** concept-vote agreement + score-bands + axis
  discrimination, the latter via axis-perturbation answers — sharper
  diagnostic than v2 Karpathy's ordering-only criterion.
- **Discrete labels:** judge picks `full | partial | none`, mapped to fixed
  values `{1.0, 0.5, 0.0}`. Per-axis criteria in the universal rubric.
- **Run isolation:** every invocation lives in `runs/<id>/`, id format
  `YYYY-MM-DD_HH-MM-SSZ__<fingerprint>` (correlates with `.specstory/history/`).
- **Reproducibility:** `src_snapshot.tar.gz` per run + `git_sha` — two
  independent reproduction paths.
- **Persistence policy:** nothing inside a run folder is ever discarded.
  Every iteration's intermediate state is on disk for audit.

**Option D specifics (not yet written into a spec):**

- Plugin at `plugins/grading/` with manifest, skills (one per stage),
  slash commands (`/grade:translate`, `/grade:seeds`, `/grade:calibrate`,
  `/grade:question`, `/grade:course`, `/grade:status`, `/grade:diff`,
  …), hooks (post-subagent YAML validation), Python helpers (schema,
  aggregation, diff, snapshot — no LLM, no SDK).
- Operations tagged by `role` (`answer_gen` / `critic` / `judge` /
  `gold_annotator` / …); plugin config maps role → tier (Claude Opus /
  Sonnet / Haiku now; Ollama Gemma4 later, already validated in user's setup).
- LLM calls batched aggressively — one call generates 20 seed questions;
  one call generates all 13 synthetic answers for a seed (good + less_good
  + wrong + axis perturbations) in a single structured JSON; one call
  judges all val-set answers in an iteration.

**Next session:**

- Rewrite §§1, 4, 5, 6 of the spec under Option D on
  `docs/superpowers/specs/2026-05-13-grading-plugin-design.md`. §§0, 2, 3, 7
  carry over verbatim. Add new §8 (plugin manifest + command surface +
  tier-dispatch config).
- Build out `plugins/grading/` skeleton (manifest, skill stubs, command
  stubs, Python helpers).
- After Option D spec is locked: invoke `superpowers:writing-plans` to
  produce a step-by-step implementation plan.

---

## 2026-05-12 22:18 — Follow-up idea: subagent-per-grade fan-out (not yet designed)

If grading shifts to Claude (rather than an OSS judge), the work is
embarrassingly parallel and a subagent could grade independently with its
own isolated context. Two natural fan-out shapes both have problems:
**(a) one subagent per test** — grades all 10 questions for one student;
each subagent loads 10 rubrics + 10 question texts + 30 exemplar answers +
10 student answers, which risks context overload. **(b) one subagent per
question** — grades that question for all 50 students; same overload risk
plus less natural caching of the per-student state. **(c) per-(student,
question)** — one subagent grades one student on one question, against
one rubric + 3 exemplars + 1 answer; fits comfortably in context, but each
subagent does very little work and the dispatch overhead per grade is
non-trivial.

Right granularity is open. Possible middle-ground: one subagent per
student (grades all 10 questions sequentially) with rubrics + exemplars
streamed in question-by-question to bound peak context. Design needed
before implementation.

Subagent-driven execution vendored Tasks 1–6 of the version2/ benchmark
plan (commits `bb891e7..ff1e482`): skeleton, v2 modules, config + slides
PDF, run_v2_benchmark.py with PDF_PATH re-anchored, tests/v2/ (44 pass,
1 pre-existing fail in test_llm_tier.py). Task 7 smoke run failed:
`httpx.ReadTimeout` on the 7th LLM call under 300s timeout — single
anomalous call, not structural. Reading v2 surfaced three real gaps: no
retry logic at any `.complete()` site, no prompt/response trace, and
`KarpathyLoop._score_set` only scores `answers[0]` so multi-variant
generation is mostly unused. Conversation pivoted to a simpler
architecture: foundational model preprocesses (questions, exemplar
answers, rubrics) offline; OSS grades at runtime per rubric dimension
with retrieval_core wired in; Karpathy loop dropped. No code from the
pivot yet — paused on Task 7. Wrote V2_BENCHMARK_2026-05-12.md (flowchart).

### Details

**Branch:** new branch `version2-self-contained-benchmark` cut from
`v2-concept-rubrics` at HEAD `4399723`. All work below is on the new branch.

**Vendoring commits (Tasks 1–6):**
- `bb891e7` Task 1 — directory scaffold (7 dirs, 4 marker files).
- `19ac471` Task 2 — `version2/v2/*.py`, 12 files vendored verbatim from `autograder/v2/`.
- `7414fb9` Task 3 — `version2/config/{llm_config.py,rubric_generation.yaml}`
  copied whole (not trimmed — deviation from spec, documented in plan).
- `01989ae` Task 4 — slides PDF (1,125,947 bytes, byte-identical).
- `9d2fc4c` Task 5 — `run_v2_benchmark.py` with single edit:
  `PDF_PATH = REPO_ROOT / "sources" / "slides_data_type_quality.pdf"`.
- `ff1e482` Task 6 — `tests/v2/*.py`, 11 files vendored; pytest from
  `version2/` reports 44 passed / 1 failed (pre-existing).

**Task 7 smoke failure:**
- Command: `cd version2 && PYTHONPATH=. ../.venv/bin/python scripts/run_v2_benchmark.py --questions q01 --tier oss --report results/v2_smoke_q01.md`.
- First 6 answer-gen LLM calls completed in 22–45s each (good ×3, less_good ×3).
- Call 7 (`wrong variant 1/3`) stalled past 300s → `httpx.ReadTimeout`. The
  script caught the exception, wrote a `QuestionResult(error="ReadTimeout: timed out")`,
  exited 0. Partial artifacts at `version2/results/v2_smoke_q01.{md,log,stdout}`,
  uncommitted, retained for diagnosis.
- Ollama state at failure: `gemma4:26b` loaded (22.9 GB VRAM, context 8192),
  no crash on Ollama side. Root cause not pinned (probably model-internal
  generation slowness on one sample); 17.5k-char prompt is identical across
  all 9 answer_gen calls, so no structural reason "wrong" should be slower.

**Architectural pivot (under discussion, not yet implemented):**

| User's 9-step process | v2 today | Offline (foundational) / Runtime (OSS) | Mod needed |
|---|---|---|---|
| Generate 10 questions from slides | hardcoded `QUESTIONS` dict | offline | New `version2/preprocess/gen_questions.py` → `questions.yaml` |
| Generate good/less_good/wrong answers | `AnswerGenerator` at runtime | offline | New `gen_answers.py` → `answers.yaml`; runtime loads |
| Generate rubric per question | `RubricGeneratorV2` at runtime | offline | New `gen_rubrics.py` → `rubrics/q0N.yaml`; runtime loads |
| Word + sentence chunking | exists in `retrieval_core/` | offline | Already there; persist index once |
| Retrieve chunks by query | not wired into v2 | runtime, no LLM | Wire `retrieval_core` call |
| Rerank by rubric dimension | exists in `retrieval_core/multi_retriever.py` | runtime, no LLM | Wire it in |
| LLM judge per dimension w/ chunks | `ConceptJudge` exists, `evidence_context=""` | runtime, OSS | Fill `evidence_context` with reranked chunks |
| Average grade | `compute_grade` in `v2/scoring.py` | runtime | Already there |

**Dropped:** Karpathy refinement loop (offline-trusted rubric makes
per-run iteration redundant). The plan's Tasks 7–10 are obsolete in their
current form.

**Files added on this branch (uncommitted at journal-write time):**
`V2_BENCHMARK_2026-05-12.md` (flowchart) at the repo root.

**Open architectural question:** whether the OSS judge should receive
(a) reranked PDF chunks as context (the 9-step process), or (b) the 9
labeled exemplar answers as in-context anchors (an earlier proposal in
this session). Both ground the judge; (b) has a much smaller prompt and
no retrieval dependency, (a) is closer to the validated 8.5/6.5/1.5 result.

---

## 2026-05-12 16:45 — rubric-layer analysis, v2 rationale captured, Ollama timeout 120→300

Bumped Ollama `request_timeout` 120→300 s in `config/llm_config.py` — follow-on
from 2026-05-11 22:29 gpt-oss:20b debugging where first calls of a benchmark
run occasionally exceeded the 120 s ceiling. Added three analysis docs:
`RUBRICS_ANALYSIS_2026-05-12.md` (rubric-layer trace, corrects the prior claim
that root `rubrics/q0N.yaml` is unused), `V2_RATIONALE_2026-05-12.md`
(consolidated v1→v2 rationale against `REDESIGN.md` §1–2), and `V1_STATE_2026-05-12.md`
(v1 pipeline baseline). Superpowers brainstorming settled the next move:
self-contained `version2/` benchmark of q01–q05 on oss tier — design doc to be
written on a new branch.

### Details

**`config/llm_config.py`** — single-line change at `request_timeout=300.0`
(was 120). Ollama runner is held for 24 h via `keep_alive`, so the timeout
matters most on cold first-call latency under large prompts.

**`RUBRICS_ANALYSIS_2026-05-12.md`** — documents the two generator scripts:
LLM-based `create_dynamic_rubrics_for_each_question.py` (writes `rubrics/yaml/`
and `rubrics/json/`) vs non-LLM `create_rubrics_for_all_questions.py` (writes
root flat `rubrics/q0N.yaml` stubs). Corrects prior claim that root files are
unused — `grading_pipeline/config/rubrics.yaml` references them for q01–q03
and `cli.py` reads that config. Explains the config-update guard at
`create_dynamic_rubrics_for_each_question.py:765` (`if question_id not in
config["rubrics"]`) which prevents stale entries from being overwritten.

**`V2_RATIONALE_2026-05-12.md`** — confirms the four user-recalled motivations
against `REDESIGN.md` (keyword brittleness, foundational-model rubric gen,
overlapping criteria, concept-grading). Adds operationalised prompt rules
(`v2/rubric_generator.py` prompt enforces "vocabulary-agnostic; judge meaning,
not words"; per-question-type templates carry the same). Specstory addendum
notes the `.specstory/history/` transcripts add no rationale beyond
`REDESIGN.md`.

**`V1_STATE_2026-05-12.md`** — was already staged before this turn; bundled
into this commit because it's part of the same documentation push.

---

## 2026-05-12 14:19 — v2 benchmark: llama_cpp noise fix, oss tier switch, unbuffered logging

### Changes

**`config/llm_config.py`** — removed two `print()` calls from the module-level
`LlamaGrammar` try/except block. The block printed `✗ Failed to compile JSON_GRAMMAR`
on every import when `llama_cpp` is not installed, flooding benchmark output. The
`JSON_GRAMMAR = None` fallback is unchanged; the grammar is not used anywhere outside
that file.

**`config/rubric_generation.yaml`** — switched `model_tier` from `foundational`
(Gemini Flash) to `oss` (Ollama `gemma4:26b`). Gemini free tier is capped at
5 RPM, which is prohibitive for the ~54 LLM calls per question the v2 benchmark makes.

**`v2/answer_generator.py`, `v2/rubric_generator.py`, `v2/judge.py`,
`v2/karpathy_loop.py`** — added `logger.info` calls at every LLM call site and
at every Karpathy-loop decision point (train scoring, violations found, val scoring,
critic call, convergence/failure). Previously all four modules defined a `logger`
but never called it, so the benchmark ran silently with no progress indication.

**`scripts/run_v2_benchmark.py`** — added `_FlushFileHandler` (flushes after every
`emit`) and `--log PATH` CLI argument. Log path defaults to `<report>.log` (e.g.
`results/v2_benchmark_q01.log`). Log format includes `HH:MM:SS` timestamps on every
line so per-step latency is visible. Both stderr and the log file receive all output.

### Run command

```bash
ollama serve &   # bare server, not Electron app
.venv/bin/python scripts/run_v2_benchmark.py \
    --questions q01 \
    --report results/v2_benchmark_q01.md
# tail -f results/v2_benchmark_q01.log  (second terminal)
```

---

## 2026-05-12 13:05 — Ollama stable 50/50; root cause was old GGML blobs, not GamePolicyAgent

Probe `scripts/probe_ollama.py --model gemma4:26b --n 50 --interval 5` completed 50/50 OK,
0 kill events, longest streak 50, avg latency 2.75 s. VERDICT: stable.

Todays crashes were caused by **old GGML-format model blobs** (magic `746a6767` = `ggjt`)
in `~/.ollama/models/blobs/`. When `ollama serve` starts it scans every manifest to hydrate
a model-show cache; hitting a pre-GGUF blob triggered fatal tensor-read errors that killed
the server before any client connected. This had nothing to do with GamePolicyAgent.

8 incompatible blobs (44.5 GB total) and 10 manifests deleted directly from disk, bypassing
`ollama rm` (which itself calls `POST /api/show` and crashes the server for the same reason).
Affected models: llama2:13b-chat, llama2:13b-text, llama2:text, codellama:13b,
codellama:7b-code, codellama:7b-instruct, codellama:latest, ge:latest,
ge_model:latest, codeup:latest.

GamePolicyAgent mitigations (kill-gamepolicy every 10 s, cleanup-bundles every 30 min)
remain deployed and working. Electron Ollama.app auto-start (com.ollama.ollama SMAppService
login item) found running without user intent; killed for this session. Permanent removal:
System Settings > General > Login Items > remove Ollama.

---

## 2026-05-12 09:54 — launchd mitigations deployed; SIGKILL required; placeholder bundle removed

Both launchd agents loaded and confirmed running (exit code 0 in `launchctl list`):
`com.user.kill-gamepolicy` (10 s interval) and `com.user.cleanup-bundles` (1800 s interval).

**kill-gamepolicy:** `pkill -x GamePolicyAgent` and direct `kill` silently fail — macOS
blocks SIGTERM on system processes owned by the same user. `kill -9` (SIGKILL) is required.
Rewritten to use `pgrep -x GamePolicyAgent` + `kill -9 "$pid"`; verified GamePolicyAgent not
running after deployment.

**cleanup-bundles:** 8 placeholder bundles detected in `/Applications/` (no valid executable
in `Contents/MacOS/`). Only `OpenVPN Connect.app` lacked SIP protection and was successfully
`rm -rf`'d. The remaining 7 (Photos Duplicate Cleaner, foobar2000, ally, Json New Haitam,
Timer+, Speechify, Unhook) are SIP-protected; logged as "skipped (permission denied)".
`lsregister -kill` flag is deprecated and removed; script uses `-r -domain local -domain
system -domain user` only. A `sed -i ''` pattern-mismatch emptied the script file mid-session;
restored from session context. `kill-gamepolicy` is the primary effective mitigation since 7
placeholder bundles feeding the GamePolicy loop cannot be removed without admin.

---

## 2026-05-12 09:19 — GamePolicyAgent Ollama-kill: Apple Discussions confirms root cause; mitigations planned

Apple Discussions thread #256283688 confirms the SIGKILL root cause documented 2026-05-11:
GamePolicyAgent enters an infinite loop when placeholder/incomplete app bundles exist in
`/Applications/` (bundles with no valid executable in `Contents/MacOS/`). Retries on a
~203 s cadence, creating corrupt Launch Services database entries. The
`backgroundtaskmanagementd` + AppIntents chain then SIGKILLs the Ollama subprocess via
the Electron wrapper.

Running bare `ollama serve` (no Electron) removes the supervisor-kill chain but does NOT
eliminate GamePolicyAgent's scan loop — system interference continues.

**Mitigations to deploy (this session):**
1. `~/.local/bin/kill-gamepolicy.sh` every 10 s via launchd — resets the scan cycle
   before database corruption accumulates.
2. `~/.local/bin/cleanup-bundles.sh` every 30 min via launchd — removes no-executable
   bundles older than 1 h; runs `lsregister -kill -r` only if something is removed.
3. `OLLAMA-ELECTRON-GamePolicy.md` committed to repo with full root-cause + mitigation docs.

See `OLLAMA-ELECTRON-GamePolicy.md` for complete technical write-up.

---

## 2026-05-11 22:54 — Ollama SIGKILL root-caused to macOS GamePolicyAgent

The probe (50 calls × 5 s) caught 2 kills on a strikingly regular ~203 s
cadence (22:25:50.532 and 22:29:13.605). Unified-log queries
(`log show --start … --end …`) around each kill timestamp show the
identical chain: `/usr/libexec/GamePolicyAgent` wakes up, scans every
`.app` bundle in `/Applications/` to decide whether it's a game (Sandbox
denies `file-read-xattr` on `Ollama.app`, `OBS.app`, `AnythingLLM.app`,
etc.), `backgroundtaskmanagementd` enumerates the Ollama login-item +
LaunchAgent, the Electron wrapper `Ollama[1039]` re-registers with
AppIntents, and ~1 s later the wrapper SIGKILLs its `ollama serve`
subprocess (PID 64304 in run 1). The ~203 s cadence is GamePolicyAgent's
scan interval. **Code is not at fault** — three prior fixes
(`context_window=8192`, `keep_alive="24h"`, `check_type` enum) stand.

**Fix:** quit the Electron `Ollama.app` and run the bare CLI
(`ollama serve`) from terminal. The bare process is not managed by
`backgroundtaskmanagementd` / AppIntents, so GamePolicyAgent's scans
can't trigger the supervisor-kill chain.

### Details

Kill-correlation evidence (representative excerpt, kill #1):

```
22:25:49.487  GamePolicyAgent(64962) deny(1) file-read-xattr .../Electron.app
22:25:49.569  GamePolicyAgent(64962) deny(1) file-read-xattr /Applications/Ollama.app
22:25:49.606  Ollama[1039]   [appintents:Connection] Registered process 1039-2678
22:25:50.532  kernel         tcp_close ollama:64304 listener on :11434
22:25:50.533  mDNSResponder  DNSServiceCreateConnection STOP PID[64304](ollama)
```

Kill #2 (22:29:12 → 22:29:13.605) shows GamePolicyAgent itself being
freshly launched as PID 65575, then the same scan-→-reregister-→-kill
sequence — confirming GamePolicyAgent's own start cadence drives the
event, not just an internal scan loop.

**The `anon<Ollama>(501):1039` process the 20:05 entry noticed in
RunningBoard logs is now identified**: PID 1039 is the long-lived
Electron Ollama.app, the supervisor that SIGKILLs and respawns its
`ollama serve` child each time the system pokes its bundle.

**Probe summary:** 48/50 ok, 2 kill events, longest streak 27,
verdict `unstable` (exit 1) — exactly as designed.

**Next:** quit Ollama.app, start `ollama serve` from terminal, re-run
`scripts/probe_ollama.py --n 50 --interval 5`, expect 0 kills, then
proceed to `scripts/run_v2_benchmark.py --tier oss --questions q01`.

---

## 2026-05-11 22:22 — Ollama stability probe added (scripts/probe_ollama.py)

Added `scripts/probe_ollama.py`, a standalone MWE for diagnosing the
SIGKILL cadence flagged in the 2026-05-11 20:05 entry before kicking off
the (~30–45 min) v2 benchmark. The probe instantiates the same Ollama
client used by the v2 pipeline (`configure_llm("ollama", ...)` with
`context_window=8192`, `keep_alive="24h"`, `json_mode=True`), issues N
tiny `{"answer": "OK"}` prompts at a configurable interval, and in
parallel tails `~/.ollama/logs/app.log` for `signal: killed` events on a
daemon thread. Per-call output: timestamp, latency, success/error, response
length. Summary prints longest consecutive-success streak, kill-event
count with timestamps, and an exit-code verdict (0 = stable, 1 = unstable).

Default: 50 calls × 5 s interval ≈ 5 min probe window. Imports verified
via `--help`; no live Ollama run yet. STATE "Next time, start by…" updated
to run this probe before any benchmark retry. No code outside `scripts/`
touched.

---

## 2026-05-11 20:05 — v2 benchmark blocked by Ollama runner SIGKILLs; 3 fixes landed

Three real bugs fixed today, but the q01 benchmark on `gpt-oss:20b` could
not be completed — `ollama serve` is being SIGKILLed by an external
macOS supervisor on a ~70 s–4 min cadence, killing every in-flight HTTP
request the Python client has open. 34+ kills logged in
`~/.ollama/logs/app.log` as `signal: killed` from `server.go:224`. Code
fixes: (1) `Ollama(context_window=8192)` to stop a 131 072-token KV
auto-resize that crashed the runner; (2) `Ollama(keep_alive="24h")` to
hold the runner across sequential calls; (3) enumerate allowed
`check_type` values in the rubric-gen prompt (gpt-oss:20b had been
inventing values like `concept_presence`, raising `ValidationError`).
Also includes a local revert of `config/rubric_generation.yaml::tiers.oss.model`
from `gemma4:26b` back to `gpt-oss:20b`. v2 tests (45) pass.

### Details

**SIGKILL evidence.** `~/.ollama/logs/app.log` accumulated 34
`level=ERROR source=server.go:224 msg="ollama exited" err="signal: killed"`
entries during the session. The killer is external (SIGKILL is uncatchable);
`ollama serve` is being terminated even when no client requests are pending
and no model is loaded. The `anon<Ollama>(501):1039` process shows up in
macOS RunningBoard logs with an `AfterLife-Interrupted` assertion, and
`generativeexperiencesd` + `ModelCatalogAgent` (Apple Intelligence services)
are active in parallel.

**KV-resize root cause.** The Ollama server env had
`OLLAMA_CONTEXT_LENGTH=65536` and the M2 Max's 77 GiB VRAM triggered
`default_num_ctx=262144`. When llama_index's first call did not specify
`num_ctx`, Ollama allocated a 131 072-token KV cache and re-loaded the
model, hitting `error reading tensor: unexpected EOF` mid-load. Pinning
`context_window=8192` makes Ollama allocate only the needed cache.
Verified: largest prompt in v2 (rubric-gen with full PDF + 9 synthetic
answers + JSON schema) is 19 575 chars ≈ 4 893 tokens; output ≤ 2 k
tokens; 8 k headroom is sufficient.

**check_type enum bug.** The rubric-gen prompt declared the JSON schema
as `"check_type": str` with no allowed-value list. gpt-oss:20b returned
`concept_presence`, `distinguishing_property`, `attribute_definition`,
`example_usage` — all rejected by `RubricV2Response.model_validate` (the
enum requires `definition | distinction | mechanism | positive_example |
negative_example | generalization`). Fix: append "Allowed values for
check_type (use exactly one of these strings): ..." to the prompt.

**Ruled out as SIGKILL source.** Memory pressure (96 GB RAM, 13 GB
model); a Claude `/loop` in this session (`CronList` empty); the user's
`claude-job-watcher.sh` poll script (killed mid-investigation, SIGKILLs
continued); 9 orphaned `ollama runner` PIDs from earlier failed attempts
(cleaned up, SIGKILLs continued); prompt size; model file integrity
(blob sizes match manifest); user crontab (empty).

**Still unverified.** A `/loop` in *another* Claude Code session;
macOS RunningBoard / Apple Intelligence enforcement; an Ollama 0.23.2
regression on this macOS version.

**Next session.** Pick up after the SIGKILL source is identified or
worked around (restart Ollama.app cleanly; downgrade Ollama; switch
`oss` tier to a different local model). The v2 pipeline itself has no
known remaining bugs blocking q01.

---

## 2026-05-11 17:13 — Switch v2 benchmark oss tier to gemma4:26b; parameterize driver --tier

Switched `config/rubric_generation.yaml::tiers.oss.model` from `gpt-oss:20b`
to `gemma4:26b` (Ollama, 17 GB, locally present) to sidestep the Gemini
Flash free-tier rate limit (5 RPM) that blocked the previous benchmark
attempt. Added `--tier {foundational|oss|mixed}` CLI flag to
`scripts/run_v2_benchmark.py` (default now `oss`); parameterized
`build_components()` accordingly. STATE.md "Next time, start by…" rewritten
to reflect: driver exists, oss tier ready, just needs to be run. SNAPSHOT
oss-tier line updated to name gemma4:26b. Committing this as a checkpoint
before kicking off the (estimated ~30–45 min) Ollama benchmark run, per
user request: "Before proceeding, updating JOURNAL, STATE, SNAPshot and
committing would be a good idea to have a base to return to if needed."

---

## 2026-05-11 16:45 — v2 benchmark driver added; Gemini free-tier rate limit blocks live run

Added `scripts/run_v2_benchmark.py` (the driver the previous JOURNAL entry
flagged as missing): wires `AnswerGenerator`, `RubricGeneratorV2`,
`RubricCritic`, `ConceptJudge`, and `KarpathyLoop` together over the full
text of `slides_data_type_quality.pdf` (extracted via `pypdf`), iterates
q01–q05 with question types `distinction`/`application`/`enumeration`/
`mechanism`/`definition`, and writes a markdown + JSON report. v2 unit
tests (45) pass; smoke run on q01 alone hit `ResourceExhausted: 429` —
gemini-2.5-flash free tier caps at **5 generate_content requests/minute**
and the pipeline needs ~25–45 calls per question. Driver script committed;
no benchmark numbers yet.

### Details

Pre-flight discoveries before the run:
- `~/.env` recreated with `GEMINI_API_KEY` after user prompt; verified via
  `config.llm_config.load_env_config()` (prefix `AIzaSy`, length 39).
- `WALKTHROUGH_v2.md` Step 3 mentions `GOOGLE_API_KEY` but the code reads
  `GEMINI_API_KEY` (from `$HOME/.env`). Doc gap — to fix later.
- `WALKTHROUGH_v2.md` Steps 4 and 5 import `retrieve_context` from
  `retrieval_core.retriever`. No such function exists — the real API is
  `class DualIndexRetriever`. The driver sidesteps this by passing the
  full PDF text as `source_material` and leaving `evidence_context=""`
  (per `USAGE_v2.md` Design Notes, retrieval wiring is a follow-on task).
- Existing pickle indexes in `grading_pipeline/persist/`
  (`word_index.pkl`, `sentence_index.pkl`, `paragraph_index.pkl`) are
  unused by the v2 driver in its current form.

Failure mode on smoke run:
- LLM provider: Gemini 2.5 Flash via `configure_llm_for_tier("foundational")`.
- Per-question call estimate: 9 (answer generation) + 1 (rubric generation)
  + up to 5 × (3 train + 3 val + 1 critic) = up to ~45 calls.
- Free-tier quota: 5 RPM. Pipeline saturates the limit during answer
  generation; subsequent calls return `429` with `retry_delay { seconds: 56 }`.
- Driver caught the exception and wrote an error row to the report;
  artifacts in `results/v2_benchmark_q01_smoke.{md,json}` (untracked).

Path forward (awaiting user decision):
1. Add retry/throttle (e.g. `tenacity` with exponential backoff or a
   simple `time.sleep(13)` between calls — 60s / 5 calls ≈ 12s minimum).
   Runtime ≈ 9 min/question × 5 = ~45 min for the full benchmark.
2. Upgrade Gemini billing tier (user action).
3. Switch to `oss` tier (Ollama `gpt-oss:20b`) — no rate limit but slower
   per call; quality may differ.
4. Defer live benchmark; commit the driver and revisit.

---

## 2026-05-11 15:39 — Reconcile state with v2 pivot; STATE/SNAPSHOT refreshed

`STATE.md` was stale (claimed last commit T3.4 on `dynamic_rubrics`, updated
2026-03-30) and missed ~30 commits including the entire **v2 concept-check
pipeline** in `v2/` and the T4.3 follow-up fixes that STATE had listed as
pending. Rewrote `STATE.md` for the current `v2-concept-rubrics` branch,
refreshed `SNAPSHOT.md` to include `v2/` components and design decisions, and
recorded open items: v1/v2 coexistence + deprecation policy, missing
benchmark-driver script, untracked v2 tasks, and `grade-spec.md` review
against the concept-check schema. No code changed.

### Details

T4.3 follow-up fixes that already landed but STATE didn't show:
- `839af81` int/round/float scoring comparison
- `1ce1655` stopword filter in `extract_keywords`, semantic-mode reverted to count
- `1524940` reranker-weighted semantic scoring with mode switch
- `7f6f71a` NaN fix in reranker scores
- `64e7a72`, `2e20ff9` Ollama SOCKS proxy fix

v2 pipeline delivered between `410916d` and `89e2225` (~15 feature commits):
typed `ConceptCheck` with precision levels, 10 `QuestionType` values and prompt
templates, synthetic answer generator (3×3 at T=0.7), answer-informed
`RubricGeneratorV2`, weighted-mean float scoring (no `int()` truncation),
single/multi-mode `ConceptJudge`, `RubricCritic` + `KarpathyLoop` iterative
refinement with train/val split, `PipelineV2` orchestrator, ordering benchmark
library (`find_violations`, `check_ordering`), ~45 tests in `tests/v2/`.

Cleanup commit `be97575` deleted ~11.8k lines: `version1/`, `mwe/`,
`grader/grade_question.py`, obsolete `IMPLEMENTATION_*.md` plans.

New design/usage docs (commits `2e20ff9`, `3a42f77`, `c5a562d`, `bf98c67`):
`REDESIGN.md`, `USAGE_v2.md`, `WALKTHROUGH_v2.md`, Quarto notebook
`notebooks/grade_assignment_v2.qmd`.

Open items recorded in STATE.md:
1. `v2/benchmark.py` is library-only; needs driver script per
   `WALKTHROUGH_v2.md` §4–5 plus Gemini API key or local Ollama.
2. v1 (`grading_pipeline/`, `grading_dynamic_rubrics/`) and v2 (`v2/`) coexist
   without an explicit deprecation policy.
3. `TASK_LIST.md` still v1-era (last entry T4.4 CI). No v2 task tracking.
4. `grade-spec.md` not yet reviewed against the concept-check schema.

Next: pick LLM provider, build source index, write `scripts/run_v2_benchmark.py`
per WALKTHROUGH, run on q01–q05, compare violation counts to the v1 T4.3 baseline.

---

## 2026-05-11 12:47 — Move .git into autograder/ (make autograder the repo root)

Used `git filter-repo --subdirectory-filter autograder` to rewrite history so `autograder/`
becomes the repo root. Tracked paths no longer carry the `autograder/` prefix. Remote `origin`
re-added and upstream tracking restored for `v2-concept-rubrics`. `CLAUDE.md` Git Commands
section updated to drop the `-C` flag. Commit SHAs rewritten (history content preserved).
Parent `.git` (backup) remains at `../grading_assessment/.git` and can be removed.

### Details

Steps taken:
1. Restored parent `.git` from `/tmp/git_backup` (first filter-repo attempt promoted content the wrong way)
2. Copied backup `.git` into `autograder/`, removed empty `.git` created by session startup hook
3. Ran `git filter-repo --subdirectory-filter autograder --force` from `autograder/`
4. Re-added `origin` remote: `https://github.com/erlebach/grading-assessment.git`
5. `git fetch origin` + `git branch --set-upstream-to=origin/v2-concept-rubrics`
6. Updated `CLAUDE.md` Git Commands section

---

## 2026-01-21 - Honor dynamic rubrics retrieval settings from YAML

### Completed Tasks ✅
- [x] Made `grading_dynamic_rubrics` retrieval parameters come from `sources.yaml`

### Files Created/Modified
- `autograder/grading_dynamic_rubrics/pipeline.py` - Load `retrieval.*` from config and pass into `retriever.retrieve()`

### Key Changes
- `retrieval.similarity_threshold` (and `top_k_per_index` / `final_top_k`) in
  `grading_dynamic_rubrics/config/sources.yaml` now **override** code defaults, so
  transparency logs accurately reflect YAML-driven retrieval behavior.

### Notes
- This fixes the mismatch where transparency logs showed `SIMILARITY_THRESHOLD=0.0`
  despite the YAML being set to `-1.0`.

---

## 2026-01-21 - Add transparent retriever + reranker tracing

### Completed Tasks ✅
- [x] Added `--transparent` CLI flag to both grading CLIs
- [x] Implemented verbose traces for retriever inputs/outputs and reranker

### Files Created/Modified
- `autograder/grading_pipeline/cli.py` - Added `--transparent` and passed to pipeline
- `autograder/grading_pipeline/pipeline.py` - Plumbed `transparent` flag and enabled trace
- `autograder/grading_dynamic_rubrics/cli.py` - Added `--transparent` and passed to pipeline
- `autograder/grading_dynamic_rubrics/pipeline.py` - Plumbed `transparent` flag and added per-criterion trace label
- `autograder/retrieval_core/retriever.py` - Added detailed trace logging for dual retriever + reranker
- `autograder/retrieval_core/multi_retriever.py` - Added detailed trace logging for multi-index retriever + reranker

### Key Changes
- `--transparent` enables logs that show:
  - input query text (clearly delimited)
  - per-index top-\(k\) retrieved texts with `SIMILARITY_SCORE`
  - reranker inputs (query + candidates) and reranker outputs with scores
  - dotted divider lines between successive texts for readability

### Notes
- Traces are routed through the existing log writer used by `--log`, so stdout and
  optional log files see the same transparency stream.

---

## 2026-01-21 - Route transparent traces to file

### Completed Tasks ✅
- [x] Changed `--transparent` output to write to `autograder/logs/transparent.log`

### Files Created/Modified
- `autograder/grading_pipeline/pipeline.py` - Write transparent traces to file-only writer
- `autograder/grading_dynamic_rubrics/pipeline.py` - Write transparent traces to file-only writer

### Key Changes
- When `--transparent` is enabled, trace output no longer prints to stdout; it is
  written (line-buffered + flushed) to `autograder/logs/transparent.log`.

---

## 2026-01-21 - Reorganize logging arguments

### Completed Tasks ✅
- [x] Replaced `--log` (path) with `--log-path`, `--log-file`, and `--log` (boolean)
- [x] Made normal stdout messages always write to log file
- [x] Made transparency conditional on `--log` flag

### Files Created/Modified
- `autograder/grading_pipeline/cli.py` - New logging arguments with defaults
- `autograder/grading_pipeline/pipeline.py` - Always write to log file, conditional transparency
- `autograder/grading_dynamic_rubrics/cli.py` - New logging arguments with defaults
- `autograder/grading_dynamic_rubrics/pipeline.py` - Always write to log file, conditional transparency

### Key Changes
- **`--log-path`** (default: `logs`): Directory where log files are written
- **`--log-file`** (default: `grading.log`): Name of the main log file
- **`--log`** (default: `True`): Enable transparency logging (use `--no-log` to disable)
- Normal stdout messages (e.g., `[Grading] ...`) **always** go to the log file
- Transparency traces go to `transparency.log` in the log path **only if `--log` is True**

### Notes
- Log files are always created (normal messages always logged)
- Transparency is optional and controlled by `--log` / `--no-log` flag

---

## 2026-01-21 - Clear log directory at run start

### Completed Tasks ✅
- [x] Clear log directory before each run (files only)

### Files Created/Modified
- `autograder/grading_pipeline/pipeline.py` - Delete existing log files before opening new logs
- `autograder/grading_dynamic_rubrics/pipeline.py` - Delete existing log files before opening new logs

### Notes
- Only files are deleted; subdirectories (if any) are left untouched.

---

## 2026-01-21 - Make transparency logs explicit about indexes and k

### Completed Tasks ✅
- [x] Log `ACTIVE_INDEXES` and requested \(k\) values per retrieval call
- [x] Make per-index headers explicit even when `returned=0`

### Files Created/Modified
- `autograder/retrieval_core/multi_retriever.py` - Add `RETRIEVAL PARAMETERS` header and clearer index headers
- `autograder/retrieval_core/retriever.py` - Add `RETRIEVAL PARAMETERS` header and clearer index headers

---

## 2026-01-21 - Add index diagnostics for dynamic rubrics

### Completed Tasks ✅
- [x] Added `print_index_diagnostics()` function to `grading_dynamic_rubrics/pipeline.py`

### Files Created/Modified
- `autograder/grading_dynamic_rubrics/pipeline.py` - Added diagnostics function for active in-memory indexes

### Key Changes
- `print_index_diagnostics()` prints chunk counts and size statistics (chars/tokens) for all active indexes
- Uses the same persist directory logic as `setup_grading_environment()` (default: `tmp/in_memory_indexes/`)
- Respects `runtime.active_indexes` from config or can accept `index_subset` parameter

### Notes
- Diagnostics function is specific to `grading_dynamic_rubrics` module (not in `grading_pipeline`)
- Works with `InMemoryVectorStore` indexes only

---

## 2026-01-21 - Make index diagnostics independent of OpenAI keys

### Completed Tasks ✅
- [x] Updated `print_index_diagnostics()` to load `*.pkl` stores directly (no embedder init)

### Files Created/Modified
- `autograder/grading_dynamic_rubrics/pipeline.py` - Load pickles directly for diagnostics

### Notes
- This avoids triggering any LLM/embedder configuration, so it works without OpenAI credentials.

---

## 2026-01-19 - Dynamic rubric generation with LLM

### Completed Tasks ✅
- [x] Created prompt template file (rubric_generator_template.txt) with placeholders
- [x] Created Pydantic schema (rubric_schema.py) for JSON validation
- [x] Added source file loading function using _extract_text_from_pdf
- [x] Added prompt template loading and formatting functions
- [x] Added LLM integration function with retry logic and Pydantic validation
- [x] Added JSON to rubric structure conversion function
- [x] Added dual format saving function (JSON and YAML subdirectories)
- [x] Modified main() function with comprehensive CLI arguments
- [x] Created wrapper script create_dynamics_rubrics.x
- [x] Created comprehensive pytest test suite (test_create_dynamic_rubrics.py) with 25 tests

### Files Created/Modified
- `autograder/gp/rubric_generator_template.txt` - Prompt template for LLM rubric generation
- `autograder/gp/rubric_schema.py` - Pydantic models for validating LLM JSON responses
- `autograder/gp/create_dynamic_rubrics_for_each_question.py` - Complete rewrite with LLM-based dynamic rubric generation
- `autograder/create_dynamics_rubrics.x` - Wrapper script for easy execution
- `autograder/tests/test_create_dynamic_rubrics.py` - Comprehensive pytest test suite (25 tests covering all functions and error cases)

### Key Changes
- Transformed rubric generation from generic templates to LLM-based dynamic generation
- Added support for source file context (PDF, text, markdown) in prompts
- Implemented Pydantic validation with retry logic (up to 3 attempts)
- Added dual output format: JSON (raw LLM output) and YAML (pipeline-compatible)
- Comprehensive CLI with --source-file, --prompt-template, --llm-provider, --llm-model, --dry-run, --verbose
- Module execution support: `python -m gp.create_dynamic_rubrics_for_each_question`
- Default LLM configuration: Ollama with gpt-oss:20b (matching grader setup)
- JSON extraction handles markdown code blocks and plain JSON
- Criterion ID generation via slugification of dimension titles
- Automatic rubric config updates pointing to YAML files

### Notes
- Rubrics are saved in `<rubrics_dir>/json/` and `<rubrics_dir>/yaml/` subdirectories
- JSON files contain both raw LLM output and converted rubric structure
- YAML files are compatible with existing grading pipeline
- Prompt template supports {QUESTION_TEXT} and {SOURCE_FILE_CONTENT} placeholders
- Retry logic provides feedback to LLM on validation failures
- Comprehensive test suite covers all functions, error cases, and integration scenarios
- All 25 tests pass successfully

---

## 2026-01-18 - Embedder metadata verification

### Completed Tasks ✅
- [ ] Added embedder metadata save/load and verification for indexes
- [ ] Fixed circular import between index builders
- [ ] Added embedder details to index build/load output
- [ ] Disabled embedding prepend instructions and printed defaults
- [ ] Added embedding consistency diagnostics in similarity test
- [ ] Added side-by-side embedding value dump for debugging
- [ ] Excluded metadata from embeddings for text nodes
- [ ] Added YAML-driven flag to enable embedding diagnostics
- [ ] Added test to ensure metadata is excluded from embeddings

### Files Created/Modified
- `autograder/grading_pipeline/index_builder.py` - Added embedder metadata helpers and verification wrapper for ChromaDB load.
- `autograder/grading_pipeline/index_builder_in_memory.py` - Store/embedder metadata and print usage details; removed local helpers.
- `autograder/grading_pipeline/test_cosine_similarity.py` - Embedded consistency check output.
- `autograder/config/llm_config.py` - Print default embedding instructions, disable prepends.
- `autograder/grading_pipeline/config/sources.yaml` - Added debug flag for diagnostics.
- `autograder/tests/test_index_builder_in_memory.py` - Added metadata exclusion test.

### Key Changes
- Persist embedder info to `embedding_metadata.yaml` in index directories.
- Verify embedder matches before loading indexes; raise error on mismatch.
- Output embedder type/model during build and load for clarity.
- Use empty `text_instruction` and `query_instruction` to remove prepends.
- Compare stored/text/query embeddings to isolate mismatch causes.
- Print first 20 embedding values and cosine similarity.
- Ensure node embeddings use text only (no metadata).
- Gate embedding diagnostics behind config flag.
- Validate metadata does not affect embeddings.

### Notes
- Embedder metadata now guards against silent model drift.

---

## 2026-01-18 - Add index backend selection

### Completed Tasks ✅
- [ ] Added CLI flag to select index backend (ChromaDB vs in-memory)
- [ ] Routed pipeline index setup through backend selector
- [ ] Updated grading script to use in-memory backend explicitly

### Files Created/Modified
- `autograder/grading_pipeline.x` - Added index backend flag in run script.
- `autograder/grading_pipeline/cli.py` - Added `--index-backend` to CLI and passed through.
- `autograder/grading_pipeline/pipeline.py` - Added backend-aware index selection helper.

### Key Changes
- `--index-backend` controls which index builder is used at runtime.
- Pipeline setup now selects between ChromaDB and in-memory builders.
- Index directory help text now reflects generic persistence.

### Notes
- Default backend remains `chromadb` when the flag is omitted.

---

## 2026-01-18 - Align in-memory embed model on load

### Completed Tasks ✅
- [ ] Ensured in-memory loader uses stored embedding metadata
- [ ] Rebuilt in-memory indexes with BAAI/bge-small-en-v1.5
- [ ] Reran grading pipeline successfully

### Files Created/Modified
- `autograder/grading_pipeline/index_builder_in_memory.py` - Load embedding using stored metadata for verification.

### Key Changes
- Removed hardcoded MiniLM placeholder in in-memory load path.
- Embedding model now matches persisted metadata when loading indexes.

### Notes
- Grading run completed with 4/4 successful after rebuild.

---

## 2026-01-18 - Add embedding model log during index load

### Completed Tasks ✅
- [ ] Added log line showing resolved embedding model during index load

### Files Created/Modified
- `autograder/grading_pipeline/index_builder_in_memory.py` - Log configured embedding model for tracing.

### Key Changes
- Print embedding type and model name when configuring from stored metadata.

### Notes
- Improves traceability when debugging embedding model mismatches.
