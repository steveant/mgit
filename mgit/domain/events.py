"""Domain events for decoupling components."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from .models.operations import OperationType, OperationStatus
from .models.repository import Repository


# Base class without dataclass decorator to avoid field ordering issues
class Event:
    """Base class for all domain events."""
    def __init__(self):
        self.event_id: UUID = uuid4()
        self.timestamp: datetime = datetime.now()


@dataclass
class BulkOperationStarted(Event):
    """Emitted when a bulk operation starts."""
    operation_type: OperationType
    project: str
    total_repositories: int
    
    def __post_init__(self):
        super().__init__()


@dataclass 
class BulkOperationCompleted(Event):
    """Emitted when a bulk operation completes."""
    operation_type: OperationType
    project: str
    successful: int
    failed: int
    skipped: int
    
    def __post_init__(self):
        super().__init__()


@dataclass
class RepositoryOperationStarted(Event):
    """Emitted when a single repository operation starts."""
    operation_id: UUID
    repository: Repository
    operation_type: OperationType
    
    def __post_init__(self):
        super().__init__()


@dataclass
class RepositoryOperationProgress(Event):
    """Emitted to report progress on a repository operation."""
    operation_id: UUID
    repository_name: str
    message: str
    
    def __post_init__(self):
        super().__init__()


@dataclass
class RepositoryOperationCompleted(Event):
    """Emitted when a repository operation completes successfully."""
    operation_id: UUID
    repository_name: str
    operation_type: OperationType
    
    def __post_init__(self):
        super().__init__()


@dataclass
class RepositoryOperationFailed(Event):
    """Emitted when a repository operation fails."""
    operation_id: UUID
    repository_name: str
    operation_type: OperationType
    error_message: str
    
    def __post_init__(self):
        super().__init__()


@dataclass
class RepositoryOperationSkipped(Event):
    """Emitted when a repository operation is skipped."""
    operation_id: UUID
    repository_name: str
    operation_type: OperationType
    reason: str
    
    def __post_init__(self):
        super().__init__()