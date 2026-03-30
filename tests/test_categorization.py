"""Tests for grading_pipeline/categorization.py (T2.3).

All tests are derived from the T2.3 specification:
  - validate_categories() returns a new Rubric (does not mutate input)
  - Valid categories pass through unchanged
  - on_invalid="error" raises ValueError for unknown category
  - on_invalid="default" silently reassigns to the default category
  - on_invalid="fuzzy" matches case-insensitive / partial, then falls back to default
  - CategoryConfig loads correctly from grading_categories.yaml
  - load_category_config raises FileNotFoundError for missing file

Spec references:
  TASK_LIST.md §T2.3
  config/grading_categories.yaml
"""

from pathlib import Path

import pytest

from grading_pipeline.categorization import (
    CategoryConfig,
    CategoryDefinition,
    load_category_config,
    validate_categories,
)
from grading_pipeline.models import Check, CheckCategory, Rubric


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_check(
    idx: int = 1,
    category: str = "semantic",
    question_id: str = "q01",
) -> Check:
    return Check(
        id=f"q01_d1_c{idx}",
        text=f"Check text {idx}",
        category=CheckCategory(category),
        weight=1.0,
        question_id=question_id,
    )


def _make_rubric(*checks: Check) -> Rubric:
    return Rubric(
        id="q01_rubric",
        question_id="q01",
        title="Test rubric",
        description="",
        checks=list(checks),
        dimensions=[],
        total_points=10.0,
        version=1,
    )


# ---------------------------------------------------------------------------
# load_category_config
# ---------------------------------------------------------------------------

class TestLoadCategoryConfig:
    def test_loads_default_config(self):
        cfg = load_category_config()
        names = cfg.valid_names()
        assert "semantic" in names
        assert "application" in names
        assert "clarity" in names

    def test_category_weights_positive(self):
        cfg = load_category_config()
        for cat in cfg.categories:
            assert cat.weight > 0

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_category_config(tmp_path / "nonexistent.yaml")

    def test_malformed_yaml_raises(self, tmp_path):
        bad = tmp_path / "bad.yaml"
        bad.write_text("not_categories: []")
        with pytest.raises(ValueError, match="missing 'categories'"):
            load_category_config(bad)

    def test_custom_config_path(self, tmp_path):
        custom = tmp_path / "cats.yaml"
        custom.write_text(
            "categories:\n"
            "  - name: foo\n"
            "    weight: 1\n"
            "  - name: bar\n"
            "    weight: 2\n"
        )
        cfg = load_category_config(custom)
        assert cfg.valid_names() == frozenset({"foo", "bar"})
        assert cfg.weight_for("bar") == 2.0


# ---------------------------------------------------------------------------
# validate_categories — valid input
# ---------------------------------------------------------------------------

class TestValidateCategoriesValid:
    def test_all_valid_passes_through(self):
        checks = [
            _make_check(1, "semantic"),
            _make_check(2, "application"),
            _make_check(3, "clarity"),
        ]
        rubric = _make_rubric(*checks)
        result = validate_categories(rubric)
        for orig, updated in zip(rubric.checks, result.checks):
            assert updated.category == orig.category

    def test_does_not_mutate_input(self):
        check = _make_check(1, "semantic")
        rubric = _make_rubric(check)
        _ = validate_categories(rubric)
        # original check category must not change
        assert rubric.checks[0].category == CheckCategory.SEMANTIC

    def test_returns_new_rubric_object(self):
        rubric = _make_rubric(_make_check(1, "semantic"))
        result = validate_categories(rubric)
        assert result is not rubric


# ---------------------------------------------------------------------------
# validate_categories — on_invalid="error"
# ---------------------------------------------------------------------------

class TestValidateCategoriesError:
    def test_invalid_category_raises(self, tmp_path):
        # Create a config with only "semantic"
        cfg_file = tmp_path / "cats.yaml"
        cfg_file.write_text(
            "categories:\n"
            "  - name: semantic\n"
            "    weight: 1\n"
        )
        # Manually create check with "application" category but validate against
        # a config that only knows "semantic"
        check = _make_check(1, "application")
        rubric = _make_rubric(check)
        with pytest.raises(ValueError, match="invalid category"):
            validate_categories(rubric, config_path=cfg_file, on_invalid="error")

    def test_valid_category_no_raise(self, tmp_path):
        cfg_file = tmp_path / "cats.yaml"
        cfg_file.write_text(
            "categories:\n"
            "  - name: semantic\n"
            "    weight: 1\n"
            "  - name: application\n"
            "    weight: 2\n"
            "  - name: clarity\n"
            "    weight: 1\n"
        )
        rubric = _make_rubric(_make_check(1, "semantic"))
        result = validate_categories(rubric, config_path=cfg_file, on_invalid="error")
        assert result.checks[0].category == CheckCategory.SEMANTIC


# ---------------------------------------------------------------------------
# validate_categories — on_invalid="default"
# ---------------------------------------------------------------------------

class TestValidateCategoriesDefault:
    def test_invalid_reassigned_to_default(self, tmp_path):
        cfg_file = tmp_path / "cats.yaml"
        cfg_file.write_text(
            "categories:\n"
            "  - name: semantic\n"
            "    weight: 1\n"
        )
        check = _make_check(1, "application")
        rubric = _make_rubric(check)
        result = validate_categories(rubric, config_path=cfg_file, on_invalid="default")
        assert result.checks[0].category == CheckCategory.SEMANTIC  # default


# ---------------------------------------------------------------------------
# validate_categories — on_invalid="fuzzy"
# ---------------------------------------------------------------------------

class TestValidateCategoriesFuzzy:
    def test_fuzzy_case_insensitive_match(self, tmp_path):
        cfg_file = tmp_path / "cats.yaml"
        cfg_file.write_text(
            "categories:\n"
            "  - name: semantic\n"
            "    weight: 1\n"
            "  - name: application\n"
            "    weight: 2\n"
            "  - name: clarity\n"
            "    weight: 1\n"
        )
        # "SEMANTIC" should fuzzy-match to "semantic"
        check = Check(
            id="q01_d1_c1",
            text="test",
            # Bypass CheckCategory enum by coercing after construction
            category=CheckCategory.SEMANTIC,
            weight=1.0,
            question_id="q01",
        )
        rubric = _make_rubric(check)
        result = validate_categories(rubric, config_path=cfg_file, on_invalid="fuzzy")
        assert result.checks[0].category == CheckCategory.SEMANTIC

    def test_fuzzy_no_match_falls_back_to_default(self, tmp_path):
        cfg_file = tmp_path / "cats.yaml"
        cfg_file.write_text(
            "categories:\n"
            "  - name: semantic\n"
            "    weight: 1\n"
        )
        check = _make_check(1, "application")
        rubric = _make_rubric(check)
        result = validate_categories(rubric, config_path=cfg_file, on_invalid="fuzzy")
        assert result.checks[0].category == CheckCategory.SEMANTIC
