"""Adapter for repository providers using existing ProviderManager."""

from typing import AsyncIterator, Optional

from mgit.application.ports import RepositoryProvider
from mgit.domain.models.repository import Repository
from mgit.providers.manager_v2 import ProviderManager


class ProviderManagerAdapter(RepositoryProvider):
    """Adapts the existing ProviderManager to the RepositoryProvider interface."""
    
    def __init__(self, provider_manager: ProviderManager):
        self._provider_manager = provider_manager
    
    async def list_repositories(
        self,
        project: str,
        pattern: Optional[str] = None
    ) -> AsyncIterator[Repository]:
        """List repositories in a project/organization."""
        # Use the existing provider manager's list_repositories method
        async for repo in self._provider_manager.list_repositories(project):
            # Convert provider-specific repository to domain model
            yield Repository(
                name=repo.name,
                clone_url=repo.clone_url,
                organization=repo.organization,
                project=repo.project,
                is_disabled=repo.is_disabled,
                default_branch=repo.default_branch
            )
    
    def get_authenticated_clone_url(self, repository: Repository) -> str:
        """Get clone URL with embedded authentication."""
        # Convert domain repository back to provider repository for this call
        # This is a bit of a hack but maintains compatibility
        class RepoAdapter:
            def __init__(self, domain_repo):
                self.name = domain_repo.name
                self.clone_url = domain_repo.clone_url
                self.organization = domain_repo.organization
                self.project = domain_repo.project
                self.is_disabled = domain_repo.is_disabled
                self.default_branch = domain_repo.default_branch
        
        adapted_repo = RepoAdapter(repository)
        return self._provider_manager.get_authenticated_clone_url(adapted_repo)
    
    async def test_connection(self) -> bool:
        """Test if the provider connection is working."""
        return self._provider_manager.test_connection()
    
    def supports_provider(self) -> bool:
        """Check if this provider is fully supported."""
        return self._provider_manager.supports_provider()
    
    @property
    def provider_type(self) -> str:
        """Get the provider type name."""
        return self._provider_manager.provider_type
    
    @property
    def provider_name(self) -> str:
        """Get the configured provider name."""
        return self._provider_manager.provider_name