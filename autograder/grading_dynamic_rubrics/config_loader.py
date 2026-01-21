"""Configuration loader for dynamic rubrics grading pipeline.

This module re-exports config loading functions from grading_pipeline.
No changes needed as the config format is the same.

"""

from grading_pipeline.config_loader import get_rubric_path, load_rubric_config

__all__ = ["load_rubric_config", "get_rubric_path"]
