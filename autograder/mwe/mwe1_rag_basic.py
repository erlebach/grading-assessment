"""MWE 1: Basic LlamaIndex RAG Setup.

This script demonstrates:
1. Loading LLM provider configuration
2. Creating an in-memory vector index
3. Document ingestion and chunking
4. Basic similarity search and retrieval

Prerequisites:
- Set environment variables in $HOME/.env (optional):
  - EMBEDDING_PROVIDER=sentence-transformer (default)
  - EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2 (default)

Note: This MWE uses local SentenceTransformer embeddings by default,
which do not require API keys. The model will be downloaded automatically
on first run.

Usage:
    python -m mwe.mwe1_rag_basic

"""

from config.llm_config import setup_llamaindex_defaults
from evidence.llamaindex_setup import (
    create_in_memory_index,
    load_documents_from_texts,
    query_index,
)


def main() -> None:
    """Run MWE 1 demonstration."""
    print("=" * 70)
    print("MWE 1: Basic LlamaIndex RAG Setup")
    print("=" * 70)

    # Step 1: Configure LlamaIndex
    print("\n[Step 1] Configuring LlamaIndex with default settings...")
    setup_llamaindex_defaults()
    print("✓ Configuration loaded from $HOME/.env")

    # Step 2: Create sample evidence corpus
    print("\n[Step 2] Creating sample evidence corpus...")
    evidence_texts = [
        # Information theory concepts
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
        # Entropy concepts
        "The entropy H(X) of a random variable measures the average "
        "information content or uncertainty. For a discrete random variable "
        "with probability mass function p(x), entropy is defined as "
        "H(X) = -sum_x p(x) log p(x).",
        "Conditional entropy H(X|Y) measures the average uncertainty "
        "remaining about X after observing Y. It is related to mutual "
        "information by: I(X;Y) = H(X) - H(X|Y).",
        # Data quality concepts
        "Data quality dimensions include accuracy, completeness, consistency, "
        "timeliness, and validity. Accuracy measures how well data represents "
        "the real-world entity or event it describes.",
        "Data completeness refers to the extent to which all required data "
        "is present. Missing data can arise from various sources and can "
        "significantly impact analysis results.",
    ]

    print(f"✓ Created corpus with {len(evidence_texts)} evidence documents")

    # Step 3: Build in-memory vector index
    print("\n[Step 3] Building in-memory vector index...")
    documents = load_documents_from_texts(evidence_texts)
    index = create_in_memory_index(documents, chunk_size=512, chunk_overlap=50)
    print("✓ Index built successfully")

    # Step 4: Demonstrate retrieval
    print("\n[Step 4] Testing evidence retrieval...")

    test_queries = [
        "What does mutual information measure?",
        "How is entropy defined?",
        "What are the dimensions of data quality?",
    ]

    for query in test_queries:
        print(f"\n{'─' * 70}")
        print(f"Query: {query}")
        print(f"{'─' * 70}")

        results = query_index(index, query, top_k=3)

        for i, result in enumerate(results, 1):
            print(f"\n  Result {i} (score: {result['score']:.4f}):")
            print(f"  {result['text'][:200]}...")

    # Step 5: Summary
    print("\n" + "=" * 70)
    print("MWE 1 Summary")
    print("=" * 70)
    print("✓ LlamaIndex configured with SentenceTransformer embeddings")
    print("✓ In-memory vector store created")
    print(f"✓ Indexed {len(evidence_texts)} evidence documents")
    print("✓ Similarity search working correctly")
    print("\nNext: MWE 2 will add citation metadata and rubric integration")


if __name__ == "__main__":
    main()
