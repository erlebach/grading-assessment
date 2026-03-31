"""Pytest configuration for autograder tests."""
import sys
from pathlib import Path

# Add the autograder directory to sys.path BEFORE pytest does anything
# This runs at conftest import time, before pytest tries to collect tests
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
