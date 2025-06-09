"""Operation context for managing state during bulk operations."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Set, Dict, Optional
from uuid import UUID

from .operations import OperationOptions, OperationError
from .repository import Repository, RepositoryOperation


@dataclass
class OperationContext:
    """Encapsulates all state for a bulk operation.
    
    This replaces the closure-based state management in the original code.
    """
    project: str
    target_path: Path
    options: OperationOptions
    operations: List[RepositoryOperation] = field(default_factory=list)
    errors: List[OperationError] = field(default_factory=list)
    confirmed_actions: Set[str] = field(default_factory=set)
    
    # Tracking state previously held in closures
    directories_to_remove: List[tuple[str, str, Path]] = field(default_factory=list)
    operation_tasks: Dict[str, UUID] = field(default_factory=dict)
    
    def add_operation(self, operation: RepositoryOperation) -> None:
        """Add a repository operation to the context."""
        self.operations.append(operation)
    
    def record_error(self, error: OperationError) -> None:
        """Record an operation error."""
        self.errors.append(error)
    
    def confirm_action(self, action: str) -> None:
        """Record a user-confirmed action."""
        self.confirmed_actions.add(action)
    
    def is_action_confirmed(self, action: str) -> bool:
        """Check if an action has been confirmed."""
        return action in self.confirmed_actions
    
    def add_directory_to_remove(self, repo_name: str, sanitized_name: str, path: Path) -> None:
        """Add a directory to the removal list."""
        self.directories_to_remove.append((repo_name, sanitized_name, path))
    
    def get_operation_for_repository(self, repo_name: str) -> Optional[RepositoryOperation]:
        """Get the operation for a specific repository."""
        for op in self.operations:
            if op.repository.name == repo_name:
                return op
        return None