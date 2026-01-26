"""
JSON schema exports from Pydantic models.

Provides JSON schema definitions for API documentation and validation.
"""

from typing import Any
import json
from pathlib import Path

from .models import (
    Check,
    Rubric,
    CheckEvaluation,
    GradeResult,
    Appeal,
    GradeCalculation,
    CheckCategory,
    CheckEvaluationResult,
)


def get_check_schema() -> dict[str, Any]:
    """Get JSON schema for Check model."""
    return Check.schema()


def get_rubric_schema() -> dict[str, Any]:
    """Get JSON schema for Rubric model."""
    return Rubric.schema()


def get_check_evaluation_schema() -> dict[str, Any]:
    """Get JSON schema for CheckEvaluation model."""
    return CheckEvaluation.schema()


def get_grade_calculation_schema() -> dict[str, Any]:
    """Get JSON schema for GradeCalculation model."""
    return GradeCalculation.schema()


def get_grade_result_schema() -> dict[str, Any]:
    """Get JSON schema for GradeResult model."""
    return GradeResult.schema()


def get_appeal_schema() -> dict[str, Any]:
    """Get JSON schema for Appeal model."""
    return Appeal.schema()


def get_all_schemas() -> dict[str, dict[str, Any]]:
    """Get all JSON schemas."""
    return {
        "Check": get_check_schema(),
        "Rubric": get_rubric_schema(),
        "CheckEvaluation": get_check_evaluation_schema(),
        "GradeCalculation": get_grade_calculation_schema(),
        "GradeResult": get_grade_result_schema(),
        "Appeal": get_appeal_schema(),
    }


def save_schemas_to_file(output_dir: str = "docs/schemas") -> None:
    """
    Save all JSON schemas to individual files.

    Args:
        output_dir: Directory to save schema files

    Creates:
        - {output_dir}/Check.schema.json
        - {output_dir}/Rubric.schema.json
        - {output_dir}/CheckEvaluation.schema.json
        - {output_dir}/GradeCalculation.schema.json
        - {output_dir}/GradeResult.schema.json
        - {output_dir}/Appeal.schema.json
        - {output_dir}/all_schemas.json
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    schemas = get_all_schemas()

    # Save individual schemas
    for schema_name, schema in schemas.items():
        file_path = output_path / f"{schema_name}.schema.json"
        with open(file_path, "w") as f:
            json.dump(schema, f, indent=2)
        print(f"✓ Saved schema: {file_path}")

    # Save all schemas combined
    combined_path = output_path / "all_schemas.json"
    with open(combined_path, "w") as f:
        json.dump(schemas, f, indent=2)
    print(f"✓ Saved combined schemas: {combined_path}")


if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "export":
        output_dir = sys.argv[2] if len(sys.argv) > 2 else "docs/schemas"
        save_schemas_to_file(output_dir)
    else:
        # Print schema info
        schemas = get_all_schemas()
        print("Available schemas:")
        for name in schemas.keys():
            print(f"  - {name}")

        if len(sys.argv) > 1:
            schema_name = sys.argv[1]
            if schema_name in schemas:
                schema = schemas[schema_name]
                print(f"\n{schema_name} schema:")
                print(json.dumps(schema, indent=2))
            else:
                print(f"Schema '{schema_name}' not found")
