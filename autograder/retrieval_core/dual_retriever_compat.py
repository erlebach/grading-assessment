"""Backward-compatible DualIndexRetriever wrapper.

Provides DualIndexRetriever as a subclass of MultiIndexRetriever for
backward compatibility with existing code that uses the dual-index API.

"""

from typing import Any, Optional

from llama_index.core import VectorStoreIndex

from retrieval_core.multi_retriever import MultiIndexRetriever


class DualIndexRetriever(MultiIndexRetriever):
    """Backward-compatible retriever for dual indexes (word and sentence).

    Extends MultiIndexRetriever with a familiar API for code expecting
    the original DualIndexRetriever with named word_index and sentence_index
    parameters.

    Attributes:
        word_index: The word-based VectorStoreIndex (for backward compatibility).
        sentence_index: The sentence-based VectorStoreIndex (for backward compatibility).
        indexes: Dictionary mapping index IDs to indexes (inherited).
        index_ids: List of index IDs (inherited).
        reranker: CrossEncoder model (inherited).

    """

    def __init__(
        self,
        word_index: VectorStoreIndex,
        sentence_index: VectorStoreIndex,
        reranker_model: Optional[str] = None,
    ) -> None:
        """Initialize backward-compatible dual-index retriever.

        Args:
            word_index: Word-based VectorStoreIndex.
            sentence_index: Sentence-based VectorStoreIndex.
            reranker_model: Cross-encoder model name. If None, uses environment
                           variable RERANKER_MODEL or defaults to ms-marco-MiniLM-L-6-v2.

        """
        # Store as named attributes for backward compatibility
        self.word_index = word_index
        self.sentence_index = sentence_index

        # Create indexes dict for parent class
        indexes = {
            "word_index": word_index,
            "sentence_index": sentence_index,
        }

        # Initialize parent with both indexes
        super().__init__(indexes, reranker_model)

    def retrieve(
        self,
        query: str,
        top_k_per_index: int = 10,
        final_top_k: int = 5,
        similarity_threshold: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Retrieve and rerank from both indexes.

        Uses the dual-index API (queries both word and sentence indexes).
        For new code, use MultiIndexRetriever.retrieve() with index_subset parameter.

        Args:
            query: Query string.
            top_k_per_index: Number of results to retrieve from each index.
            final_top_k: Number of results to return after reranking.
            similarity_threshold: Minimum similarity score (0.0 to 1.0).

        Returns:
            List of reranked evidence dictionaries with citation metadata.

        """
        # Use parent retrieve with both indexes (original behavior)
        return super().retrieve(
            query=query,
            top_k_per_index=top_k_per_index,
            final_top_k=final_top_k,
            similarity_threshold=similarity_threshold,
            index_subset=["word_index", "sentence_index"],  # Always both for backward compat
        )
