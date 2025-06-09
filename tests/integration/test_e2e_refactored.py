"""End-to-end tests for the refactored architecture using real config."""

import os
import asyncio
from pathlib import Path
import pytest
from unittest.mock import patch

from mgit.application.container import get_container, reset_container
from mgit.domain.models.operations import OperationType, UpdateMode, OperationOptions
from mgit.domain.models.context import OperationContext
from mgit.presentation.cli.commands import bulk_ops


@pytest.fixture
def container():
    """Get test container."""
    reset_container()
    container = get_container()
    yield container
    reset_container()


@pytest.mark.integration
@pytest.mark.skipif(
    not os.path.exists(os.path.expanduser("~/.config/mgit/config.yaml")),
    reason="No mgit config found"
)
def test_list_projects_with_real_config(container):
    """Test listing projects with real configuration."""
    # This uses the real config from ~/.config/mgit/config.yaml
    provider_manager = container.provider_manager
    
    # Try to list projects from configured providers
    configured_providers = []
    config = container.config_manager.config
    
    if config.get("azure_devops", {}).get("pat"):
        configured_providers.append("azure-devops")
    if config.get("github", {}).get("token"):
        configured_providers.append("github") 
    if config.get("bitbucket", {}).get("pat"):
        configured_providers.append("bitbucket")
    
    assert len(configured_providers) > 0, "No providers configured"
    
    # Test listing projects from first configured provider
    provider = configured_providers[0]
    projects = provider_manager.list_projects(provider=provider)
    
    # Should return a list (even if empty)
    assert isinstance(projects, list)


@pytest.mark.integration
@pytest.mark.skipif(
    not os.path.exists(os.path.expanduser("~/.config/mgit/config.yaml")),
    reason="No mgit config found"
)
@pytest.mark.asyncio
async def test_bulk_operation_service_with_real_provider(container, tmp_path):
    """Test bulk operation service with real provider (dry run)."""
    service = container.bulk_operation_service
    
    # Get first configured project
    provider_manager = container.provider_manager
    config = container.config_manager.config
    
    # Find first configured provider
    project = None
    for provider in ["azure_devops", "github", "bitbucket"]:
        if config.get(provider, {}).get("pat") or config.get(provider, {}).get("token"):
            projects = provider_manager.list_projects(provider=provider.replace("_", "-"))
            if projects:
                project = projects[0]
                break
    
    if not project:
        pytest.skip("No projects found in configured providers")
    
    # Create context for dry run
    context = OperationContext(
        project=project,
        target_path=tmp_path,
        options=OperationOptions(
            concurrency=1,
            update_mode=UpdateMode.SKIP,
            dry_run=True,  # Don't actually clone
        ),
    )
    
    # Test clone operation (dry run)
    result = await service.clone_all(context)
    
    # Should complete without errors
    assert result is not None
    assert result.total_repositories >= 0


@pytest.mark.integration 
def test_cli_login_command(tmp_path):
    """Test the login CLI command."""
    from typer.testing import CliRunner
    from mgit.__main__ import app
    
    runner = CliRunner()
    
    # Mock the config save to avoid modifying real config
    with patch("mgit.config.ConfigManager.save_config") as mock_save:
        result = runner.invoke(
            app,
            ["login", "--org", "https://github.com/test-org", "--token", "test-token"]
        )
        
        assert result.exit_code == 0
        assert "Successfully configured github authentication" in result.output
        mock_save.assert_called_once()


@pytest.mark.integration
def test_cli_list_projects_command():
    """Test the list-projects CLI command.""" 
    from typer.testing import CliRunner
    from mgit.__main__ import app
    
    runner = CliRunner()
    
    result = runner.invoke(app, ["list-projects"])
    
    # Should complete (might show "No providers configured" if no config)
    assert result.exit_code == 0


@pytest.mark.integration
def test_modular_architecture_imports():
    """Test that all modular components can be imported."""
    # Domain layer
    from mgit.domain.models.operations import OperationType, UpdateMode
    from mgit.domain.models.repository import Repository
    from mgit.domain.models.context import OperationContext
    from mgit.domain.events import BulkOperationStarted
    
    # Application layer
    from mgit.application.services.bulk_operation_service import BulkOperationService
    from mgit.application.container import DIContainer
    from mgit.application.ports import EventBus, GitOperations, ProviderOperations
    
    # Infrastructure layer
    from mgit.infrastructure.event_bus import InMemoryEventBus
    from mgit.infrastructure.adapters.git_adapter import GitManagerAdapter
    from mgit.infrastructure.adapters.provider_adapter import ProviderManagerAdapter
    
    # Presentation layer
    from mgit.presentation.cli.commands.bulk_ops import clone_all, pull_all
    from mgit.presentation.cli.progress.progress_handler import CliProgressHandler
    
    # All imports should succeed
    assert True