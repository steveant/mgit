"""Repository provider interface."""

from abc import ABC, abstractmethod
from typing import List, Optional

from mgit.domain.models.repository import Repository


class ProviderOperations(ABC):
    """Interface for repository providers (GitHub, Azure DevOps, BitBucket)."""
    
    @abstractmethod
    def list_repositories(self, project: str) -> List[Repository]:
        """List repositories in a project/organization."""
        pass
    
    @abstractmethod
    def get_authenticated_clone_url(self, repository: Repository) -> str:
        """Get clone URL with embedded authentication."""
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """Test if the provider connection is working."""
        pass
    
    @abstractmethod
    def supports_provider(self) -> bool:
        """Check if this provider is fully supported."""
        pass
    
    @property
    @abstractmethod
    def provider_type(self) -> str:
        """Get the provider type name."""
        pass
    
    @property
    @abstractmethod 
    def provider_name(self) -> str:
        """Get the configured provider name."""
        pass