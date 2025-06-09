"""Dependency injection container for application services."""

from typing import Optional

from mgit.config import ConfigManager
from mgit.providers.manager_v2 import ProviderManager
from mgit.git.manager import GitManager
from mgit.monitoring.logger_compat import get_logger
from mgit.infrastructure.event_bus import InMemoryEventBus
from mgit.infrastructure.adapters.git_adapter import GitManagerAdapter
from mgit.infrastructure.adapters.provider_adapter import ProviderManagerAdapter
from mgit.application.services.bulk_operation_service import BulkOperationService
from mgit.application.ports import EventBus, GitOperations, ProviderOperations


logger = get_logger(__name__)


class DIContainer:
    """Dependency injection container for application components."""
    
    def __init__(self):
        """Initialize the container."""
        self._config_manager: Optional[ConfigManager] = None
        self._provider_manager: Optional[ProviderManager] = None
        self._git_manager: Optional[GitManager] = None
        self._event_bus: Optional[EventBus] = None
        self._git_adapter: Optional[GitOperations] = None
        self._provider_adapter: Optional[ProviderOperations] = None
        self._bulk_operation_service: Optional[BulkOperationService] = None
    
    @property
    def config_manager(self) -> ConfigManager:
        """Get or create ConfigManager instance."""
        if self._config_manager is None:
            logger.debug("Creating ConfigManager instance")
            self._config_manager = ConfigManager()
        return self._config_manager
    
    @property
    def provider_manager(self) -> ProviderManager:
        """Get or create ProviderManager instance."""
        if self._provider_manager is None:
            logger.debug("Creating ProviderManager instance")
            self._provider_manager = ProviderManager(self.config_manager.config)
        return self._provider_manager
    
    @property
    def git_manager(self) -> GitManager:
        """Get or create GitManager instance."""
        if self._git_manager is None:
            logger.debug("Creating GitManager instance")
            self._git_manager = GitManager()
        return self._git_manager
    
    @property
    def event_bus(self) -> EventBus:
        """Get or create EventBus instance."""
        if self._event_bus is None:
            logger.debug("Creating EventBus instance")
            self._event_bus = InMemoryEventBus()
        return self._event_bus
    
    @property
    def git_adapter(self) -> GitOperations:
        """Get or create GitOperations adapter."""
        if self._git_adapter is None:
            logger.debug("Creating GitOperations adapter")
            self._git_adapter = GitManagerAdapter(self.git_manager)
        return self._git_adapter
    
    @property
    def provider_adapter(self) -> ProviderOperations:
        """Get or create ProviderOperations adapter."""
        if self._provider_adapter is None:
            logger.debug("Creating ProviderOperations adapter")
            self._provider_adapter = ProviderManagerAdapter(self.provider_manager)
        return self._provider_adapter
    
    @property
    def bulk_operation_service(self) -> BulkOperationService:
        """Get or create BulkOperationService instance."""
        if self._bulk_operation_service is None:
            logger.debug("Creating BulkOperationService instance")
            self._bulk_operation_service = BulkOperationService(
                provider_adapter=self.provider_adapter,
                git_adapter=self.git_adapter,
                event_bus=self.event_bus,
            )
        return self._bulk_operation_service
    
    def reset(self) -> None:
        """Reset all cached instances."""
        logger.debug("Resetting DI container")
        self._config_manager = None
        self._provider_manager = None
        self._git_manager = None
        self._event_bus = None
        self._git_adapter = None
        self._provider_adapter = None
        self._bulk_operation_service = None


# Global container instance
_container: Optional[DIContainer] = None


def get_container() -> DIContainer:
    """Get the global DI container instance."""
    global _container
    if _container is None:
        _container = DIContainer()
    return _container


def reset_container() -> None:
    """Reset the global DI container."""
    global _container
    if _container is not None:
        _container.reset()
    _container = None