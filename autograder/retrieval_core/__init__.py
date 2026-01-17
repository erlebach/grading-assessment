"""Retrieval Core: Dual-index Chroma RAG with reranking.

This module provides core retrieval functionality:
- Chroma vector database (persistent storage)
- Dual embedding indexes: word-based (512 chars) + sentence-based
- YAML-based source configuration (files + URLs)
- Cross-encoder reranking for improved relevance

"""

__version__ = "1.0.0"
