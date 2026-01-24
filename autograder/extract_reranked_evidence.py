#!/usr/bin/env python3
"""
Extract reranked evidence from transparency.log and populate q01_reranked.json

This script:
1. Parses logs/transparency.log
2. Extracts INPUT QUERY sections to identify criteria
3. Extracts RERANKER OUTPUTS sections with reranked text
4. Populates q01_reranked.json with actual reranked evidence
5. Saves to results/q01_reranked.json
"""

import json
import re
import logging
from pathlib import Path
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def parse_transparency_log():
    """Parse transparency.log to extract reranked evidence by criterion."""

    log_path = Path("logs/transparency.log")

    if not log_path.exists():
        logger.error(f"Transparency log not found at {log_path}")
        return None

    logger.info(f"Reading {log_path}...")
    with open(log_path, "r") as f:
        log_content = f.read()

    # Split into logical chunks by RERANKER OUTPUTS sections
    # Each section corresponds to one criterion

    criterion_data = defaultdict(lambda: {
        "title": None,
        "reranked_evidence": []
    })

    # Find all occurrences of INPUT QUERY sections with criterion IDs
    # Format: [TRANSPARENT] INPUT QUERY [criterion_id]
    query_sections = re.split(r'\[TRANSPARENT\] INPUT QUERY \[([\w_]+)\]', log_content)

    current_criterion = None

    for i in range(1, len(query_sections), 2):
        criterion_id = query_sections[i]
        section_content = query_sections[i + 1] if i + 1 < len(query_sections) else ""

        logger.info(f"\nProcessing criterion: {criterion_id}")

        # Extract RERANKER OUTPUTS section from this criterion's content
        reranker_pattern = r'\[TRANSPARENT\] RERANKER OUTPUTS\s+REQUESTED_TOP_K=(\d+) RETURNED=(\d+)\s+(.*?)(?=\[TRANSPARENT\]|\Z)'
        reranker_match = re.search(reranker_pattern, section_content, re.DOTALL)

        if not reranker_match:
            logger.warning(f"  No RERANKER OUTPUTS found for {criterion_id}")
            continue

        requested_k = int(reranker_match.group(1))
        returned_k = int(reranker_match.group(2))
        reranker_output = reranker_match.group(3)

        logger.info(f"  Requested: {requested_k}, Returned: {returned_k}")

        # Extract individual reranked entries
        # Format: [reranked #N] RERANK_SCORE=... SIMILARITY_SCORE=... SOURCE_ID=... INDEX=...
        # Followed by: <<<BEGIN RERANKED TEXT>>> ... <<<END RERANKED TEXT>>>

        reranked_pattern = r'\[reranked #(\d+)\] RERANK_SCORE=([\d.-]+) SIMILARITY_SCORE=([\d.-]+) SOURCE_ID=(\S+) INDEX=(\S+)\s+<<<BEGIN RERANKED TEXT>>>\s*(.*?)\s*<<<END RERANKED TEXT>>>'

        matches = list(re.finditer(reranked_pattern, reranker_output, re.DOTALL))

        logger.info(f"  Found {len(matches)} reranked results")

        for match in matches:
            rank = int(match.group(1))
            rerank_score = float(match.group(2))
            similarity_score = float(match.group(3))
            source_id = match.group(4)
            index = match.group(5)
            text = match.group(6).strip()

            logger.info(f"    [{rank}] {source_id}: score={rerank_score:.4f}")

            evidence_entry = {
                "rank": rank,
                "source_id": source_id,
                "reranker_score": rerank_score,
                "similarity_score": similarity_score,
                "index": index,
                "text": text
            }

            criterion_data[criterion_id]["reranked_evidence"].append(evidence_entry)

    return criterion_data

def main():
    print("=" * 80)
    print("EXTRACTING RERANKED EVIDENCE FROM TRANSPARENCY LOG")
    print("=" * 80)

    # Parse the log
    criterion_data = parse_transparency_log()

    if not criterion_data:
        logger.error("Failed to parse transparency log")
        return False

    logger.info(f"\nExtracted data for {len(criterion_data)} criteria")

    # Q01 criterion titles for reference
    CRITERION_TITLES = {
        "definition_accuracy": "Definition Accuracy",
        "alternative_names": "Alternative Names",
        "distinction_clarity": "Distinction Clarity",
        "source_referencing_and_context": "Source Referencing and Context",
        "conceptual_understanding_of_attribute_properties": "Conceptual Understanding of Attribute Properties",
        "understanding_of_data_types_and_scales": "Understanding of Data Types and Scales",
        "identification_and_analysis_of_attribute_types": "Identification and Analysis of Attribute Types",
    }

    # Build final output structure
    output_data = []

    for criterion_id in sorted(criterion_data.keys()):
        data = criterion_data[criterion_id]
        title = CRITERION_TITLES.get(criterion_id, criterion_id.replace("_", " ").title())

        output_data.append({
            "criterion_id": criterion_id,
            "title": title,
            "reranked_evidence": data["reranked_evidence"]
        })

    # Save to results folder
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)

    output_path = results_dir / "q01_reranked.json"

    logger.info(f"\nSaving to {output_path}...")
    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2)

    logger.info(f"✓ Successfully saved {output_path}")

    # Print summary
    print("\n" + "=" * 80)
    print("EXTRACTION COMPLETE")
    print("=" * 80)
    print(f"\nOutput file: {output_path}")
    print(f"Total criteria: {len(output_data)}\n")

    for item in output_data:
        evidence_count = len(item["reranked_evidence"])
        print(f"  {item['criterion_id']:45} {evidence_count:2d} evidence items")

    # Show sample of first criterion
    if output_data:
        print(f"\n--- Sample: {output_data[0]['criterion_id']} ---")
        first_criterion = output_data[0]
        print(f"Title: {first_criterion['title']}")
        print(f"Evidence items: {len(first_criterion['reranked_evidence'])}")
        if first_criterion['reranked_evidence']:
            first_evidence = first_criterion['reranked_evidence'][0]
            print(f"\nFirst evidence item:")
            print(f"  source_id: {first_evidence['source_id']}")
            print(f"  reranker_score: {first_evidence['reranker_score']:.4f}")
            print(f"  similarity_score: {first_evidence['similarity_score']:.4f}")
            print(f"  text (first 100 chars): {first_evidence['text'][:100]}...")

    print("\n" + "=" * 80)
    print("READY FOR GRADING")
    print("=" * 80)
    print(f"\nFile: {output_path.resolve()}")
    print("This file contains reranked evidence for all criteria.")
    print("Ready to be fed into LLM for grading process.")

    return True

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n✓ Extraction successful. Exiting preprocessing stage.")
            exit(0)
        else:
            print("\n✗ Extraction failed.")
            exit(1)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        exit(1)
