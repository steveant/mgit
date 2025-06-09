"""Integration tests for refactored commands."""

import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import pytest

from mgit.domain.models.operations import OperationType, UpdateMode, OperationOptions
from mgit.domain.models.context import OperationContext
from mgit.domain.models.repository import Repository
from mgit.application.services.bulk_operation_service import BulkOperationService
from mgit.application.container import DIContainer, reset_container
from mgit.infrastructure.event_bus import InMemoryEventBus


@pytest.fixture
def container():
    """Create a test container."""
    reset_container()
    container = DIContainer()
    yield container
    reset_container()


@pytest.fixture
def mock_repos():
    """Create mock repositories."""
    return [
        Repository(name="repo1", clone_url="https://example.com/repo1.git"),
        Repository(name="repo2", clone_url="https://example.com/repo2.git"),
        Repository(name="repo3", clone_url="https://example.com/repo3.git"),
    ]


@pytest.mark.asyncio
async def test_bulk_operation_service_clone_all(container, mock_repos, tmp_path):
    """Test BulkOperationService clone_all functionality."""
    # Create mocks
    mock_provider_adapter = Mock()
    mock_provider_adapter.list_repositories = Mock(return_value=mock_repos)
    
    mock_git_adapter = AsyncMock()
    mock_git_adapter.clone_repository = AsyncMock(return_value=True)
    mock_git_adapter.repository_exists = Mock(return_value=False)
    
    event_bus = InMemoryEventBus()
    
    # Create service
    service = BulkOperationService(
        provider_adapter=mock_provider_adapter,
        git_adapter=mock_git_adapter,
        event_bus=event_bus,
    )
    
    # Create context
    context = OperationContext(
        project="test-project",
        target_path=tmp_path,
        options=OperationOptions(
            concurrency=2,
            update_mode=UpdateMode.SKIP,
        ),
    )
    
    # Track events
    events_received = []
    event_bus.subscribe("BulkOperationStarted", lambda e: events_received.append(e))
    event_bus.subscribe("BulkOperationCompleted", lambda e: events_received.append(e))
    
    # Execute
    await service.clone_all(context)
    
    # Verify
    assert mock_provider_adapter.list_repositories.called
    assert mock_git_adapter.clone_repository.call_count == 3
    assert len(events_received) == 2  # Started and Completed
    assert events_received[0].__class__.__name__ == "BulkOperationStarted"
    assert events_received[1].__class__.__name__ == "BulkOperationCompleted"


@pytest.mark.asyncio
async def test_bulk_operation_service_pull_all(container, mock_repos, tmp_path):
    """Test BulkOperationService pull_all functionality."""
    # Create repository directories
    for repo in mock_repos:
        (tmp_path / repo.name).mkdir(parents=True)
    
    # Create mocks
    mock_provider_adapter = Mock()
    mock_provider_adapter.list_repositories = Mock(return_value=mock_repos)
    
    mock_git_adapter = AsyncMock()
    mock_git_adapter.pull_repository = AsyncMock(return_value=True)
    
    event_bus = InMemoryEventBus()
    
    # Create service
    service = BulkOperationService(
        provider_adapter=mock_provider_adapter,
        git_adapter=mock_git_adapter,
        event_bus=event_bus,
    )
    
    # Create context
    context = OperationContext(
        project="test-project",
        target_path=tmp_path,
        options=OperationOptions(
            concurrency=2,
            update_mode=UpdateMode.PULL,
        ),
    )
    
    # Execute
    await service.pull_all(context)
    
    # Verify
    assert mock_git_adapter.pull_repository.call_count == 3


def test_container_singleton_behavior(container):
    """Test that container provides singleton instances."""
    # Get instances multiple times
    config1 = container.config_manager
    config2 = container.config_manager
    
    provider1 = container.provider_manager
    provider2 = container.provider_manager
    
    # Verify same instances
    assert config1 is config2
    assert provider1 is provider2
    
    # Reset and verify new instances
    container.reset()
    config3 = container.config_manager
    assert config3 is not config1


def test_container_lazy_initialization(container):
    """Test that container initializes components lazily."""
    # Verify nothing is initialized yet
    assert container._config_manager is None
    assert container._provider_manager is None
    assert container._git_manager is None
    
    # Access one component
    _ = container.config_manager
    
    # Verify only that component is initialized
    assert container._config_manager is not None
    assert container._provider_manager is None
    assert container._git_manager is None


@pytest.mark.asyncio
async def test_event_bus_integration():
    """Test event bus publish/subscribe functionality."""
    event_bus = InMemoryEventBus()
    received_events = []
    
    # Subscribe to events
    event_bus.subscribe("TestEvent", lambda e: received_events.append(e))
    
    # Publish event
    class TestEvent:
        def __init__(self, data):
            self.data = data
    
    test_event = TestEvent("test_data")
    await event_bus.publish(test_event)
    
    # Verify
    assert len(received_events) == 1
    assert received_events[0].data == "test_data"


@pytest.mark.asyncio
async def test_operation_with_excludes(container, mock_repos, tmp_path):
    """Test bulk operation with excluded repositories."""
    # Create mocks
    mock_provider_adapter = Mock()
    mock_provider_adapter.list_repositories = Mock(return_value=mock_repos)
    
    mock_git_adapter = AsyncMock()
    mock_git_adapter.clone_repository = AsyncMock(return_value=True)
    mock_git_adapter.repository_exists = Mock(return_value=False)
    
    event_bus = InMemoryEventBus()
    
    # Create service
    service = BulkOperationService(
        provider_adapter=mock_provider_adapter,
        git_adapter=mock_git_adapter,
        event_bus=event_bus,
    )
    
    # Create context with excludes
    context = OperationContext(
        project="test-project",
        target_path=tmp_path,
        options=OperationOptions(
            concurrency=2,
            update_mode=UpdateMode.SKIP,
            exclude_repos=["repo2"],
        ),
    )
    
    # Execute
    await service.clone_all(context)
    
    # Verify repo2 was excluded
    assert mock_git_adapter.clone_repository.call_count == 2
    called_repos = [call[0][0].name for call in mock_git_adapter.clone_repository.call_args_list]
    assert "repo2" not in called_repos
    assert "repo1" in called_repos
    assert "repo3" in called_repos


@pytest.mark.asyncio
async def test_operation_with_includes(container, mock_repos, tmp_path):
    """Test bulk operation with included repositories only."""
    # Create mocks
    mock_provider_adapter = Mock()
    mock_provider_adapter.list_repositories = Mock(return_value=mock_repos)
    
    mock_git_adapter = AsyncMock()
    mock_git_adapter.clone_repository = AsyncMock(return_value=True)
    mock_git_adapter.repository_exists = Mock(return_value=False)
    
    event_bus = InMemoryEventBus()
    
    # Create service
    service = BulkOperationService(
        provider_adapter=mock_provider_adapter,
        git_adapter=mock_git_adapter,
        event_bus=event_bus,
    )
    
    # Create context with includes
    context = OperationContext(
        project="test-project",
        target_path=tmp_path,
        options=OperationOptions(
            concurrency=2,
            update_mode=UpdateMode.SKIP,
            include_repos=["repo1", "repo3"],
        ),
    )
    
    # Execute
    await service.clone_all(context)
    
    # Verify only included repos were processed
    assert mock_git_adapter.clone_repository.call_count == 2
    called_repos = [call[0][0].name for call in mock_git_adapter.clone_repository.call_args_list]
    assert "repo1" in called_repos
    assert "repo3" in called_repos
    assert "repo2" not in called_repos