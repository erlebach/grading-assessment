"""Multi-index retriever with cross-encoder reranking.

Generalizes DualIndexRetriever to support N indexes with runtime subset selection,
deduplication across all indexes, and cross-encoder reranking.

"""

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any, Optional

from llama_index.core import VectorStoreIndex
from sentence_transformers import CrossEncoder

from evidence.index_builder import extract_citation_from_node

# Global file handle for retriever diagnostics (same pattern as transparency.log)
_retriever_log_handle = None


def _get_retriever_log_handle():
    """Get or create the retriever diagnostics log file handle."""
    global _retriever_log_handle
    if _retriever_log_handle is None:
        # Create logs directory with absolute path
        autograder_dir = Path(__file__).parent.parent
        logs_dir = autograder_dir / "logs"
        logs_dir.mkdir(exist_ok=True)

        # Open retriever.log with line buffering
        log_file = logs_dir / "retriever.log"
        _retriever_log_handle = open(log_file, "a", buffering=1)

    return _retriever_log_handle


def _write_retriever_log(message: str) -> None:
    """Write a message to retriever.log."""
    handle = _get_retriever_log_handle()
    handle.write(message)
    handle.flush()


class MultiIndexRetriever:
    """Retriever that queries multiple indexes with deduplication and reranking.

    Combines results from multiple indexes with smart deduplication (removes only
    exact duplicates based on source_id and text) and reranks using a cross-encoder.

    Attributes:
        indexes: Dictionary mapping index IDs to VectorStoreIndex instances.
        index_ids: List of available index IDs.
        reranker: CrossEncoder model instance.
        reranker_model_name: Name of the reranker model.

    """

    def __init__(
        self,
        indexes: dict[str, VectorStoreIndex],
        reranker_model: Optional[str] = None,
        transparent: bool = False,
        trace_writer: Callable[[str], None] | None = None,
    ) -> None:
        """Initialize the multi-index retriever.

        Args:
            indexes: Dictionary mapping index ID strings to VectorStoreIndex objects.
                    Example: {"word_index": word_idx, "sentence_index": sent_idx}
            reranker_model: Cross-encoder model name. If None, uses environment
                           variable RERANKER_MODEL or defaults to ms-marco-MiniLM-L-6-v2.
            transparent: If True, emit verbose retrieval/rerank traces.
            trace_writer: Optional function that receives trace strings.
                If None, trace output goes to stdout.

        Raises:
            ValueError: If indexes dict is empty.

        """
        if not indexes:
            raise ValueError("At least one index must be provided")

        self.indexes = indexes
        self.index_ids = list(indexes.keys())
        self.transparent = transparent
        self._trace_writer = trace_writer

        # Get reranker model from parameter, env var, or default
        if reranker_model is None:
            reranker_model = os.getenv(
                "RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
            )

        print(f"Loading reranker model: {reranker_model}")
        self.reranker = CrossEncoder(reranker_model)
        self.reranker_model_name = reranker_model

    def enable_transparency(self, trace_writer: Callable[[str], None] | None) -> None:
        """Enable verbose transparency traces.

        Args:
            trace_writer: Function that receives trace strings. If None, traces
                are printed to stdout.

        """
        self.transparent = True
        self._trace_writer = trace_writer

    def retrieve(
        self,
        query: str,
        top_k_per_index: int = 10,
        final_top_k: int = 5,
        similarity_threshold: float = 0.0,
        index_subset: Optional[list[str]] = None,
        trace_label: str | None = None,
        rerank_query: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Retrieve and rerank evidence from multiple indexes.

        Retrieves from specified indexes, deduplicates, and reranks results.

        Args:
            query: Query string for vector similarity retrieval.
            top_k_per_index: Number of results to retrieve from each index.
            final_top_k: Number of results to return after reranking.
            similarity_threshold: Minimum similarity score (0.0 to 1.0).
            index_subset: List of index IDs to query. If None, queries all indexes.
            trace_label: Optional label included in transparent traces (e.g.,
                criterion id).
            rerank_query: Optional separate query for reranking. If None, uses query.

        Returns:
            List of reranked evidence dictionaries with citation metadata.

        Raises:
            ValueError: If index_subset contains unknown index IDs.

        """
        # Log query received by retriever
        _write_retriever_log(f"[RETRIEVER_DIAGNOSIS] QUERY_RECEIVED_BY_RETRIEVER={query[:80]}...\n")
        _write_retriever_log(f"[RETRIEVER_DIAGNOSIS] TRACE_LABEL={trace_label} QUERY_LENGTH={len(query)}\n")

        # Determine which indexes to query
        if index_subset is None:
            active_indexes = self.index_ids
        else:
            # Validate subset IDs
            unknown = set(index_subset) - set(self.index_ids)
            if unknown:
                raise ValueError(
                    f"Unknown index IDs in subset: {unknown}. "
                    f"Available: {self.index_ids}"
                )
            active_indexes = index_subset

        if self.transparent:
            self._trace_retrieval_parameters(
                active_indexes=active_indexes,
                top_k_per_index=top_k_per_index,
                final_top_k=final_top_k,
                similarity_threshold=similarity_threshold,
            )
            self._trace_query(query=query, trace_label=trace_label)

        # Retrieve from each active index
        all_results: list[dict[str, Any]] = []

        for index_id in active_indexes:
            index = self.indexes[index_id]
            retriever = index.as_retriever(similarity_top_k=top_k_per_index)
            nodes = retriever.retrieve(query)

            # Extract citations and filter by threshold
            index_results: list[dict[str, Any]] = []
            for node in nodes:
                citation = extract_citation_from_node(node)
                if citation["score"] >= similarity_threshold:
                    citation["index_id"] = index_id  # Track which index this came from
                    index_results.append(citation)
                    all_results.append(citation)

            if self.transparent:
                self._trace_retriever_results(
                    index_label=index_id,
                    results=index_results,
                    top_k=top_k_per_index,
                )

        # Union and deduplicate
        combined_results = self._union_and_deduplicate(all_results)

        # Rerank using separate query if provided
        if rerank_query is None:
            rerank_query = query

        if self.transparent:
            self._trace_reranker_inputs(query=rerank_query, candidates=combined_results)
        print(f"===> rerank, {rerank_query=}")
        reranked_results = self._rerank(rerank_query, combined_results, final_top_k)
        if self.transparent:
            self._trace_reranker_outputs(results=reranked_results, top_k=final_top_k)

        return reranked_results

    def _union_and_deduplicate(
        self, results: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Remove exact duplicates from results across all indexes.

        Removes only exact duplicates (same source_id AND identical text).
        Keeps overlapping chunks that provide different context.

        Args:
            results: List of result dictionaries from all indexes.

        Returns:
            Deduplicated results list.

        """
        # Use a set to track (source_id, text) pairs for exact duplicate detection
        seen_pairs = set()
        unique_results = []

        # Process all results
        for result in results:
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
        """Rerank candidates using cross-encoder model with threshold filtering.

        Args:
            query: Query string.
            candidates: List of candidate evidence dictionaries.
            top_k: Number of top results to return.

        Returns:
            Top-k reranked results sorted by score (descending) that meet the
            relevance threshold. If no results meet the threshold, returns the
            top-1 result as fallback.

        """
        # Relevance threshold: only return results with reranker score >= this value
        # Negative scores indicate the cross-encoder judges the text as irrelevant
        RERANK_THRESHOLD = 0.0

        if not candidates:
            return []

        if top_k <= 0:
            return []

        # Log query being sent to reranker
        _write_retriever_log(f"[RERANKER_DIAGNOSIS] QUERY_TO_RERANKER={query[:80]}...\n")
        _write_retriever_log(f"[RERANKER_DIAGNOSIS] QUERY_LENGTH={len(query)} NUM_CANDIDATES={len(candidates)}\n")

        # Prepare pairs for reranker
        query_text_pairs = [(query, result["text"]) for result in candidates]

        # Get reranker scores
        scores = self.reranker.predict(query_text_pairs)
        _write_retriever_log(f"[RERANKER_DIAGNOSIS] RERANKER_SCORES={scores[:3]}... (first 3 of {len(scores)})\n")

        # Attach scores to candidates
        for result, score in zip(candidates, scores):
            result["reranker_score"] = float(score)

        # Sort by reranker score descending
        sorted_results = sorted(candidates, key=lambda x: x["reranker_score"], reverse=True)

        # Filter by relevance threshold
        # Only keep results where cross-encoder judges them as relevant (score >= 0)
        filtered_results = [
            r for r in sorted_results if r["reranker_score"] >= RERANK_THRESHOLD
        ]

        # Log filtering results
        _write_retriever_log(
            f"[RERANKER_THRESHOLD] THRESHOLD={RERANK_THRESHOLD} "
            f"BEFORE_FILTER={len(sorted_results)} AFTER_FILTER={len(filtered_results)}\n"
        )

        # If all results were filtered out, use at least the top-1 result
        # This ensures we always return something for the LLM to work with
        if not filtered_results:
            _write_retriever_log(
                f"[RERANKER_THRESHOLD] All {len(sorted_results)} candidates below threshold. "
                f"Using top-1 as fallback (score={sorted_results[0]['reranker_score']:.4f})\n"
            )
            filtered_results = sorted_results[:1]

        # Return top-k from filtered results
        return filtered_results[:top_k]

    def get_active_indexes(self) -> list[str]:
        """Get list of available index IDs.

        Returns:
            List of index IDs.

        """
        return self.index_ids

    def _trace_write(self, msg: str) -> None:
        """Write a trace message.

        Args:
            msg: Message to write (should already contain trailing newline).

        """
        if self._trace_writer is not None:
            self._trace_writer(msg)
            return
        print(msg, end="", flush=True)

    def _trace_divider(self) -> None:
        """Write a dotted divider line."""
        self._trace_write("." * 80 + "\n")

    def _trace_query(self, query: str, trace_label: str | None) -> None:
        """Trace the input query text.

        Args:
            query: Query string.
            trace_label: Optional label for this query (e.g., criterion id).

        """
        self._trace_divider()
        label = f" [{trace_label}]" if trace_label else ""
        self._trace_write(f"[TRANSPARENT] INPUT QUERY{label}\n")
        query_display = query if query else '""'
        self._trace_write(f"QUERY_STRING={query_display}\n")
        self._trace_divider()

    def _trace_retriever_results(
        self,
        index_label: str,
        results: list[dict[str, Any]],
        top_k: int,
    ) -> None:
        """Trace retriever outputs for an index.

        Args:
            index_label: Index identifier for this retriever.
            results: Retrieved citation dicts (already threshold-filtered).
            top_k: Requested top-k for that index.

        """
        self._trace_write("[TRANSPARENT] RETRIEVER RESULTS\n")
        self._trace_write(f"INDEX_NAME={index_label}\n")
        self._trace_write(f"REQUESTED_K={top_k} RETURNED={len(results)}\n")
        if not results:
            self._trace_divider()
            return
        for i, r in enumerate(results, 1):
            similarity = float(r.get("score", 0.0))
            source_id = str(r.get("source_id", "unknown"))
            self._trace_write(
                f"[{index_label} #{i}] SIMILARITY_SCORE={similarity:.6f} "
                f"SOURCE_ID={source_id}\n"
            )
            self._trace_write("<<<BEGIN RETRIEVED TEXT>>>\n")
            self._trace_write(f"{r.get('text', '')}\n")
            self._trace_write("<<<END RETRIEVED TEXT>>>\n")
            self._trace_divider()

    def _trace_reranker_inputs(
        self, query: str, candidates: list[dict[str, Any]]
    ) -> None:
        """Trace inputs to the reranker.

        Args:
            query: Query string.
            candidates: Candidate list prior to reranking.

        """
        self._trace_write("[TRANSPARENT] RERANKER INPUTS\n")
        self._trace_write(f"CANDIDATES={len(candidates)}\n")
        self._trace_write("<<<BEGIN RERANKER QUERY>>>\n")
        self._trace_write(f"{query}\n")
        self._trace_write("<<<END RERANKER QUERY>>>\n")
        self._trace_divider()
        for i, c in enumerate(candidates, 1):
            similarity = float(c.get("score", 0.0))
            source_id = str(c.get("source_id", "unknown"))
            index_id = str(c.get("index_id", "unknown"))
            self._trace_write(
                f"[candidate #{i}] SIMILARITY_SCORE={similarity:.6f} "
                f"SOURCE_ID={source_id} INDEX={index_id}\n"
            )
            self._trace_write("<<<BEGIN CANDIDATE TEXT>>>\n")
            self._trace_write(f"{c.get('text', '')}\n")
            self._trace_write("<<<END CANDIDATE TEXT>>>\n")
            self._trace_divider()

    def _trace_reranker_outputs(self, results: list[dict[str, Any]], top_k: int) -> None:
        """Trace outputs from the reranker.

        Args:
            results: Reranked results (post top-k).
            top_k: Requested final top-k.

        """
        self._trace_write("[TRANSPARENT] RERANKER OUTPUTS\n")
        self._trace_write(f"REQUESTED_TOP_K={top_k} RETURNED={len(results)}\n")
        if not results:
            self._trace_divider()
            return
        for i, r in enumerate(results, 1):
            rerank_score = float(r.get("reranker_score", 0.0))
            similarity = float(r.get("score", 0.0))
            source_id = str(r.get("source_id", "unknown"))
            index_id = str(r.get("index_id", "unknown"))
            self._trace_write(
                f"[reranked #{i}] RERANK_SCORE={rerank_score:.6f} "
                f"SIMILARITY_SCORE={similarity:.6f} "
                f"SOURCE_ID={source_id} INDEX={index_id}\n"
            )
            self._trace_write("<<<BEGIN RERANKED TEXT>>>\n")
            self._trace_write(f"{r.get('text', '')}\n")
            self._trace_write("<<<END RERANKED TEXT>>>\n")
            self._trace_divider()

    def _trace_retrieval_parameters(
        self,
        active_indexes: list[str],
        top_k_per_index: int,
        final_top_k: int,
        similarity_threshold: float,
    ) -> None:
        """Trace which indexes/parameters are used for retrieval.

        Args:
            active_indexes: List of index IDs that will be queried.
            top_k_per_index: Requested top-k per index.
            final_top_k: Requested final top-k after reranking.
            similarity_threshold: Similarity threshold for accepting candidates.

        """
        self._trace_divider()
        self._trace_write("[TRANSPARENT] RETRIEVAL PARAMETERS\n")
        self._trace_write(f"ACTIVE_INDEXES={active_indexes}\n")
        self._trace_write(f"TOP_K_PER_INDEX={top_k_per_index}\n")
        self._trace_write(f"FINAL_TOP_K={final_top_k}\n")
        self._trace_write(f"SIMILARITY_THRESHOLD={similarity_threshold:.6f}\n")
        self._trace_divider()
