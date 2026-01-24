#!/usr/bin/env python3
"""
Preprocessing stage: Collect all reranked evidence for each criterion.

This script:
1. Loads the rubric for q01
2. Builds in-memory indexes
3. For each criterion, retrieves and reranks evidence
4. Saves all reranked evidence to q01_reranked.json
5. Creates a schema with criterion_id, title, and reranked evidence array

Output: q01_reranked.json with structure:
[
  {
    "criterion_id": "definition_accuracy",
    "title": "Definition Accuracy",
    "reranked_evidence": [
      {
        "source_id": "...",
        "text": "...",
        "reranker_score": 1.234,
        "similarity_score": 0.789
      },
      ...
    ]
  },
  ...
]
"""

import json
import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Add autograder to path
sys.path.insert(0, str(Path(__file__).parent))

from grading_dynamic_rubrics.criterion_loader import load_criterion_titles
from grading_pipeline.config_loader import load_rubric_config, get_rubric_path
from grading_pipeline.index_builder_in_memory import (
    build_multi_indexes_in_memory,
)
from grading_dynamic_rubrics.pipeline import _load_retrieval_params_from_config
from retrieval_core.multi_retriever import MultiIndexRetriever

def main():
    print("=" * 80)
    print("PREPROCESSING: RERANKED EVIDENCE COLLECTION FOR Q01")
    print("=" * 80)

    question_id = "q01"

    # Load configuration
    logger.info(f"Loading configuration for {question_id}...")
    config = load_rubric_config(question_id)

    # Load rubric
    logger.info(f"Loading rubric for {question_id}...")
    rubric_path = get_rubric_path(question_id)
    with open(rubric_path, "r") as f:
        rubric = json.load(f)
    logger.info(f"  Question: {rubric.get('question_text', 'N/A')[:100]}...")
    logger.info(f"  Total criteria: {len(rubric.get('criteria', []))}")

    # Load criterion titles
    logger.info(f"Loading criterion titles for {question_id}...")
    criterion_titles = load_criterion_titles(question_id)
    logger.info(f"  Loaded {len(criterion_titles)} criterion titles")

    # Build in-memory indexes
    logger.info("Building in-memory indexes...")
    indexes = build_multi_indexes_in_memory(config)
    logger.info(f"  Built {len(indexes)} indexes: {list(indexes.keys())}")

    # Create retriever
    logger.info("Creating multi-index retriever with cross-encoder reranking...")
    retriever = MultiIndexRetriever(indexes, transparent=False)

    # Load retrieval parameters
    retrieval_params = _load_retrieval_params_from_config(config)
    logger.info(f"  Retrieval params: top_k_per_index={retrieval_params.get('top_k_per_index')}, "
                f"final_top_k={retrieval_params.get('final_top_k')}")

    # Process each criterion
    logger.info("\nProcessing criteria...")
    print("-" * 80)

    all_criterion_evidence = []

    for criterion in rubric.get("criteria", []):
        if not criterion.get("evidence_required", False):
            logger.info(f"  Skipping {criterion.get('criterion_id')} (evidence_required=False)")
            continue

        criterion_id = criterion.get("criterion_id")
        criterion_title = criterion_titles.get(criterion_id, criterion_id)

        logger.info(f"\nProcessing criterion: {criterion_id} ({criterion_title})")

        # Retrieve and rerank evidence
        # Use criterion description as query (from rubric)
        query = criterion.get("description", "")
        if not query:
            logger.warning(f"  No description found for {criterion_id}, skipping")
            continue

        logger.info(f"  Query length: {len(query)} characters")
        logger.info(f"  Retrieving and reranking evidence...")

        try:
            evidence = retriever.retrieve(
                query=query,
                top_k_per_index=int(retrieval_params.get("top_k_per_index", 10)),
                final_top_k=int(retrieval_params.get("final_top_k", 5)),
                similarity_threshold=float(retrieval_params.get("similarity_threshold", 0.0)),
                index_subset=None,
                trace_label=criterion_id,
            )

            logger.info(f"  Retrieved {len(evidence)} reranked evidence items")

            # Build reranked evidence array
            reranked_evidence = []
            for i, ev in enumerate(evidence, 1):
                reranked_evidence.append({
                    "source_id": ev.get("source_id", "unknown"),
                    "text": ev.get("text", ""),
                    "reranker_score": ev.get("reranker_score", 0.0),
                    "similarity_score": ev.get("score", 0.0),
                })
                logger.info(f"    [{i}] {ev.get('source_id', 'unknown'):30} "
                          f"rerank={ev.get('reranker_score', 0.0):8.4f} "
                          f"sim={ev.get('score', 0.0):8.4f}")

            # Add to output
            all_criterion_evidence.append({
                "criterion_id": criterion_id,
                "title": criterion_title,
                "reranked_evidence": reranked_evidence,
            })

        except Exception as e:
            logger.error(f"  Error retrieving evidence for {criterion_id}: {e}")
            # Continue with empty evidence for this criterion
            all_criterion_evidence.append({
                "criterion_id": criterion_id,
                "title": criterion_title,
                "reranked_evidence": [],
            })

    # Save to JSON file
    output_path = Path("q01_reranked.json")
    logger.info(f"\nSaving results to {output_path}...")

    with open(output_path, "w") as f:
        json.dump(all_criterion_evidence, f, indent=2)

    logger.info(f"✓ Successfully saved {len(all_criterion_evidence)} criteria with reranked evidence")

    # Print summary
    print("\n" + "=" * 80)
    print("PREPROCESSING COMPLETE")
    print("=" * 80)
    print(f"\nOutput file: {output_path}")
    print(f"Total criteria: {len(all_criterion_evidence)}")
    for criterion_data in all_criterion_evidence:
        evidence_count = len(criterion_data.get("reranked_evidence", []))
        print(f"  - {criterion_data['criterion_id']:35} {evidence_count:2d} evidence items")

    print(f"\nSchema:")
    print("""
[
  {
    "criterion_id": "definition_accuracy",
    "title": "Definition Accuracy",
    "reranked_evidence": [
      {
        "source_id": "slide_12",
        "text": "Evidence text...",
        "reranker_score": 1.234567,
        "similarity_score": 0.789000
      },
      ...
    ]
  },
  ...
]
    """)

    logger.info("\nPreprocessing stage complete. Ready for grading.")
    logger.info("Next step: Run grading using q01_reranked.json as evidence source.")

if __name__ == "__main__":
    try:
        main()
        print("\n✓ Preprocessing successful. Exiting.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
