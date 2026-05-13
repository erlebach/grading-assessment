"""Test configuration for the grading plugin's Python helpers.

Adds the repo root to sys.path so tests can `from plugins.grading.python...`.
This is redundant with the pyproject pytest pythonpath setting but makes
direct file invocations work too.
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
