"""Configuration management module for mgit."""

from .manager import (
    CONFIG_DIR,
    CONFIG_FILE,
    get_config_value,
    load_config_file,
    save_config_file,
)

__all__ = [
    "CONFIG_DIR",
    "CONFIG_FILE",
    "get_config_value",
    "load_config_file",
    "save_config_file",
]