"""Backwards compatibility wrapper for logger module."""

import logging
from typing import Optional

# Import from the actual logger module
from .logger import get_structured_logger, setup_structured_logging


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return get_structured_logger(name)


def configure_logging(level: Optional[str] = None) -> None:
    """Configure logging with the specified level."""
    if level is None:
        level = "INFO"
    
    # Use the new setup_structured_logging function
    setup_structured_logging(
        log_level=level,
        log_file=None,
        json_format=False,  # Use simple format for CLI
        include_correlation=False,
        mask_credentials=True
    )