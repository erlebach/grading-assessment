"""Generate citations for grading evidence."""

from typing import Any


def generate_citation(
    evidence_text: str,
    source: str,
    location: str | None = None,
) -> dict[str, Any]:
    """Generate a citation for grading evidence.

    Args:
        evidence_text: The text evidence being cited.
        source: Source identifier (e.g., file path, document ID).
        location: Optional location within source (e.g., line numbers).

    Returns:
        Dictionary containing citation information:
        - text: The evidence text
        - source: Source identifier
        - location: Location within source (if provided)

    """
    citation = {
        "text": evidence_text,
        "source": source,
    }

    if location:
        citation["location"] = location

    return citation


def format_citation(citation: dict[str, Any]) -> str:
    """Format a citation as a human-readable string.

    Args:
        citation: Citation dictionary from generate_citation.

    Returns:
        Formatted citation string.

    """
    parts = [citation["source"]]
    if "location" in citation:
        parts.append(f"({citation['location']})")
    return ": ".join(parts)
