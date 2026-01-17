"""Dual-index retriever with cross-encoder reranking.

This module retrieves evidence from both word-based and sentence-based indexes,
combines results with smart deduplication, and reranks using a cross-encoder model.

"""

import os
from typing import Any

from llama_index.core import VectorStoreIndex
from sentence_transformers import CrossEncoder

from evidence.index_builder import extract_citation_from_node


class DualIndexRetriever:
    """Retriever that queries both word-based and sentence-based indexes.

    Combines results with smart deduplication (removes only exact duplicates)
    and reranks using a cross-encoder model for improved relevance.

    """

    def __init__(
        self,
        word_index: VectorStoreIndex,
        sentence_index: VectorStoreIndex,
        reranker_model: str | None = None,
    ) -> None:
        """Initialize the dual-index retriever.

        Args:
            word_index: Word-based VectorStoreIndex.
            sentence_index: Sentence-based VectorStoreIndex.
            reranker_model: Cross-encoder model name. If None, uses environment
                variable RERANKER_MODEL or defaults to ms-marco-MiniLM-L-6-v2.

        """
        self.word_index = word_index
        self.sentence_index = sentence_index

        # Get reranker model from parameter, env var, or default
        if reranker_model is None:
            reranker_model = os.getenv(
                "RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
            )

        print(f"Loading reranker model: {reranker_model}")
        self.reranker = CrossEncoder(reranker_model)
        self.reranker_model_name = reranker_model

    def retrieve(
        self,
        query: str,
        top_k_per_index: int = 10,
        final_top_k: int = 5,
        similarity_threshold: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Retrieve and rerank evidence from both indexes.

        Args:
            query: Query string.
            top_k_per_index: Number of results to retrieve from each index.
            final_top_k: Number of results to return after reranking.
            similarity_threshold: Minimum similarity score (0.0 to 1.0).

        Returns:
            List of reranked evidence dictionaries with citation metadata.

        """
        # Retrieve from word-based index
        word_retriever = self.word_index.as_retriever(
            similarity_top_k=top_k_per_index
        )
        word_nodes = word_retriever.retrieve(query)

        # Retrieve from sentence-based index
        sentence_retriever = self.sentence_index.as_retriever(
            similarity_top_k=top_k_per_index
        )
        sentence_nodes = sentence_retriever.retrieve(query)

        # Extract citations and filter by threshold
        word_results = []
        for node in word_nodes:
            citation = extract_citation_from_node(node)
            if citation["score"] >= similarity_threshold:
                citation["index_type"] = "word"
                word_results.append(citation)

        sentence_results = []
        for node in sentence_nodes:
            citation = extract_citation_from_node(node)
            if citation["score"] >= similarity_threshold:
                citation["index_type"] = "sentence"
                sentence_results.append(citation)

        # Union and deduplicate
        combined_results = self._union_and_deduplicate(word_results, sentence_results)

        # Rerank
        reranked_results = self._rerank(query, combined_results, final_top_k)

        return reranked_results

    def _union_and_deduplicate(
        self, results1: list[dict[str, Any]], results2: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Combine results with smart deduplication.

        Removes only exact duplicates (same source_id AND identical text).
        Keeps overlapping chunks that provide different context.

        Args:
            results1: Results from first index.
            results2: Results from second index.

        Returns:
            Combined and deduplicated results.

        """
        # Use a set to track (source_id, text) pairs for exact duplicate detection
        seen_pairs = set()
        unique_results = []

        # Process all results
        for result in results1 + results2:
            source_id = result.get("source_id", "unknown")
            text = result.get("text", "")

            # Create unique key from source_id and text
            key = (source_id, text)

            # Only add if not an exact duplicate
            if key not in seen_pairs:
                seen_pairs.add(key)
                unique_results.append(result)

        return unique_results

    def _rerank(
        self, query: str, candidates: list[dict[str, Any]], top_k: int
    ) -> list[dict[str, Any]]:
        """Rerank candidates using cross-encoder model.

        Args:
            query: Query string.
            candidates: List of candidate evidence dictionaries.
            top_k: Number of top results to return.

        Returns:
            Reranked results with updated scores.

        """
        if not candidates:
            return []

        # Prepare (query, text) pairs for reranking
        pairs = [(query, candidate["text"]) for candidate in candidates]

        # Get reranking scores
        rerank_scores = self.reranker.predict(pairs)

        # Update candidates with reranking scores
        for candidate, score in zip(candidates, rerank_scores):
            candidate["original_score"] = candidate.get("score", 0.0)
            candidate["rerank_score"] = float(score)
            candidate["score"] = float(score)  # Use rerank score as primary score

        # Sort by rerank score and return top_k
        reranked = sorted(candidates, key=lambda x: x["rerank_score"], reverse=True)

        return reranked[:top_k]

    def retrieve_for_criterion(
        self,
        criterion: dict[str, Any],
        student_answer: str,
        top_k_per_index: int = 10,
        final_top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Retrieve evidence relevant to a specific rubric criterion.

        Args:
            criterion: Rubric criterion dictionary containing:
                - criterion_id: Unique identifier
                - description: Criterion description
            student_answer: Student's answer text.
            top_k_per_index: Number of results from each index.
            final_top_k: Number of results after reranking.

        Returns:
            List of reranked evidence citations relevant to the criterion.

        """
        # Construct query from criterion and student answer
        query = f"{criterion['description']} {student_answer}"

        return self.retrieve(
            query, top_k_per_index=top_k_per_index, final_top_k=final_top_k
        )

    def format_evidence_for_grading(
        self, evidence_list: list[dict[str, Any]]
    ) -> str:
        """Format evidence citations for use in grading prompts.

        Args:
            evidence_list: List of evidence citations.

        Returns:
            Formatted string with numbered evidence items.

        """
        if not evidence_list:
            return "No evidence retrieved."

        lines = []
        for i, evidence in enumerate(evidence_list, 1):
            source_id = evidence["source_id"]
            text = evidence["text"]
            score = evidence.get("rerank_score", evidence.get("score", 0.0))
            index_type = evidence.get("index_type", "unknown")

            lines.append(
                f"[{i}] Source: {source_id} (relevance: {score:.3f}, from: {index_type})\n{text}\n"
            )

        return "\n".join(lines)


if __name__ == "__main__":
    # Test dual retriever with reranking
    import time
    from pathlib import Path

    from config.llm_config import setup_llamaindex_defaults
    from evidence.index_builder import create_documents_with_metadata
    from retrieval_core.index_builder import build_sentence_index, build_word_index

    print("Testing DualIndexRetriever with reranking...")

    # Setup LlamaIndex
    setup_llamaindex_defaults()

    # Create sample evidence
    texts = [
        "Mutual information I(X;Y) measures the reduction in uncertainty "
        "about variable X when we observe variable Y. It quantifies the "
        "amount of information obtained about one random variable through "
        "observing the other random variable.",
        "The mutual information is always non-negative: I(X;Y) >= 0. "
        "It equals zero if and only if X and Y are independent. "
        "It is also symmetric: I(X;Y) = I(Y;X).",
        "Mutual information captures both linear and nonlinear dependencies "
        "between variables. Unlike correlation, which only measures linear "
        "relationships, mutual information is based on the joint probability "
        "distribution and can detect any type of statistical dependence.",
        "Entropy H(X) measures the average information content or uncertainty. "
        "For a discrete random variable, entropy is defined as H(X) = -sum_x p(x) log p(x).",
        "Conditional entropy H(X|Y) measures the average uncertainty "
        "remaining about X after observing Y. It is related to mutual "
        "information by: I(X;Y) = H(X) - H(X|Y).",
    ]

    sources = [
        {"source_id": "slide_12", "source_type": "slide", "page_number": 12},
        {"source_id": "slide_13", "source_type": "slide", "page_number": 13},
        {"source_id": "slide_14", "source_type": "slide", "page_number": 14},
        {"source_id": "slide_20", "source_type": "slide", "page_number": 20},
        {"source_id": "slide_21", "source_type": "slide", "page_number": 21},
    ]

    documents = create_documents_with_metadata(texts, sources)

    # Build dual indexes in retrieval_core/tmp/
    temp_dir = Path(__file__).parent / "tmp" / f"test_retriever_{int(time.time())}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nBuilding indexes in {temp_dir}")

    word_index = build_word_index(documents, temp_dir, "test_word_index")
    print("✓ Word-based index built")

    sentence_index = build_sentence_index(documents, temp_dir, "test_sentence_index")
    print("✓ Sentence-based index built")

    # Create dual retriever
    retriever = DualIndexRetriever(word_index, sentence_index)
    print("✓ Dual retriever created")

    # Test retrieval and reranking
    print("\n[Test 1] Basic dual retrieval with reranking:")
    query = "What is mutual information?"
    results = retriever.retrieve(query, top_k_per_index=3, final_top_k=3)
    print(f"Retrieved and reranked {len(results)} results")
    for i, result in enumerate(results, 1):
        print(
            f"  {i}. {result['source_id']} (rerank: {result['rerank_score']:.3f}, "
            f"original: {result['original_score']:.3f}, from: {result['index_type']})"
        )

    # Test criterion-based retrieval
    print("\n[Test 2] Criterion-based retrieval:")
    criterion = {
        "criterion_id": "c1",
        "description": "Correctly defines mutual information",
    }
    student_answer = "Mutual information tells us how much knowing Y reduces uncertainty about X."

    results = retriever.retrieve_for_criterion(
        criterion, student_answer, top_k_per_index=3, final_top_k=2
    )
    print(f"Retrieved {len(results)} results for criterion")
    for i, result in enumerate(results, 1):
        print(
            f"  {i}. {result['source_id']} (rerank: {result['rerank_score']:.3f})"
        )

    # Test formatting
    print("\n[Test 3] Formatted evidence:")
    formatted = retriever.format_evidence_for_grading(results)
    print(formatted)

    # Test deduplication
    print("\n[Test 4] Testing smart deduplication:")
    # Create duplicate results
    dup_results1 = [
        {"source_id": "s1", "text": "text1", "score": 0.9},
        {"source_id": "s2", "text": "text2", "score": 0.8},
    ]
    dup_results2 = [
        {"source_id": "s1", "text": "text1", "score": 0.85},  # Exact duplicate
        {"source_id": "s1", "text": "text1_different", "score": 0.7},  # Different text, same source
        {"source_id": "s3", "text": "text3", "score": 0.6},
    ]

    deduped = retriever._union_and_deduplicate(dup_results1, dup_results2)
    print(f"Original: {len(dup_results1) + len(dup_results2)} results")
    print(f"After deduplication: {len(deduped)} results")
    print("Kept results:")
    for result in deduped:
        print(f"  - {result['source_id']}: {result['text'][:20]}...")

    print("\n✓ Dual retriever test complete")
