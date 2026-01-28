"""Centralized logger configuration for retriever diagnostics.

This module provides a singleton logger that both pipeline.py and multi_retriever.py
use to write diagnostics to logs/retriever.log.
"""

import logging
import sys
from pathlib import Path

# Global logger instance - shared across all modules
_logger = None
_configured = False


def get_retriever_logger(module_name: str = "retriever"):
    """Get or create the centralized retriever logger.

    Args:
        module_name: Name for logging context (default: "retriever")

    Returns:
        Configured logger instance that writes to logs/retriever.log
    """
    global _logger, _configured

    if _logger is not None:
        return _logger

    # Create logger
    _logger = logging.getLogger("retriever_diagnostics")
    _logger.setLevel(logging.DEBUG)

    # Only configure once
    if _configured:
        return _logger

    _configured = True

    # Create logs directory with absolute path
    autograder_dir = Path(__file__).parent.parent
    logs_dir = autograder_dir / "logs"

    try:
        logs_dir.mkdir(exist_ok=True)
        print(f"[LOGGER_INIT] Logs directory: {logs_dir}", file=sys.stderr)
    except Exception as e:
        print(f"[LOGGER_INIT_ERROR] Failed to create logs directory: {e}", file=sys.stderr)
        return _logger

    # Create file handler with absolute path
    log_file = logs_dir / "retriever.log"

    try:
        # Remove any existing handlers to avoid duplicates
        for handler in _logger.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                _logger.removeHandler(handler)

        # Create new file handler
        file_handler = logging.FileHandler(log_file, mode='a')
        file_handler.setLevel(logging.DEBUG)  # Capture all levels

        # Create formatter
        formatter = logging.Formatter('%(levelname)s: %(message)s')
        file_handler.setFormatter(formatter)

        # Add handler
        _logger.addHandler(file_handler)

        print(f"[LOGGER_INIT] File handler configured: {log_file}", file=sys.stderr)
        print(f"[LOGGER_INIT] Handlers: {_logger.handlers}", file=sys.stderr)

        # Write initialization marker
        _logger.info("=" * 80)
        _logger.info(f"[LOGGER_INIT] Retriever logger initialized (autograder_dir={autograder_dir})")
        _logger.info(f"[LOGGER_INIT] Log file: {log_file}")
        _logger.info("=" * 80)

        # Force flush to ensure marker is written
        file_handler.flush()

    except Exception as e:
        print(f"[LOGGER_INIT_ERROR] Failed to configure file handler: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)

    return _logger
