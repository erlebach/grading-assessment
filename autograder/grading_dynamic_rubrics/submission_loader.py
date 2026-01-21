"""Submission loader for dynamic rubrics grading pipeline.

This module re-exports submission loading functions from grading_pipeline.
No changes needed as the submission format is the same.

"""

from grading_pipeline.submission_loader import (
    load_all_submissions_for_question,
    load_submission,
)

__all__ = ["load_submission", "load_all_submissions_for_question"]
