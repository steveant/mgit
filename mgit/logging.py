#!/usr/bin/env python3
"""Logging configuration and setup for mgit."""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler


class MgitFormatter(logging.Formatter):
    """Formatter that removes PAT from the URL in logs."""

    def __init__(
        self,
        fmt=None,
        datefmt=None,
        style="%",
        validate=True,
    ):
        if fmt is None:
            fmt = "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s"
        super().__init__(
            fmt=fmt,
            datefmt=datefmt,
            style=style,
            validate=validate,
        )

    @staticmethod
    def _remove_pat(msg: str) -> str:
        pat = os.getenv("AZURE_DEVOPS_EXT_PAT")
        if not pat:
            return msg

        if "https://ado:" in msg:
            # Remove the PAT from the URL
            msg = msg.replace(
                "ado:" + pat,
                "ado:***",
            )
        elif "https://PersonalAccessToken:" in msg:
            # Remove the PAT from the URL
            msg = msg.replace(
                "https://PersonalAccessToken:" + pat,
                "https://PersonalAccessToken:***",
            )
        return msg

    def format(self, record):
        # Update the record so that %(message)s uses the filtered text
        record.msg = self._remove_pat(record.getMessage())
        record.args = None
        return super().format(record)


class ConsoleFriendlyRichHandler(RichHandler):
    """Enhanced Rich handler that formats long messages better for console display."""

    def emit(self, record):
        # Format repository URLs in a more readable way
        if record.levelname == "INFO":
            msg = str(record.msg)

            # Handle repository cloning messages
            if "Cloning repository:" in msg:
                # Extract repository name from URL
                if "_git/" in msg:
                    try:
                        # Extract repo name from URL pattern
                        repo_name = msg.split("_git/")[1].split(" into")[0]
                        # Truncate long repo names
                        if len(repo_name) > 40:
                            repo_name = repo_name[:37] + "..."
                        # Format message to be more concise
                        shortened_url = f"Cloning: [bold blue]{repo_name}[/bold blue]"
                        record.msg = shortened_url
                    except Exception:
                        # If parsing fails, keep original message
                        pass

            # Handle skipping disabled repositories message
            elif "Skipping disabled repository:" in msg:
                try:
                    repo_name = msg.split("Skipping disabled repository:")[1].strip()
                    # Truncate long repo names
                    if len(repo_name) > 40:
                        repo_name = repo_name[:37] + "..."
                    record.msg = f"Skipping disabled: [bold yellow]{repo_name}[/bold yellow]"
                except Exception:
                    pass

        # Call the parent class's emit method
        super().emit(record)


def setup_logging(config_dir: Path, log_filename: str, log_level: str, console_level: str) -> logging.Logger:
    """
    Set up logging configuration for mgit.
    
    Args:
        config_dir: Directory for log files
        log_filename: Name of the log file
        log_level: Logging level for file handler
        console_level: Logging level for console handler
        
    Returns:
        Configured logger instance
    """
    # Ensure config directory exists
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # Set up file handler
    log_path = config_dir / log_filename
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=5_000_000,
        backupCount=3,
    )
    file_handler.setFormatter(MgitFormatter())
    
    # Set up console handler
    console_handler = ConsoleFriendlyRichHandler(
        rich_tracebacks=True,
        markup=True,
        show_path=False,  # Hide the file path in log messages
        show_time=False,  # Hide timestamp (already in the formatter)
    )
    console_handler.setLevel(console_level)
    
    # Configure logger
    logger = logging.getLogger(__name__)
    logger.setLevel(log_level)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger