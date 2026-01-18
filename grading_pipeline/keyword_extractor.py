"""Keyword extraction transformation for LlamaIndex.

Extracts keywords from chunks and stores them in a separate keyword store file.

"""

from pathlib import Path
from typing import Any

from llama_index.core.node_parser import TextSplitter
from llama_index.core.schema import BaseNode, Document, TransformComponent

from grader.grade_question import extract_keywords
from grading_pipeline.keyword_store import add_chunk_keywords


class KeywordExtractor(TransformComponent):
    """Transform that extracts keywords from nodes and stores them separately."""

    def __init__(
        self,
        keyword_store_path: Path,
        domain_specific: bool = True,
        max_keywords_per_chunk: int = 30,
    ):
        """Initialize keyword extractor.

        Args:
            keyword_store_path: Path to keyword store JSON file.
            domain_specific: If True, filter to domain-specific terms only.
            max_keywords_per_chunk: Maximum keywords to store per chunk.

        """
        self.keyword_store_path = keyword_store_path
        self.domain_specific = domain_specific
        self.max_keywords_per_chunk = max_keywords_per_chunk

    def __call__(
        self, nodes: list[BaseNode], **kwargs: Any
    ) -> list[BaseNode]:
        """Extract keywords from nodes and store them.

        Args:
            nodes: List of nodes to process.
            **kwargs: Additional arguments.

        Returns:
            Processed nodes (unchanged, keywords stored separately).

        """
        for node in nodes:
            # Extract keywords from chunk text
            keywords = extract_keywords(
                node.text, domain_specific=self.domain_specific
            )

            # Limit keywords per chunk
            keywords = keywords[: self.max_keywords_per_chunk]

            # Store keywords using node_id as chunk_id
            chunk_id = node.node_id
            if chunk_id and keywords:
                add_chunk_keywords(chunk_id, keywords, self.keyword_store_path)

        return nodes
