# Rubric Generation Plan (Standalone Project)

**Date**: 2026-01-25
**Session ID**: 2026-01-25_session01
**Status**: Design Phase - Ready for Later Implementation
**Related Project**: Weighted Checklist Grading System (separate)

---

## Executive Summary

This plan describes **rubric generation as a standalone, decoupled project** that produces clean rubric artifacts for use by the grading system.

**Key Principle:** Rubric generation and grading are separate concerns. Rubrics can be:
- Generated manually using ChatGPT-Plus/Claude/Gemini (offline)
- Generated via automated ensemble pipeline (in-process)
- Created by humans and version-controlled as JSON artifacts
- Reviewed and refined iteratively before being fed to the grading system

**Output of this project:** Clean, deduplicated rubric JSON files ready for the grading system.

---

## Architecture & Context

### Integration Point
```
This Project (Rubric Generation)
    ↓
    Produces: rubric_q01.json, rubric_q02.json, ...
    ↓
Weighted Checklist Grading System (separate project)
    ↓
    Consumes: rubric JSON files
    Produces: Grades with audit trail
```

**Important:** The grading system does NOT depend on how rubrics are generated. It only depends on the final rubric JSON format.

---

## Approach 1: Manual Generation (Immediate, Ad-Hoc)

### **Workflow: ChatGPT-Plus / Claude / Gemini Sessions**

**When to use:** For creating 1-5 rubrics, with human oversight

**Process:**

```
Step 1: Open ChatGPT-Plus / Claude / Gemini

Step 2: Paste into prompt:
  ---
  Question: [question text]

  Source Material:
  [Full slides/textbook text - complete context]

  Generate a rubric for grading student answers to this question.

  Requirements:
  1. 2-5 dimensions (criteria) assessing DISTINCT, NON-OVERLAPPING aspects
  2. Each dimension worth 1-5 points (total = 10)
  3. Each dimension has:
     - Clear title
     - Description (prescriptive: what full credit looks like, specific deductions)

  Format as JSON:
  {
    "dimensions": [
      {
        "dimension_id": "...",
        "title": "...",
        "points": N,
        "description": "..."
      }
    ]
  }
  ---

Step 3: Review LLM output
  - Are dimensions distinct and non-overlapping?
  - Are descriptions clear and prescriptive?
  - Do points sum to 10?

Step 4: Refine
  - Ask LLM: "Please revise dimension X to not overlap with dimension Y"
  - Adjust point allocations if needed
  - Clarify descriptions

Step 5: Export
  - Copy final JSON into file: rubrics/q01.json
  - Store complete transcript for reference
```

**Advantages:**
- ✅ Manual oversight → higher quality
- ✅ Interactive refinement → iterate until satisfied
- ✅ Works immediately (no pipeline needed)
- ✅ Can use any model (ChatGPT, Claude, Gemini, local)
- ✅ Full context without token limits
- ✅ No infrastructure needed

**Disadvantages:**
- ❌ Manual for each question
- ❌ Not reproducible (different sessions produce different rubrics)
- ❌ Human time intensive

**Effort per question:** 15-30 minutes (generation + review + refinement)

**Total for 10 questions:** 2.5-5 hours

---

## Approach 2: Automated Ensemble Pipeline

### **Workflow: Multi-Generation with Consensus**

**When to use:** For batch generation (5+ questions) with quality guarantee

**Process:**

```
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: Generate Rubric Multiple Times (Ensemble)           │
├─────────────────────────────────────────────────────────────┤
│ For each question Q:                                         │
│   Generate rubric N times (N = 3-5)                          │
│   Result: [Rubric_1, Rubric_2, Rubric_3, ...]              │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: Extract Checks from All Rubrics                     │
├─────────────────────────────────────────────────────────────┤
│ For each generated rubric:                                   │
│   Extract discrete checks from dimension descriptions       │
│   Result: [Checks_1, Checks_2, Checks_3, ...]              │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: Identify Common Checks (Consensus)                  │
├─────────────────────────────────────────────────────────────┤
│ Use LLM to determine:                                        │
│   "Which checks appear in multiple rubrics?"                │
│   "Are they semantically equivalent?"                        │
│                                                              │
│ Scoring: Weight by agreement                                │
│   Check appears in 3/3 rubrics → weight = 3 (high conf.)   │
│   Check appears in 2/3 rubrics → weight = 2 (med conf.)    │
│   Check appears in 1/3 rubrics → weight = 1 (low conf.)    │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 4: Filter by Confidence Threshold                      │
├─────────────────────────────────────────────────────────────┤
│ Keep only checks with agreement ≥ threshold                 │
│   Default threshold: 2/3 (majority agreement)               │
│   Configurable: min_agreement: 2                            │
│                                                              │
│ Result: High-confidence checks only                         │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 5: Reconstruct Rubric Dimensions                       │
├─────────────────────────────────────────────────────────────┤
│ Group checks by original dimensions                         │
│ Recalculate points based on agreement                       │
│ Preserve non-overlapping requirement                        │
│                                                              │
│ Result: Final rubric with consensus backing                │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 6: Store with Metadata                                 │
├─────────────────────────────────────────────────────────────┤
│ Store final rubric WITH:                                    │
│   - agreement counts for each check                         │
│   - all N intermediate rubrics (for audit)                  │
│   - consensus metadata                                      │
└─────────────────────────────────────────────────────────────┘
```

**Configuration:**
```yaml
rubric_generation:
  ensemble:
    enabled: true
    num_generations: 3  # Generate 3 rubrics
    min_agreement: 2    # Keep if appears in ≥2 rubrics
    weight_by_agreement: true  # Score checks by agreement count

  generation:
    temperature: 0.7  # Some variety (default: 0.7)
    max_retries: 2    # Retry if parsing fails
```

**LLM Prompts:**

**Prompt 1: Generate Rubric**
```
Question: {question_text}

Source Material:
{full_context}

Generate a rubric for grading student answers with:
- 2-5 dimensions (DISTINCT, NON-OVERLAPPING)
- Total 10 points
- Prescriptive descriptions (deductions for specific omissions)

Format as JSON: {...}
```

**Prompt 2: Extract Checks**
```
Rubric dimensions:
{dimension_descriptions}

Extract 3-5 discrete checks from these dimensions.
Each check should be:
- Atomic (one evaluatable item)
- Distinct from other checks
- Evaluatable from student answer

Format: JSON with check_id, text, source_dimension, base_weight
```

**Prompt 3: Identify Common Checks**
```
I have extracted checks from N rubrics for the same question.

Rubric 1 checks: {checks_1}
Rubric 2 checks: {checks_2}
Rubric 3 checks: {checks_3}

For each check, determine:
1. Is it semantically equivalent to any check in other rubrics?
2. If yes, which rubric(s) contain it?

Output JSON with agreement counts.
```

**Advantages:**
- ✅ Reduces LLM hallucinations
- ✅ Consensus backing (higher confidence)
- ✅ Fully automated
- ✅ Reproducible (same input → same output)
- ✅ Can weight checks by agreement
- ✅ Audit trail (all N rubrics stored)

**Disadvantages:**
- ❌ N times more LLM calls (cost)
- ❌ N times more latency
- ❌ Requires orchestration pipeline

**Cost:** 3 calls per question (not 1), so ~3× cost

**Effort:** Implementation complexity, but runtime minimal once deployed

---

## Approach 3: Decomposition Strategies

### **Strategy 1: Question Decomposition (Recommended)**

**Process:**
```
Step 1: Identify Dimensions
  Question: "Define objects and attributes in data mining"
  LLM: "What are the key learning objectives?"
  → [Conceptual Understanding, Terminology, Application, Clarity]

Step 2: Generate Rubric for Each Dimension
  Dimension 1 (Conceptual): "Student understands object/attribute distinction"
  Dimension 2 (Terminology): "Student knows alternative names"
  Dimension 3 (Application): "Student applies concepts with examples"
  Dimension 4 (Clarity): "Answer is clear and well-structured"

Step 3: Assign Points
  Conceptual: 4 points
  Terminology: 3 points
  Application: 2 points
  Clarity: 1 point
  Total: 10 points

Step 4: Create Integrated Rubric
  Combine all dimensions into single JSON rubric
```

**Advantages:**
- ✅ Explicit dimensions → easy to understand
- ✅ Reusable dimensions (use "Terminology" across questions)
- ✅ Clear separation of concerns
- ✅ Easy to adjust weights (change points per dimension)
- ✅ Easy for students to understand what's evaluated

**Disadvantages:**
- ❌ More steps = more LLM calls
- ❌ Risk of redundancy across dimensions

**Effort:** 2-3 LLM calls per question (identify dimensions, then rubric per dimension)

### **Strategy 2: Integrated Generation (Simpler)**

**Process:**
```
Single Step: Question + Context → Rubric with Dimensions
  LLM generates complete rubric in one call
  All dimensions in one holistic rubric
```

**Advantages:**
- ✅ Fewer LLM calls
- ✅ LLM sees big picture (naturally avoids overlaps)
- ✅ Faster

**Disadvantages:**
- ❌ Less explicit structure
- ❌ Harder to reuse dimensions

**Recommendation:** Use **Strategy 1 (Question Decomposition)** because:
- Better structure and reusability
- Explicit dimensions help prevent overlaps
- Only 1-2 extra LLM calls worth the clarity gain

---

## Approach 4: Context Inclusion vs RAG

### **Context Inclusion (Full Text in Prompt)**

**When to use:** Small context (slides, short textbook)

**Process:**
```
Paste entire context into single prompt:
  Question: {q}
  Source: {FULL SLIDES/TEXT}
  Generate rubric...
```

**Advantages:**
- ✅ No retrieval errors
- ✅ LLM sees complete context
- ✅ No network latency
- ✅ Works offline
- ✅ Deterministic (same input → same LLM behavior)
- ✅ Fully reproducible

**Disadvantages:**
- ❌ Token limit (context must fit in window)
- ❌ More expensive (more tokens)
- ❌ Can be noisy (irrelevant parts included)

**Token budget:** ~4000 tokens for context = ~2000 words
- Typical slides: 5-20 pages = 5000-15000 words (might exceed)
- Typical chapter: 10-50 pages = too large

### **RAG (Retrieval-Augmented Generation)**

**When to use:** Large context (textbooks, multi-chapter materials)

**Process:**
```
Question: "Define objects and attributes"
  ↓
Retrieval: Find 2-3 most relevant passages
  Passage 1: "Objects are collections of related data..."
  Passage 2: "Attributes describe properties of objects..."
  Passage 3: "Alternative names include field, column, property..."
  ↓
Combined: Question + passages
  ↓
Generate: Rubric based on retrieved content
```

**Advantages:**
- ✅ Handles large documents
- ✅ More cost-efficient (fewer tokens)
- ✅ Cleaner context (only relevant parts)
- ✅ Scales to large sources

**Disadvantages:**
- ❌ Retrieval can miss important context
- ❌ More moving parts (retrieval pipeline)
- ❌ Non-deterministic (retrieval results vary)
- ❌ Risk of retrieval errors affecting quality

**Recommendation:** For this project, use **Context Inclusion** because:
- Slides are typically small (~10-20 pages)
- Token limits are manageable
- Quality is more important than cost
- Reproducibility matters for rubrics
- Rubrics are one-time creation (cost not critical)

**Implementation:** If context too large, use RAG but document carefully.

---

## Approach 5: Question-Rubric Co-Evolution (Iterative Refinement)

### **Workflow: Iterative Question & Rubric Refinement**

**When to use:** When question and rubric should be tightly aligned; when question wording needs clarification to match grading dimensions

**Key Insight:** The question we ask should match what we grade. This approach co-evolves the question and rubric together.

**Process:**

```
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: Initial Question                                    │
├─────────────────────────────────────────────────────────────┤
│ Start with original question text                            │
│ Example: "Explain objects and attributes in data mining"    │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: Generate Rubric Dimensions (from question + context)│
├─────────────────────────────────────────────────────────────┤
│ Input:                                                       │
│   - Question text                                           │
│   - Source material (slides/textbook)                       │
│   - Model: foundational LLM (could be smaller/faster)       │
│                                                              │
│ Output: Rubric dimensions                                   │
│   Dimension 1: "Conceptual Distinction"                     │
│   Dimension 2: "Alternative Terminology"                    │
│   Dimension 3: "Precision of Definitions"                   │
│   Dimension 4: "Clarity & Examples"                         │
│                                                              │
│ These dimensions define WHAT we grade for                   │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: Identify & Remove Duplicates                        │
├─────────────────────────────────────────────────────────────┤
│ Check for overlapping dimensions                            │
│ Example: "Conceptual Distinction" and "Precision..."        │
│   Could overlap on definitional precision                   │
│                                                              │
│ Use LLM: "Do these dimensions overlap? If yes, refactor"   │
│                                                              │
│ Result: Clean, non-overlapping dimensions                  │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 4: Reformulate Question for Dimension Alignment        │
├─────────────────────────────────────────────────────────────┤
│ For each dimension in the rubric:                            │
│   "What part of the question solicits this dimension?"      │
│                                                              │
│ If dimension has no corresponding question part:            │
│   Reformulate question to explicitly ask for it             │
│                                                              │
│ Example:                                                    │
│   Original: "Explain objects and attributes in data mining" │
│   Reformulated: "Define 'object' and 'attribute' in data    │
│                  mining, providing alternative terminology, │
│                  exact definitions, and concrete examples.   │
│                  Clearly distinguish objects from attributes"│
│                                                              │
│ Result: Question now elicits all rubric dimensions         │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 5: Validate Alignment                                  │
├─────────────────────────────────────────────────────────────┤
│ Check: Does reformed question clearly ask for all grading   │
│        dimensions?                                           │
│                                                              │
│ Use LLM: "For each rubric dimension, which part of the     │
│          question solicits it? Are all dimensions covered?" │
│                                                              │
│ If misalignment found:                                       │
│   → Adjust rubric dimensions (back to STEP 3) OR           │
│   → Further reformulate question (back to STEP 4)           │
│                                                              │
│ Continue until alignment achieved (typically 1-2 iterations)│
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 6: Finalize Rubric with Context                        │
├─────────────────────────────────────────────────────────────┤
│ Generate final rubric using:                                │
│   - Refined question text                                   │
│   - Clean dimensions (after deduplication)                  │
│   - Full context material                                   │
│                                                              │
│ Result: Final rubric where each dimension is clearly        │
│         solicited by the reformulated question             │
└─────────────────────────────────────────────────────────────┘
```

**Example: Q01 Evolution**

**Original Question:**
```
"Explain objects and attributes in data mining"
```

**Generated Dimensions:**
1. Conceptual Distinction (object vs attribute)
2. Alternative Terminology (field, column, property, etc.)
3. Precision of Definitions (exact meaning)
4. Clarity & Examples (clear communication)
5. Structural Understanding (collection metaphor)

**After Deduplication:**
- Removed: "Precision of Definitions" (overlaps with Conceptual Distinction)
- Kept: 1, 2, 3, 4 (Clarity includes explanation quality)

**Wait, Precision actually needed?** Reconsider: Precision = exact definitions + attribute values mentioned
- This is distinct from Conceptual (which is about distinguishing concepts)
- So keep it: Dimensions are now 1, 2, 3, 4

**Reformulated Question:**
```
"Define 'object' and 'attribute' in data mining.
- Clearly distinguish them from each other (with examples like objects = rows, attributes = columns)
- Provide alternative names for 'object' and 'attribute' (e.g., entity, field, column, property)
- Be precise: specify what values an attribute has and that objects are collections
- Structure your answer clearly with examples"
```

**Validation:**
- Q1: "Define..." → Dimension 1 (Conceptual Distinction) ✓
- Q1: "alternative names..." → Dimension 2 (Alternative Terminology) ✓
- Q1: "precisely specify..." → Dimension 3 (Precision) ✓
- Q1: "structure clearly..." → Dimension 4 (Clarity) ✓

**Result:** Question and rubric now perfectly aligned.

---

### **Advantages:**

- ✅ **Perfect alignment:** Question solicits exactly what rubric grades
- ✅ **Clearer expectations:** Students know exactly what's expected
- ✅ **Reduced ambiguity:** Explicit question wording eliminates interpretation issues
- ✅ **Better grading:** Rubric dimensions directly map to question parts
- ✅ **Fairer assessment:** All dimensions are equally solicited by question
- ✅ **Works with all methods:** Can combine with ensemble or manual approaches
- ✅ **Documentation:** Reformulation process documents rubric intent
- ✅ **Iterative:** Can refine multiple times if needed

### **Disadvantages:**

- ❌ **Question text changes:** Original question is reformulated (intentional, not a bug)
- ⚠️ **Intentional ambiguity loss:** If question was deliberately ambiguous for pedagogical reasons, reformulation makes it explicit

### **When to Use:**

- ✅ **New assessments:** Creating question + rubric together
- ✅ **Ambiguous questions:** Questions that could be interpreted multiple ways
- ✅ **Rubric-first design:** When you define rubric dimensions first, then craft question to match
- ✅ **High-stakes assessments:** Where alignment is critical
- ✅ **Quality improvement:** Refining existing questions that don't align with grading dimensions

### **When NOT to Use:**

- ❌ **Fixed questions:** When question text cannot be changed
- ❌ **Already-administered questions:** Changing question after students answered is unfair
- ❌ **Quick rubrics:** When speed is more important than perfect alignment

### **Effort:**

**Rubric generation is one-time, amortized work:**
- Done once per question
- Used for grading all students across all years
- LLM calls and latency are not significant constraints (LLMs getting faster, work can be batched)

**Process steps:**
- Dimension generation from question + context
- Deduplication/overlap detection
- Question reformulation (with length constraint)
- Alignment validation
- Final rubric generation

---

### **Implementation Notes:**

**Phase 2 Addition:** Add to Phase 2 (Manual Support)
- New template: "Question-Rubric Co-Evolution Worksheet"
- Guides manual step-by-step process
- Shows how to identify dimensions and reformulate question

**Phase 3 Enhancement:** Add to Phase 3 (Automated Pipeline)
- New pipeline step: Co-evolution module
- Can run as post-processing on ensemble rubrics
- Takes any rubric + question, reformulates question for alignment
- Implementation can batch/combine steps as needed

**Configuration Option:**
```yaml
rubric_generation:
  co_evolution:
    enabled: true              # Enable question reformulation
    auto_reformulate: true     # Auto-reformulate or suggest only
    deduplication_threshold: 0.7  # LLM similarity threshold for overlaps
    max_iterations: 2          # Max refinement iterations before finalizing
```

---

## Hybrid Approach (Recommended)

Combine approaches based on situation:

```
For Ad-Hoc Rubrics (1-3 questions):
  → Manual generation via ChatGPT-Plus
  → One-time investment per question
  → High quality via interactive refinement
  → Optional: Add Question-Rubric Co-Evolution for perfect alignment

For Batch Rubrics (5-10 questions):
  → Automated ensemble pipeline
  → One-time setup cost
  → Reproducible, confidence-backed rubrics
  → Optional: Run co-evolution post-processing on ensemble output

For New Assessment Design (questions + rubrics together):
  → Use Question-Rubric Co-Evolution from the start
  → Ensures perfect question-rubric alignment
  → Can combine with ensemble for quality + alignment

Always:
  → Use full context inclusion (not RAG)
  → Use question decomposition strategy
  → Consider Question-Rubric Co-Evolution for alignment
  → Version control rubrics as JSON (with reformulated question)
  → Store audit trail (intermediate rubrics + original/reformulated questions)
  → Document all iterations (original question → final rubric + reformulated question)
```

---

## Implementation Plan

### **Phase 1: Infrastructure** (2-3 days)

#### T1.1: Define Rubric JSON Schema
- Pydantic model for rubric format
- JSON schema for validation
- Version tracking

#### T1.2: Create Prompt Templates
- Template for manual sessions (ChatGPT-Plus/Claude)
- Template for automated generation
- Template for check extraction
- Template for consensus detection

#### T1.3: Set Up Version Control
- Directory structure: `rubrics/`
- Git ignore rules
- Metadata storage (intermediate rubrics, audit trail)

### **Phase 2: Manual Generation Support** (1-2 days)

#### T2.1: Create Prompt Kits
- Copy-paste ready prompts for ChatGPT-Plus/Claude/Gemini
- Instructions for manual workflow
- Checklist for review/refinement

#### T2.2: Create Export/Import Tools
- Import JSON from manual sessions
- Validate format
- Store in version control

### **Phase 3: Automated Ensemble Pipeline** (1-2 weeks)

#### T3.1: Implement Multi-Generation
- Call LLM N times per question
- Store all N rubrics

#### T3.2: Implement Check Extraction
- Parse all rubrics
- Extract checks from descriptions

#### T3.3: Implement Consensus Detection
- LLM analyzes all checks
- Identifies common/duplicate checks
- Weights by agreement

#### T3.4: Implement Filtering & Reconstruction
- Filter by confidence threshold
- Reconstruct dimensions
- Final rubric with metadata

### **Phase 3b: Question-Rubric Co-Evolution Module** (1 week)

#### T3b.1: Implement Dimension Generation
- Extract rubric dimensions from question + context
- Format for validation and manual review

#### T3b.2: Implement Deduplication Detection
- LLM analyzes dimension overlap
- Identifies and suggests fixes
- Returns clean dimension set

#### T3b.3: Implement Question Reformulation
- For each dimension, check question alignment
- Generate reformulated question that solicits all dimensions
- Track original vs reformulated versions

#### T3b.4: Implement Alignment Validation
- Validate reformulated question covers all dimensions
- Support iterative refinement (up to max_iterations)
- Return alignment report

#### T3b.5: Integrate Co-Evolution as Pipeline Stage
- Can run as post-processing on ensemble output
- Can run standalone (question → rubric → reformulated question)
- Optional flag to enable/disable in configuration

### **Phase 4: Testing & Validation** (1 week)

#### T4.1: Manual Testing
- Generate 3-5 rubrics manually
- Compare quality
- Refine process

#### T4.2: Automated Testing
- Generate rubrics with pipeline
- Compare N generations
- Validate consensus detection
- Verify reproducibility

#### T4.3: Integration Testing
- Output rubrics ready for grading system
- Validate format
- Test with grading pipeline

---

## Configuration Template

```yaml
# Rubric Generation Configuration
rubric_generation:
  # Generation method: "manual", "ensemble", or "integrated"
  method: "ensemble"

  # For manual method: provide prompts
  manual:
    model_provider: "anthropic"  # ChatGPT, Claude, Gemini
    model_name: "claude-3-sonnet"
    context_inclusion: true  # Full text vs RAG

  # For automated ensemble
  ensemble:
    enabled: true
    num_generations: 3
    temperature: 0.7
    max_retries: 2

  # Check consensus
  consensus:
    min_agreement: 2  # Out of num_generations
    weight_by_agreement: true

  # Question decomposition
  decomposition:
    strategy: "question_decomposition"  # or "integrated"
    max_dimensions: 5
    point_allocation: "automatic"  # or "manual" (user specifies)

  # Context handling
  context:
    method: "inclusion"  # "inclusion" or "rag"
    max_tokens_context: 4000
    rag:
      enabled: false
      chunk_size: 500
      top_k: 3

  # Question-Rubric Co-Evolution (new)
  co_evolution:
    enabled: false              # Enable co-evolution by default
    auto_reformulate: true      # Auto-reformulate or suggest only
    deduplication_threshold: 0.7  # LLM similarity threshold (0.0-1.0)
    max_iterations: 2           # Max refinement iterations for alignment
    store_versions: true        # Store original + reformulated questions
    alignment_report: true      # Generate alignment validation report

  # Output
  output:
    store_intermediates: true  # Store all N generations
    audit_trail: true
    version_control: true
    include_question_evolution: true  # Include original→reformulated in output
```

---

## Expected Artifacts

### **Per Question:**

```
rubrics/
├── q01/
│   ├── q01.json                    (final rubric)
│   ├── q01_metadata.json           (agreement counts, etc.)
│   ├── q01_question_original.txt   (original question)
│   ├── q01_question_reformulated.txt (if co-evolution enabled)
│   ├── q01_alignment_report.json   (co-evolution alignment validation)
│   ├── intermediates/
│   │   ├── q01_gen_1.json         (rubric generation 1)
│   │   ├── q01_gen_2.json         (rubric generation 2)
│   │   ├── q01_gen_3.json         (rubric generation 3)
│   │   ├── q01_checks_1.json      (checks extracted from gen 1)
│   │   ├── q01_checks_2.json      (checks extracted from gen 2)
│   │   ├── q01_checks_3.json      (checks extracted from gen 3)
│   │   ├── q01_dimensions_extracted.json    (extracted from question, pre-dedup)
│   │   ├── q01_dimensions_deduplicated.json (after overlap removal)
│   │   └── q01_coevolution_iterations/     (if multiple refinement iterations)
│   │       ├── iteration_1.json
│   │       ├── iteration_2.json
│   │       └── ...
│   └── session_transcript.md      (if manual: ChatGPT log)
├── q02/
└── ...
```

### **Final Rubric Format:**

```json
{
  "question_id": "q01",
  "question_text": "...",
  "generation_method": "ensemble",
  "question_evolution": {
    "original_question": "Explain objects and attributes in data mining",
    "reformulated_question": "Define 'object' and 'attribute'... (reformulated version)",
    "co_evolution_enabled": true,
    "alignment_validated": true,
    "iterations": 1
  },
  "metadata": {
    "num_generations": 3,
    "min_agreement": 2,
    "consensus_checks": [...],
    "agreement_distribution": {...},
    "deduplication": {
      "initial_dimensions": 5,
      "dimensions_after_dedup": 4,
      "overlaps_removed": ["Precision of Definitions merged into Conceptual Distinction"]
    }
  },
  "dimensions": [
    {
      "dimension_id": "conceptual_understanding",
      "title": "Conceptual Understanding",
      "points": 4,
      "description": "...",
      "question_alignment": "Define 'object' and 'attribute'... Clearly distinguish them",
      "checks": [
        {
          "check_id": "c1",
          "text": "Defines object",
          "agreement_count": 3,
          "confidence": 1.0
        }
      ]
    }
  ]
}
```

---

## Benefits of This Approach

✅ **Decoupled:** Rubric generation separate from grading
✅ **Flexible:** Manual (ChatGPT) or automated (pipeline)
✅ **High Quality:** Ensemble consensus or human review
✅ **Auditable:** Complete audit trail stored
✅ **Reproducible:** JSON artifacts version-controlled
✅ **Transparent:** All intermediate steps documented
✅ **Reusable:** Rubrics can be shared across courses

---

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| LLM hallucinations | Bad rubrics | Ensemble + consensus |
| Context too large | Token limits | Use RAG if needed |
| Retrieval errors (RAG) | Wrong context | Validate retrieved passages |
| Overlap in dimensions | Double penalties | Check extraction catches this |
| Inconsistent format | Incompatible with grading | JSON schema validation |
| Question reformulation changes intent | Assessment validity | Store original; manual review before deploy |
| Already-administered questions | Fairness issues | Only use co-evolution for new assessments |
| Misalignment despite validation | Grading mismatches | Include alignment report in rubric metadata |

---

## Timeline

- **Immediate:**
  - Manual generation via ChatGPT-Plus/Claude (start any time, no setup)
  - Question-Rubric Co-Evolution manually (apply to any manually-generated rubric)

- **Later:**
  - Automated ensemble pipeline (separate project)
  - Co-evolution module integrated into pipeline

- **Integration:**
  - Feed rubrics to grading system (existing task)
  - Include original + reformulated questions in rubric metadata

---

## Next Steps (When Ready)

1. Decide: Manual (ChatGPT-Plus) vs Automated (pipeline) vs Both
2. Decide: Include Question-Rubric Co-Evolution? (recommended for new assessments)
3. Create prompt templates (including co-evolution if enabled)
4. Generate initial rubrics (manual or pipeline)
5. Apply co-evolution if enabled (reformulate questions, validate alignment)
6. Validate quality (rubric clarity, question-rubric alignment)
7. Document both original and reformulated questions
8. Feed into grading system with complete metadata

---
