  # *Is there an inconsistency in my approach? If the grading is done without the feedback, something is strange.  I know I am doing RAG and reranking and determining a grade, but somehow, I feel that the language model should play a role.*

    Yes, there's a real inconsistency.

    The scoring pipeline (apply_rubric_scoring_dynamic) is purely mechanical — keyword matching + semantic similarity. No LLM is
    involved in assigning the score. The LLM (gpt-oss:20b via Ollama) is only called afterward to narrate the feedback,
    explaining a score that's already been finalized.

    This means:
    - The grade is determined by BM25 keyword overlap and embedding similarity against the evidence index
    - The LLM has zero influence on the score
    - The feedback is post-hoc rationalization of a mechanically-computed number

    The philosophical problem: you're using a rubric with criteria like "explains that a true zero is required for ratios to be
    meaningful" — that's a semantic judgment, not a keyword match. A student could write a perfect conceptually-correct answer
    using different vocabulary and score low. A student could parrot rubric-adjacent words and score high.

    The LLM should be doing the criterion-level judgment: "does this answer demonstrate understanding of X?" That's what humans
    do when grading. The RAG evidence index is useful for grounding (confirming the source material supports the criterion), but
    the LLM should be deciding whether the student's answer meets each criterion — not just whether rubric keywords appear in the
     text.

    The current design inverts the natural roles: mechanical scoring where judgment is needed, LLM narration where no judgment is
     needed.
----------------------------------------------------------------------
  # *This inconsistency derives from the notion that feedback should only occur after scoring (conversation with Perplexity). So perhaps RAG shoudl be replaced by LLM querying? Of course use of LLM is more expensive.*

    The core tension is:

    RAG (current): retrieves chunks from the source PDF, matches keywords/embeddings against the student answer. Fast, cheap,
    deterministic — but it's measuring overlap with the textbook, not correctness of the answer. A wrong answer that happens to
    use the right words scores well.

    LLM-as-judge: reads the rubric criterion, the student answer, and the source material, then reasons about whether the
    criterion is met. More expensive, but it's actually evaluating understanding, not surface overlap.

    The Perplexity insight — that feedback should follow scoring, not influence it — is about keeping the grading decision clean.
     But it doesn't mandate how scoring works. An LLM judge can still produce a score first, then justify it, without the
    justification affecting the score.

    The real question is whether the scoring failures you're seeing (wrong answers scoring above less_good answers) are a RAG
    problem or a rubric problem:

    - If the rubric criteria are well-written and content-specific, an LLM judge reading the criterion + answer would likely get
    the ordering right.
    - If the criteria are too generic or keyword-heavy (which the stopword analysis suggests), an LLM judge may also struggle.

    A middle path worth considering: LLM-scored, RAG-grounded — the LLM reads the criterion and student answer, but is
    constrained to only cite evidence from retrieved chunks. This keeps costs lower than full LLM-free-form and maintains
    auditability, while getting semantic understanding rather than keyword overlap.

    The rubric generation quality is likely the deeper root cause regardless of scoring method.
