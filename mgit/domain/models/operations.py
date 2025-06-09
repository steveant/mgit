"""Domain models for repository operations."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional, Set
from datetime import datetime


class UpdateMode(str, Enum):
    """How to handle existing folders during operations."""
    SKIP = "skip"
    PULL = "pull" 
    FORCE = "force"


class OperationType(str, Enum):
    """Types of repository operations."""
    CLONE = "clone"
    PULL = "pull"
    STATUS = "status"


class OperationStatus(str, Enum):
    """Status of a repository operation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class OperationOptions:
    """Options for repository operations."""
    update_mode: UpdateMode = UpdateMode.SKIP
    concurrency: int = 4
    force_confirmed: bool = False
    fetch_before_status: bool = False
    

@dataclass
class OperationError:
    """Represents an error during a repository operation."""
    repository_name: str
    operation_type: OperationType
    error_message: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __str__(self) -> str:
        return f"{self.repository_name}: {self.error_message}"


@dataclass 
class OperationResult:
    """Result of a bulk operation."""
    total_repositories: int
    successful: int
    failed: int
    skipped: int
    errors: List[OperationError] = field(default_factory=list)
    
    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0
    
    @property
    def success_rate(self) -> float:
        if self.total_repositories == 0:
            return 0.0
        return self.successful / self.total_repositories