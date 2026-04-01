# Grading an Assignment with Autograder v2 — Step-by-Step Walkthrough

## What This Guide Covers

You have:
- A folder of source materials (PDF, MD, TXT) — the course content students were assessed on
- A JSON file listing all exam questions
- A JSON file of student answers

You want:
- One JSON feedback file per student per question, containing score, per-check rationale, and improvement suggestions

This guide walks through every step from raw files to final feedback.

---

## Prerequisites

### Python environment

```bash
cd /path/to/autograder
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -e .
```

### API keys

The v2 pipeline uses **Gemini Flash** by default (the `foundational` tier).

**Option A — Gemini (recommended default)**

Get a key at https://aistudio.google.com/app/apikey, then:

```bash
# Add to your shell profile (~/.zshrc or ~/.bashrc) — never commit this file
export GOOGLE_API_KEY="your-key-here"
```

Reload: `source ~/.zshrc`

**Option B — Ollama (local, no API key required)**

Install Ollama from https://ollama.com, then pull the model:

```bash
ollama pull gpt-oss:20b
```

Change `model_tier` to `oss` in `config/rubric_generation.yaml` (see Step 3).

---

## Step 1 — Organise Your Input Files

Create a working directory for this assignment:

```
assignments/
  my_assignment/
    source_materials/         ← your PDF, MD, TXT files go here
      chapter3.pdf
      lecture_notes.md
      ...
    questions.json            ← one file listing all questions
    answers/
      student_001.json        ← one file per student
      student_002.json
      ...
```

### `questions.json` format

```json
[
  {
    "question_id": "q01",
    "question_text": "Why can't you compute ratios on a Celsius temperature scale?",
    "question_type": "mechanism",
    "max_points": 10
  },
  {
    "question_id": "q02",
    "question_text": "Define 'interval scale' and distinguish it from a ratio scale.",
    "question_type": "distinction",
    "max_points": 10
  }
]
```

**Valid `question_type` values:**

| Value | When to use |
|-------|-------------|
| `definition` | "Define X" |
| `distinction` | "Distinguish X from Y" / "What is the difference between…" |
| `mechanism` | "Why does X happen?" / "Explain how X works" |
| `classification` | "Classify the following items…" |
| `enumeration` | "List all…" / "Name the four…" |
| `example_generation` | "Give an example of…" |
| `error_identification` | "What is wrong with this statement?" |
| `comparison` | "Compare X and Y" |
| `application` | "Apply concept X to scenario Y" |
| `proof_or_argument` | "Argue that…" / "Prove that…" |

### `student_NNN.json` format

Each student file contains all their answers:

```json
{
  "student_id": "student_001",
  "answers": {
    "q01": "Celsius has an arbitrary zero point — the freezing point of water. Because zero does not represent the absence of temperature, ratios are meaningless. 20°C is not twice as hot as 10°C.",
    "q02": "An interval scale has equal spacing between values but an arbitrary zero..."
  }
}
```

---

## Step 2 — Index Your Source Materials

Before grading, you need to build a searchable index of your source materials. This is the **retrieval** step — it lets the grader look up relevant passages when evaluating student answers.

> **What is retrieval?** The pipeline stores your source documents in a vector database. When grading an answer, it searches for the most relevant passages and passes them to the LLM judge as context. This grounds the judge in your course material rather than general LLM knowledge.

```bash
cd assignments/my_assignment

python -c "
from retrieval_core.index_builder import build_index

build_index(
    source_dir='source_materials/',
    index_dir='index/',          # where the index is saved
    chunk_size=512,
    chunk_overlap=64,
)
print('Index built.')
"
```

This creates an `index/` folder. You only need to do this once per assignment (or when source materials change).

---

## Step 3 — Configure the Pipeline

Edit `config/rubric_generation.yaml` to match your setup:

```yaml
model_tier: foundational        # foundational (Gemini) | oss (Ollama) | mixed
evaluation_mode: single         # single (faster) | multi (more precise per check)
max_iterations: 5               # Karpathy refinement rounds — 3–5 is usually enough
max_checks_per_criterion: 4     # keep at 4 unless rubrics feel too coarse
answer_variants_per_level: 3    # 3 gives good vocabulary coverage; reduce to 1 for speed
answer_temperature: 0.7         # temperature for synthetic answer generation
train_per_level: 2
val_per_level: 1
```

**Speed vs. quality trade-offs:**

| Goal | Settings |
|------|----------|
| Fast prototype | `max_iterations: 2`, `answer_variants_per_level: 1`, `evaluation_mode: single` |
| Production quality | `max_iterations: 5`, `answer_variants_per_level: 3`, `evaluation_mode: multi` |

---

## Step 4 — Generate Rubrics (Once Per Question)

For each question, the pipeline:
1. Generates 9 synthetic answers (3 good / 3 less_good / 3 wrong) using the LLM
2. Generates an initial rubric grounded in your source material and those answers
3. Runs the Karpathy loop — iteratively refines the rubric until it correctly ranks the synthetic answers

You run this **once per question**, before grading any students.

```python
# scripts/generate_rubrics.py
import json
from pathlib import Path

from config.llm_config import configure_llm_for_tier
from retrieval_core.retriever import retrieve_context
from v2.answer_generator import AnswerGenerator, AnswerGeneratorConfig
from v2.rubric_generator import RubricGeneratorV2, RubricGeneratorConfig
from v2.rubric_critic import RubricCritic
from v2.judge import ConceptJudge, EvaluationMode
from v2.scoring import compute_grade
from v2.karpathy_loop import KarpathyLoop, KarpathyConfig
from v2.benchmark import check_ordering

ASSIGNMENT_DIR = Path("assignments/my_assignment")
RUBRICS_DIR    = ASSIGNMENT_DIR / "rubrics"
RUBRICS_DIR.mkdir(exist_ok=True)

# Load questions
questions = json.loads((ASSIGNMENT_DIR / "questions.json").read_text())

# Set up LLM
llm = configure_llm_for_tier("foundational")

# Set up components
answer_gen  = AnswerGenerator(llm=llm, config=AnswerGeneratorConfig(variants_per_level=3))
rubric_gen  = RubricGeneratorV2(llm=llm, config=RubricGeneratorConfig())
critic      = RubricCritic(llm=llm)
judge       = ConceptJudge(llm=llm, mode=EvaluationMode.SINGLE)

def scorer(**kw):
    evals = judge.evaluate(
        answer_text=kw["answer_text"],
        rubric=kw["rubric"],
        evidence_context="",
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

for q in questions:
    qid   = q["question_id"]
    out   = RUBRICS_DIR / f"{qid}.json"

    if out.exists():
        print(f"{qid}: rubric already exists, skipping.")
        continue

    print(f"\n=== Generating rubric for {qid} ===")

    # Retrieve relevant source passages for this question
    source_material = retrieve_context(
        query=q["question_text"],
        index_dir=str(ASSIGNMENT_DIR / "index"),
        top_k=5,
    )

    # Generate synthetic answers
    answers = answer_gen.generate(
        question_id=qid,
        question_text=q["question_text"],
        question_type=q["question_type"],
        source_material=source_material,
    )

    # Generate initial rubric
    initial_rubric = rubric_gen.generate(
        question_id=qid,
        question_text=q["question_text"],
        question_type=q["question_type"],
        source_material=source_material,
        synthetic_answers=answers,
        version=1,
    )

    # Karpathy refinement
    result = loop.run(
        initial_rubric=initial_rubric,
        answers=answers,
        question_id=qid,
        question_text=q["question_text"],
        question_type=q["question_type"],
        source_material=source_material,
    )

    status = "converged" if result.converged else f"stopped at {result.iterations_used} iterations"
    print(f"  {qid}: rubric ready ({status})")

    # Save rubric
    rubric_dict = result.final_rubric.model_dump(mode="json")
    out.write_text(json.dumps(rubric_dict, indent=2))
    print(f"  Saved → {out}")

print("\nAll rubrics generated.")
```

Run it:

```bash
python scripts/generate_rubrics.py
```

This produces `assignments/my_assignment/rubrics/q01.json`, `q02.json`, etc.

**Check rubric quality:** Open a rubric JSON and read the `criteria` and `checks`. Each check should describe a *concept*, not a keyword. If a check says "mentions the word 'arbitrary'" that is a bad check. It should say "states that the zero point has no physical significance".

---

## Step 5 — Grade Student Answers

With rubrics in hand, grade each student's answers.

```python
# scripts/grade_students.py
import json
from pathlib import Path

from config.llm_config import configure_llm_for_tier
from retrieval_core.retriever import retrieve_context
from v2.rubric_schema import RubricV2
from v2.judge import ConceptJudge, EvaluationMode
from v2.scoring import compute_grade

ASSIGNMENT_DIR = Path("assignments/my_assignment")
RUBRICS_DIR    = ASSIGNMENT_DIR / "rubrics"
ANSWERS_DIR    = ASSIGNMENT_DIR / "answers"
GRADES_DIR     = ASSIGNMENT_DIR / "grades"
GRADES_DIR.mkdir(exist_ok=True)

# Load questions index (for question_text lookup)
questions = {q["question_id"]: q for q in
             json.loads((ASSIGNMENT_DIR / "questions.json").read_text())}

# Load rubrics
rubrics = {}
for rubric_file in RUBRICS_DIR.glob("*.json"):
    rubric = RubricV2.model_validate_json(rubric_file.read_text())
    rubrics[rubric.question_id] = rubric

llm   = configure_llm_for_tier("foundational")
judge = ConceptJudge(llm=llm, mode=EvaluationMode.SINGLE)

for answer_file in sorted(ANSWERS_DIR.glob("*.json")):
    student_data = json.loads(answer_file.read_text())
    student_id   = student_data["student_id"]
    print(f"\n=== Grading {student_id} ===")

    for qid, answer_text in student_data["answers"].items():
        out = GRADES_DIR / f"{student_id}_{qid}.json"
        if out.exists():
            print(f"  {qid}: already graded, skipping.")
            continue

        if qid not in rubrics:
            print(f"  {qid}: no rubric found, skipping.")
            continue

        rubric = rubrics[qid]

        # Retrieve relevant context for this answer
        evidence_context = retrieve_context(
            query=answer_text,
            index_dir=str(ASSIGNMENT_DIR / "index"),
            top_k=3,
        )

        # Judge the answer
        check_evals = judge.evaluate(
            answer_text=answer_text,
            rubric=rubric,
            evidence_context=evidence_context,
        )

        # Compute grade
        grade = compute_grade(
            grade_id=f"{student_id}_{qid}",
            question_id=qid,
            student_id=student_id,
            rubric=rubric,
            check_evaluations=check_evals,
        )

        # Save grade record
        out.write_text(json.dumps(grade.model_dump(mode="json"), indent=2))
        print(f"  {qid}: {grade.final_score:.1f}/10")

print("\nGrading complete.")
```

Run it:

```bash
python scripts/grade_students.py
```

This produces `grades/student_001_q01.json`, `grades/student_001_q02.json`, etc.

---

## Step 6 — Generate Student Feedback

The grade records contain raw scores and per-check evaluations. This step transforms them into human-readable feedback JSON files that include improvement suggestions.

```python
# scripts/generate_feedback.py
import json
from pathlib import Path

from config.llm_config import configure_llm_for_tier
from v2.models import GradeV2, RubricV2, PrecisionLevel

ASSIGNMENT_DIR = Path("assignments/my_assignment")
RUBRICS_DIR    = ASSIGNMENT_DIR / "rubrics"
GRADES_DIR     = ASSIGNMENT_DIR / "grades"
FEEDBACK_DIR   = ASSIGNMENT_DIR / "feedback"
FEEDBACK_DIR.mkdir(exist_ok=True)

questions = {q["question_id"]: q for q in
             json.loads((ASSIGNMENT_DIR / "questions.json").read_text())}

rubrics = {}
for f in RUBRICS_DIR.glob("*.json"):
    r = RubricV2.model_validate_json(f.read_text())
    rubrics[r.question_id] = r

llm = configure_llm_for_tier("foundational")

def build_feedback(grade: GradeV2, rubric: RubricV2, question: dict) -> dict:
    """Build a structured feedback record from a grade."""

    # Map check_id → ConceptCheck for lookup
    check_map = {c.check_id: c for crit in rubric.criteria for c in crit.checks}

    checks_detail = []
    for ev in grade.check_evaluations:
        check = check_map.get(ev.check_id)
        if check is None:
            continue
        checks_detail.append({
            "check_id":    ev.check_id,
            "concept":     check.concept,
            "check_type":  check.check_type,
            "precision":   ev.precision,
            "score":       ev.score,
            "points_available": check.points,
            "points_earned":    ev.score * check.points,
            "rationale":   ev.rationale,
            "what_full_looks_like": check.precision_levels[PrecisionLevel.FULL],
        })

    # Ask LLM for an improvement suggestion
    missed = [c for c in checks_detail if c["precision"] != "full"]
    suggestion = ""
    if missed:
        missed_concepts = "\n".join(f"  - {c['concept']} ({c['precision']})" for c in missed)
        prompt = (
            f"A student answered the following question:\n"
            f"Q: {question['question_text']}\n\n"
            f"A: (answer not shown)\n\n"
            f"They did not fully address these concepts:\n{missed_concepts}\n\n"
            "Write 2–3 sentences of constructive feedback telling the student "
            "specifically what to add or clarify to improve their answer. "
            "Do not repeat the question. Be concrete and encouraging."
        )
        suggestion = llm.complete(prompt).text.strip()

    return {
        "grade_id":      grade.grade_id,
        "student_id":    grade.student_id,
        "question_id":   grade.question_id,
        "question_text": question["question_text"],
        "final_score":   grade.final_score,
        "max_score":     10.0,
        "raw_score":     grade.raw_score,
        "evaluation_mode": grade.evaluation_mode,
        "model_tier":    grade.model_tier,
        "rubric_id":     grade.rubric_id,
        "rubric_version": grade.rubric_version,
        "checks": checks_detail,
        "improvement_suggestion": suggestion,
        "graded_at": grade.graded_at.isoformat(),
    }


for grade_file in sorted(GRADES_DIR.glob("*.json")):
    grade = GradeV2.model_validate_json(grade_file.read_text())
    qid   = grade.question_id
    sid   = grade.student_id

    out = FEEDBACK_DIR / f"{sid}_{qid}.json"
    if out.exists():
        print(f"{sid}/{qid}: feedback exists, skipping.")
        continue

    if qid not in rubrics or qid not in questions:
        print(f"{sid}/{qid}: missing rubric or question, skipping.")
        continue

    feedback = build_feedback(grade, rubrics[qid], questions[qid])
    out.write_text(json.dumps(feedback, indent=2))
    print(f"{sid}/{qid}: {grade.final_score:.1f}/10 → {out.name}")

print("\nFeedback generation complete.")
```

Run it:

```bash
python scripts/generate_feedback.py
```

---

## Output Structure

After all steps, your directory looks like:

```
assignments/my_assignment/
  source_materials/           ← your original input (unchanged)
  questions.json              ← your original input (unchanged)
  answers/
    student_001.json          ← your original input (unchanged)
    student_002.json
  index/                      ← built in Step 2 (vector index)
  rubrics/
    q01.json                  ← generated in Step 4
    q02.json
  grades/
    student_001_q01.json      ← generated in Step 5
    student_001_q02.json
    student_002_q01.json
    ...
  feedback/
    student_001_q01.json      ← generated in Step 6  ← final output
    student_001_q02.json
    student_002_q01.json
    ...
```

### Example feedback file: `feedback/student_001_q01.json`

```json
{
  "grade_id": "student_001_q01",
  "student_id": "student_001",
  "question_id": "q01",
  "question_text": "Why can't you compute ratios on a Celsius temperature scale?",
  "final_score": 6.67,
  "max_score": 10.0,
  "raw_score": 0.667,
  "evaluation_mode": "single",
  "model_tier": "foundational",
  "rubric_id": "q01_v2",
  "rubric_version": 2,
  "checks": [
    {
      "check_id": "c1",
      "concept": "interval scale zero is arbitrary (not absence of quantity)",
      "check_type": "definition",
      "precision": "full",
      "score": 1.0,
      "points_available": 1.0,
      "points_earned": 1.0,
      "rationale": "Student explicitly states zero is the freezing point of water and not the absence of heat.",
      "what_full_looks_like": "Names the convention (freezing point) and states it does not represent absence of heat"
    },
    {
      "check_id": "c2",
      "concept": "arbitrary zero makes ratio operations meaningless",
      "check_type": "mechanism",
      "precision": "partial",
      "score": 0.5,
      "points_available": 2.0,
      "points_earned": 1.0,
      "rationale": "Student gives the 20°C/10°C example but does not explain the causal chain — why the arbitrary zero is what breaks the ratio.",
      "what_full_looks_like": "Explains the causal chain: arbitrary zero → no common reference → ratio depends on choice of zero → ratio is undefined"
    },
    {
      "check_id": "c3",
      "concept": "contrast with ratio scale where zero means absence",
      "check_type": "distinction",
      "precision": "none",
      "score": 0.0,
      "points_available": 1.0,
      "points_earned": 0.0,
      "rationale": "No mention of ratio scales or what a valid zero would look like (e.g. Kelvin).",
      "what_full_looks_like": "Names a ratio scale (e.g. Kelvin or mass) and explains that its zero represents actual absence"
    }
  ],
  "improvement_suggestion": "Your answer correctly identifies that zero on the Celsius scale is the freezing point of water rather than the absence of heat — that is the key insight. To strengthen it, explain *why* this matters for ratios: because the zero is a convention, doubling the number does not double the physical quantity, so ratios give different results depending on which zero you choose. Consider contrasting Celsius with Kelvin, where zero does represent the absence of thermal energy, making ratio statements like '200K is twice as hot as 100K' physically meaningful.",
  "graded_at": "2026-03-31T14:22:05.123456"
}
```

---

## Troubleshooting

### `GOOGLE_API_KEY` not found
Make sure you exported the variable in the same shell session you're running Python from. Run `echo $GOOGLE_API_KEY` to verify.

### Rubric check says "mentions the word X"
The rubric generator drifted into vocabulary matching. Re-run `generate_rubrics.py` for that question (delete the old `rubrics/qNN.json` first). If it happens repeatedly, add to the prompt: "Every check must test concept presence, not word choice."

### `CriterionV2` validation error: points mismatch
The LLM returned a rubric where `criterion.points` ≠ sum of check points. `parse_rubric_response` will reject it. The `RubricGeneratorV2` retries automatically (if you add retry logic), or re-run the script.

### Karpathy loop never converges
Increase `max_iterations` in `config/rubric_generation.yaml`, or switch to `model_tier: foundational` if you were using `oss`. A stronger model generates more discriminating checks.

### All students score 0
Check that `judge.evaluate()` is returning non-empty `check_evaluations`. If the list is empty, `compute_grade` returns 0 because `total_points == 0`. This usually means the judge prompt is malformed or the LLM returned unparseable JSON.

---

## Quick Reference

| Step | Script | Input | Output |
|------|--------|-------|--------|
| 1 | — | your files | organised `assignments/` folder |
| 2 | `python -c "..."` | `source_materials/` | `index/` |
| 3 | edit YAML | — | `config/rubric_generation.yaml` |
| 4 | `generate_rubrics.py` | `questions.json`, `index/` | `rubrics/qNN.json` |
| 5 | `grade_students.py` | `answers/`, `rubrics/` | `grades/sNNN_qNN.json` |
| 6 | `generate_feedback.py` | `grades/`, `rubrics/` | `feedback/sNNN_qNN.json` |
