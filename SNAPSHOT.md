# SNAPSHOT — autograder

*Last updated: 2026-05-11 12:47*

## Purpose

LLM-based autograder for short-answer assignments. Retrieves evidence from indexed
student submissions, applies YAML-defined rubrics, and produces structured grade records.

## Scripts / Components

- `grading_pipeline/cli.py` — CLI args, backend selection plumbing
- `grading_pipeline/pipeline.py` — Grading flow + backend-aware index setup
- `retrieval_core/retriever.py` — Dual-index retrieval + reranker with optional tracing
- `retrieval_core/multi_retriever.py` — Multi-index retrieval + reranker with optional tracing
- `grading_pipeline/index_builder.py` — ChromaDB indexing + incremental updates
- `grading_pipeline/index_builder_in_memory.py` — In-memory indexing + pickle persistence
- `grading_dynamic_rubrics/pipeline.py` — Dynamic rubrics pipeline (YAML-driven retrieval)
- `gp/create_dynamic_rubrics_for_each_question.py` — LLM-based dynamic rubric generation
- `gp/rubric_schema.py` — Pydantic models for rubric validation
- `tests/` — pytest suite covering all pipeline modules

## Output structure

- `rubrics/` — YAML rubrics (authoritative)
- `rubrics_dynamic/` — LLM-generated rubrics (JSON + YAML)
- `data/grades/` — Grade records
- `logs/` — grading.log + transparency.log (per run)

## Key design decisions

- Dual index backends: ChromaDB (persistent) or in-memory pickle
- Transparency tracing (`--transparent`) writes to `logs/transparent.log`
- Dynamic rubrics retrieval parameters are YAML-driven (`sources.yaml`)
- Pydantic validation with retry logic for LLM-generated rubrics
- `.git` now lives at `autograder/.git` (repo root); no `-C` flag needed for git commands

## TODO

- Remove parent `.git` backup at `../grading_assessment/.git` when no longer needed
