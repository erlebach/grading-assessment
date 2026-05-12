# V2 Rationale — Why the Autograder Was Redesigned

*Compiled 2026-05-12 from existing project documents.*

This file collects, in one place, the documented reasons v1 was replaced by v2.
Every claim below is sourced from a file in the repo; citations follow each point.

---

## Source documents

| File | Role |
|------|------|
| `REDESIGN.md` | **Canonical design rationale** (dated 2026-03-31). §1 ("What We Learned") and §2 ("Core Design Insight") are the primary motivation text. |
| `docs/superpowers/plans/2026-03-31-v2-concept-rubrics.md` | Implementation plan; restates the goal at top, then lays out the task-by-task build. |
| `V1_STATE_2026-05-12.md` | Snapshot of the v1 pipeline (entry points, scoring formula, schema) — provides the baseline that REDESIGN.md argues against. |
| `WALKTHROUGH_v2.md`, `USAGE_v2.md` | How to run v2 once built. Confirm the implemented architecture matches the design. |
| `JOURNAL.md` | Dated entries about each implementation step; useful for "when was X decided" but secondary for rationale. |
| `RUBRICS_ANALYSIS_2026-05-12.md` | Independent analysis of the rubric layer (root stubs vs LLM-generated authoritative rubrics, dual generation scripts). |

---

## The four points from your memory, against the docs

### 1. "v1 graded partially based on keywords, which is brittle"

**Confirmed by `REDESIGN.md` §1 (Why it fails, points 1, 2, 3) and `V1_STATE_2026-05-12.md` §3.**

v1 combined two signals per criterion:

```
combined_score = keyword_weight × keyword_score + semantic_weight × semantic_score
```
(`V1_STATE_2026-05-12.md:53–55`, `REDESIGN.md:17–19`)

- `keyword_score` = fraction of criterion keywords found in the student answer (`REDESIGN.md:21`).
- `semantic_score` = `min(1, evidence_chunks_retrieved / top_k)` (`REDESIGN.md:22`).

`REDESIGN.md:28–30` states the brittleness directly:

> "A student who writes 'you can't divide Celsius temperatures' has the right concept but misses the keyword 'ratio'. Keyword score = 0. Correct answer = 0."

Two other related failure modes are documented:

- **Stopword leakage** — rubric prose like "full credit", "awarded", "student", "provides" dominates the keyword set and dilutes signal (`REDESIGN.md:32–35`).
- **Semantic signal is non-discriminating** — retrieval count is roughly constant across good/less_good/wrong answers on the same topic, so `evidence_count / top_k` provides no discrimination (`REDESIGN.md:37–39`).

### 2. "v1 depended on dynamically-created rubrics, generated on foundational models and stored under `rubrics/`"

**Confirmed by `RUBRICS_ANALYSIS_2026-05-12.md` and `V1_STATE_2026-05-12.md` §2.**

- The dynamic rubric generator is `grading_pipeline/create_dynamic_rubrics_for_each_question.py`. It calls an LLM via `config/llm_config.configure_llm()`, validates the JSON response with `RubricJsonResponse`, then writes four artifacts per question under `<rubrics-dir>/json/` and `<rubrics-dir>/yaml/` (`RUBRICS_ANALYSIS_2026-05-12.md`, §"What Generates `rubrics/yaml/` and `rubrics/json/`").
- The LLM was a "foundational" tier model by default (Gemini Flash); see `REDESIGN.md:336–337`: *"Settable, defaulting to **Gemini Flash** (fast, no deep reasoning required for this task)."* The same default appears in `config/rubric_generation.yaml` before the 2026-05-12 switch to `oss` (see `JOURNAL.md` 2026-05-12 14:19 entry: "switched `model_tier` from `foundational` (Gemini Flash) to `oss`").
- Storage layout: `rubrics_dynamic/yaml/q0N.yaml` (default `--rubrics-dir`) or `rubrics/yaml/q0N.yaml` (when the script is invoked with `--rubrics-dir rubrics`). `V1_STATE_2026-05-12.md:23–26` confirms `rubrics_dynamic/yaml/q0N.yaml` as the v1 input path.

### 3. "Some questions had multiple dimensions, and sometimes the same issue was graded twice, making the grade less reliable"

**Confirmed indirectly. The v1 generator already had a partial defense; v2 makes the defense structural.**

`REDESIGN.md:34–35` flags that "P2 (this session) partially addressed [stopwords] but did not fix ordering violations" — i.e., even after cleanup, the *ranking* of good > less_good > wrong did not hold. The next paragraph (`REDESIGN.md:47–52`) lists specific ordering violations on q03 and q05.

The v1 LLM generator was extended with `validate_criterion_independence()` (lines 194–266 of `grading_pipeline/create_dynamic_rubrics_for_each_question.py`): it asks a second LLM call to detect overlapping deduction targets and regenerate on overlap. This is the in-place v1 mitigation for "same issue graded twice"; the comment string in that function — *"If Criterion A deducts for 'missing alternative names' and Criterion B also deducts for 'not providing alternative names', that's an overlap"* — matches your recollection verbatim.

v2 replaces this **detection-and-retry** approach with a structural rule: each dimension is restricted to **non-overlapping aspects** by template and enforced by the Karpathy refinement loop, which only converges when ordering holds on a held-out validation split (`REDESIGN.md:213–217`).

### 4. "Concept grading was seen as more reasonable than keyword grading"

**Confirmed by `REDESIGN.md` §2 — this is stated as the core design insight.**

`REDESIGN.md:58–64`:

> "**Replace keyword matching with concept-presence evaluation by an LLM judge.**
>
> A criterion is no longer 'does the answer contain these words?' but 'does the answer demonstrate this concept, at what level of precision?'
>
> This is vocabulary-agnostic, handles paraphrase, and naturally produces partial credit."

Implementation: the v2 criterion schema (`REDESIGN.md:72–104`) replaces keyword lists with typed `ConceptCheck` objects, each with `precision_levels` (`full` / `partial` / `none`). The `ConceptJudge` LLM rates each check; weighted-mean scoring gives a float without truncation.

---

## Additional rationale that goes beyond your four bullets

These are documented motivations in the source files that you didn't recall — worth knowing.

### A. v1 truncated ~80% of scores to zero

`REDESIGN.md:45`:

> "**`int()` truncation collapses ~80% of scores to 0** (P1, partially addressed)."

`V1_STATE_2026-05-12.md:56–59` shows the three v1 score variants — `score_int = int(combined × max_points)` was the default and discards everything below the next integer. v2 mandates *float scores throughout, no `int()` truncation anywhere* (`REDESIGN.md:349`).

### B. v1 rubrics were generated only from slides, never from answer data

`REDESIGN.md:41–44`:

> "**Rubric generated from slides only, independently of answers.** The rubric uses slide vocabulary; students use their own vocabulary (they have access to AI and the web). Mismatch is structural, not fixable by stopword lists."

v2 generates **3 synthetic answers per quality level × 3 levels = 9 answers** at T=0.7, then uses those as vocabulary grounding alongside the textbook/slides during rubric generation (`REDESIGN.md:166–195`).

### C. Karpathy-style iterative refinement, not a one-shot rubric

v2 treats rubric generation as a research loop: generate → score train answers → check ordering → critic LLM proposes fixes → repeat → validate on held-out answers before stopping (`REDESIGN.md:197–228`). This was inspired by Karpathy's autoresearch loop and is one of the design's distinguishing features versus v1's static rubric.

The train/val split (6 train / 3 held-out) is an explicit overfitting guard. A complexity budget (max 4 checks per criterion) is a second guard.

### D. Question-type registry as a prior on rubric structure

A late-added design element (`REDESIGN.md` §10, lines 354–390): questions are catalogued into ~10 types (`definition`, `distinction`, `mechanism`, `classification`, `enumeration`, …). Each type carries a prompt template and an example bank so example generation is reusable across questions of the same type. This both:

- Stabilises positive/negative examples (which were unreliable when redefined per question), and
- Constrains the rubric-generator search space, reducing overfitting risk.

### E. Switchable evaluation mode and model tier

v2 makes two empirical questions explicit, configurable, and comparable (`REDESIGN.md:135–157`):

- **`evaluation_mode`**: `single` (one LLM call per answer evaluates all checks) vs `multi` (one call per check).
- **`model_tier`**: `oss` (`gpt-oss:20b` via Ollama, local), `foundational` (Claude/GPT-4 via API), or `mixed` (foundational for rubric generation, oss for scoring).

The benchmark (good > less_good > wrong ordering) is the metric for choosing among them.

### F. Retrieval is retained but repurposed

Dual-index retrieval (word + sentence) and the cross-encoder reranker carry over from v1, but their **role changes** (`REDESIGN.md:231–240`):

- v1 used retrieved chunk count as the semantic score directly.
- v2 passes retrieved chunks as **context to the LLM judge**, which uses them to locate relevant course material when evaluating concept presence.

---

## Addendum — what `.specstory/history/` adds

The specstory archive (`.specstory/history/*.md`, 72 transcripts) was sampled for v2 rationale. Most v2-era transcripts are *implementation* logs (debugging SOCKS-proxy issues, running benchmarks, Ollama stability) rather than design discussion. The substantive rationale was authored once, in `REDESIGN.md` (2026-03-31), and then mirrored into `docs/superpowers/plans/2026-03-31-v2-concept-rubrics.md`.

Two additional pieces worth capturing — they don't add new rationale but they show the rationale being **operationalized in code** and are useful as citations:

### Vocabulary-agnostic enforcement in the rubric-generator prompt

`v2/rubric_generator.py` puts the concept-vs-keyword principle directly in the LLM prompt (visible in transcript `2026-03-31_22-02-12Z-ok-continue-writing-the.md:1589–1599`):

> "RUBRIC DESIGN RULES:
> - Criteria test concept presence, not vocabulary match.
> - Each check must be vocabulary-agnostic: judge meaning, not words.
> - Precision levels: full=1.0, partial=0.5, none=0.0.
> - The rubric must discriminate good > less_good > wrong answers."

So the v1→v2 motivation (keyword brittleness) is not just a design-doc claim — it's a hard rule in the rubric-generation prompt itself.

### Per-question-type templates enforce the principle further

The same transcript shows the `DEFINITION` template (line ~1004):

> "Focus checks on concept presence, not vocabulary match."

…and the `DISTINCTION` template asks for "the key distinguishing property" rather than wording. These templates are the question-type registry mentioned in `REDESIGN.md` §10 turned into prompt-level priors.

### Synthetic answer generator's stated purpose

`v2/answer_generator.py` docstring (transcript line ~1313):

> "Uses a foundational LLM at T=0.7 to produce vocabulary variation, making rubrics robust to phrasing differences."

This makes explicit *why* T=0.7 was chosen: to spread the vocabulary distribution so the rubric is forced to generalize.

### Transcripts that don't add rationale (for completeness)

- `2026-03-31_03-39-59Z-…` and `2026-03-31_03-46-31Z-…`: SOCKS-proxy/Ollama debugging during a v1 benchmark run; no v2 design content.
- `2026-03-30_22-38-06Z-make-sure-state-md.md`: test-suite work and STATE.md updates; no v2 design content.
- `2026-05-11_*` and `2026-05-12_*`: Ollama stability (GamePolicyAgent, GGML blob crash), gpt-oss:20b tensor-EOF debugging, git/journal workflow. Implementation, not rationale.
- `2026-03-31_22-02-12Z-ok-continue-writing-the.md`: this is the **plan being authored**; it restates `REDESIGN.md` in checkbox form and adds the prompt-string fragments quoted above, but no new top-level rationale.

The conclusion: `REDESIGN.md` and the superpowers plan are the canonical sources; the specstory transcripts confirm the rationale was enforced in code (prompts, templates) but do not extend or contradict it.

---

## One-paragraph summary

The autograder moved from v1 to v2 because v1's scoring was a weighted sum of two
signals that both turned out to be poor proxies for understanding: keyword overlap
penalised paraphrase, and retrieval-chunk count failed to discriminate answer
quality. Stopwords and overlapping criteria amplified the noise; `int()`
truncation collapsed most scores to zero. v2 replaces the keyword leg with an
LLM concept-presence judge over typed checks with precision levels, keeps
retrieval as evidence context only, generates answer-informed rubrics
iteratively against synthetic good/less_good/wrong sets with a held-out
validation split, and uses float scores throughout. The canonical rationale is
in `REDESIGN.md` (2026-03-31, §1–§2 for motivation and §3–§10 for the response).
