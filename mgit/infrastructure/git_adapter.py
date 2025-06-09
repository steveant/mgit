"""Adapter for Git operations using existing GitManager."""

from pathlib import Path
from typing import Optional, Dict, Any
import subprocess

from mgit.application.ports import GitOperations
from mgit.git import GitManager


class GitManagerAdapter(GitOperations):
    """Adapts the existing GitManager to the GitOperations interface."""
    
    def __init__(self):
        self._git_manager = GitManager()
    
    async def clone(
        self,
        url: str,
        target_path: Path,
        directory_name: Optional[str] = None
    ) -> None:
        """Clone a repository."""
        await self._git_manager.git_clone(url, target_path, directory_name)
    
    async def pull(self, repo_path: Path) -> None:
        """Pull latest changes in a repository."""
        await self._git_manager.git_pull(repo_path)
    
    async def fetch(self, repo_path: Path) -> None:
        """Fetch remote changes without merging."""
        # The existing GitManager doesn't have fetch, so we'll implement it
        proc = await self._git_manager._run_git_command(
            ["fetch", "--all"],
            cwd=repo_path
        )
        if proc.returncode != 0:
            raise subprocess.CalledProcessError(
                proc.returncode,
                "git fetch",
                stderr=proc.stderr
            )
    
    async def get_status(self, repo_path: Path) -> Dict[str, Any]:
        """Get repository status information."""
        # This would need to be implemented based on the status command logic
        # For now, return a basic status
        return {
            "path": str(repo_path),
            "clean": True,  # Would need actual implementation
            "branch": "main"  # Would need actual implementation
        }
    
    def is_git_repository(self, path: Path) -> bool:
        """Check if a path is a Git repository."""
        return (path / ".git").exists()