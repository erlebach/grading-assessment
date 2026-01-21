from pathlib import Path
from grading_dynamic_rubrics.pipeline import print_index_diagnostics

# Uses defaults: config from grading_dynamic_rubrics/config/sources.yaml
# and persist_dir from grading_dynamic_rubrics/tmp/in_memory_indexes/
print_index_diagnostics()

"""
# Or specify custom paths:
print_index_diagnostics(
    config_path=Path("path/to/sources.yaml"),
    persist_dir=Path("grading_dynamic_rubrics/tmp/in_memory/"),  # if different
    index_subset=["word_index", "sentence_index"],  # optional subset
)
"""
