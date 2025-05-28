#!/usr/bin/env python3
"""
CLI module for mgit - Multi-Git CLI Tool

This module handles the CLI setup, including the main Typer app instance,
version callback, and main options configuration.
"""

from typing import Optional
import typer

# Import from constants module
from mgit.constants import __version__

# Initialize the main Typer app
app = typer.Typer(
    name="mgit",
    help=f"Multi-Git CLI Tool v{__version__} - A utility for managing repositories across "
    "multiple git platforms (Azure DevOps, GitHub, BitBucket) with bulk operations.",
    add_completion=False,
    no_args_is_help=True,
)

def version_callback(value: bool):
    """Display the application version and exit."""
    if value:
        print(f"mgit version: {__version__}")
        raise typer.Exit()

@app.callback()
def main_options(
    version: Optional[bool] = typer.Option(
        None, "--version", callback=version_callback, is_eager=True,
        help="Show the application's version and exit."
    )
):
    """
    Multi-Git CLI Tool - Manage repos across multiple git platforms easily.
    """
    pass