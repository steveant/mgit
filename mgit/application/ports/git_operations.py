"""Git operations interface."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, List, Any


class GitOperations(ABC):
    """Interface for Git operations."""
    
    @abstractmethod
    async def clone_repository(
        self, 
        repository: Any,  # Repository model
        target_path: Path
    ) -> bool:
        """Clone a repository."""
        pass
    
    @abstractmethod
    async def pull_repository(self, repo_path: Path) -> bool:
        """Pull latest changes in a repository."""
        pass
    
    @abstractmethod
    async def fetch(self, repo_path: Path) -> None:
        """Fetch remote changes without merging."""
        pass
    
    @abstractmethod
    async def get_status(self, repo_path: Path) -> Dict[str, Any]:
        """Get repository status information."""
        pass
    
    @abstractmethod
    def repository_exists(self, path: Path) -> bool:
        """Check if a path is a Git repository."""
        pass