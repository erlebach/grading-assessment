# Autograder

Automatic Grading System

This repository implements a rubric-driven, evidence-constrained automatic grading system for explanatory and code-based assessments.

Grades are assigned deterministically from explicit rubrics using admissible evidence sources. Large language models are used only to assist with evidence matching and feedback generation; they do not define grading policy or scoring criteria.

## Core Invariants

- Rubrics define grading law.
- Evidence must come from explicitly allowed sources.
- Grades are assigned before feedback is generated.
- Feedback is determined by **(grade × rubric)** and cited evidence.
- Internal model reasoning is transient and non-authoritative.

## Grading Workflow

1. Student submits an answer.
2. Admissible evidence is retrieved and ranked.
3. Rubric-driven internal reasoning evaluates criteria.
4. Grades are assigned per rubric dimensions.
5. Feedback is generated to explain assigned grades, with citations.

## Scope

### Supported
- Explanatory justifications
- Multi-dimensional rubric scoring
- Batch, CLI-based grading
- Citation-linked feedback

### Out of Scope
- Implicit or prompt-based grading
- Use of external world knowledge
- Plagiarism detection
- Auto-modification of rubrics

## Installation

```bash
uv venv
source .venv/bin/activate
uv sync
```

## Usage

### Grade a single question

```bash
python -m cli.grade_batch --question q01 --submission path/to/submission.py
```

### Grade a batch of submissions

```bash
python -m cli.grade_batch --question q01 --submissions-dir path/to/submissions/
```

## Project Structure

- `grader/` - Core grading logic and pipeline
- `rubrics/` - YAML rubric definitions
- `evidence/` - RAG index configuration and building
- `prompts/` - Prompt templates for grading and explanations
- `cli/` - Command-line interface
- `docs/` - Design documentation and architecture decision records
- `tests/` - Test suite

## Development

See `docs/DESIGN.md` for architectural details and `docs/adr/` for decision records.
