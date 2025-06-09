"""Configuration manager for backwards compatibility."""

from pathlib import Path
from typing import Dict, Any

from . import (
    get_global_config,
    get_provider_configs,
    add_provider_config,
    set_global_setting,
    CONFIG_FILE,
)


class ConfigManager:
    """Wrapper around YAML configuration for backwards compatibility."""
    
    def __init__(self):
        """Initialize the config manager."""
        self.config_path = Path(CONFIG_FILE)
    
    @property
    def config(self) -> Dict[str, Any]:
        """Get the full configuration."""
        config = get_global_config()
        
        # Add provider configs with backwards-compatible keys
        providers = get_provider_configs()
        for provider_name, provider_config in providers.items():
            # Convert provider names to old format
            if provider_name == "azure-devops":
                config["azure_devops"] = provider_config
            elif provider_name == "github":
                config["github"] = provider_config
            elif provider_name == "bitbucket":
                config["bitbucket"] = provider_config
        
        return config
    
    def save_config(self, config: Dict[str, Any]) -> None:
        """Save configuration."""
        # Save global settings
        for key, value in config.items():
            if key not in ["azure_devops", "github", "bitbucket"]:
                set_global_setting(key, value)
        
        # Save provider configs
        if "azure_devops" in config:
            add_provider_config("azure-devops", config["azure_devops"])
        if "github" in config:
            add_provider_config("github", config["github"])
        if "bitbucket" in config:
            add_provider_config("bitbucket", config["bitbucket"])