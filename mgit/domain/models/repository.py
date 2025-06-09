"""Domain models for repositories."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .operations import OperationType, OperationStatus


@dataclass
class Repository:
    """Domain model for a repository.
    
    This is a simplified version that doesn't depend on provider-specific models.
    """
    name: str
    clone_url: str
    organization: str
    project: Optional[str] = None
    is_disabled: bool = False
    default_branch: Optional[str] = None
    
    @property
    def full_name(self) -> str:
        """Get the full repository name including organization/project."""
        if self.project:
            return f"{self.organization}/{self.project}/{self.name}"
        return f"{self.organization}/{self.name}"


@dataclass
class RepositoryOperation:
    """Represents a single repository operation."""
    repository: Repository
    operation_type: OperationType
    target_path: Path
    status: OperationStatus = OperationStatus.PENDING
    error: Optional[str] = None
    
    @property
    def is_complete(self) -> bool:
        return self.status in (
            OperationStatus.COMPLETED,
            OperationStatus.FAILED,
            OperationStatus.SKIPPED
        )
    
    @property
    def is_successful(self) -> bool:
        return self.status == OperationStatus.COMPLETED