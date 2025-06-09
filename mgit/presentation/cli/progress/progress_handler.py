"""Progress handler for CLI using Rich progress bars."""

from typing import Dict, Optional
from uuid import UUID

from rich.progress import Progress, TaskID
from rich.console import Console

from mgit.domain.events import (
    BulkOperationStarted,
    BulkOperationCompleted,
    RepositoryOperationStarted,
    RepositoryOperationProgress,
    RepositoryOperationCompleted,
    RepositoryOperationFailed,
    RepositoryOperationSkipped,
)
from mgit.application.ports import EventBus


class CliProgressHandler:
    """Handles progress display for CLI operations."""
    
    def __init__(self, event_bus: EventBus, console: Console):
        self.event_bus = event_bus
        self.console = console
        self.progress = Progress(console=console)
        self.task_map: Dict[UUID, TaskID] = {}
        self.overall_task_id: Optional[TaskID] = None
        self.total_repos = 0
        
        # Subscribe to events
        event_bus.subscribe(BulkOperationStarted, self._on_bulk_started)
        event_bus.subscribe(BulkOperationCompleted, self._on_bulk_completed)
        event_bus.subscribe(RepositoryOperationStarted, self._on_repo_started)
        event_bus.subscribe(RepositoryOperationProgress, self._on_repo_progress)
        event_bus.subscribe(RepositoryOperationCompleted, self._on_repo_completed)
        event_bus.subscribe(RepositoryOperationFailed, self._on_repo_failed)
        event_bus.subscribe(RepositoryOperationSkipped, self._on_repo_skipped)
    
    def __enter__(self):
        """Enter context manager."""
        self.progress.__enter__()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        return self.progress.__exit__(exc_type, exc_val, exc_tb)
    
    def _on_bulk_started(self, event: BulkOperationStarted) -> None:
        """Handle bulk operation start."""
        self.total_repos = event.total_repositories
        self.overall_task_id = self.progress.add_task(
            f"[green]Processing {event.operation_type.value} for {event.project}...",
            total=self.total_repos
        )
    
    def _on_bulk_completed(self, event: BulkOperationCompleted) -> None:
        """Handle bulk operation completion."""
        if self.overall_task_id is not None:
            self.progress.update(
                self.overall_task_id,
                completed=self.total_repos,
                description=f"[green]Completed: {event.successful} successful, "
                           f"{event.failed} failed, {event.skipped} skipped[/green]"
            )
    
    def _on_repo_started(self, event: RepositoryOperationStarted) -> None:
        """Handle repository operation start."""
        display_name = self._truncate_name(event.repository.name)
        task_id = self.progress.add_task(
            f"[grey50]Pending: {display_name}[/grey50]",
            total=1,
            visible=True
        )
        self.task_map[event.operation_id] = task_id
    
    def _on_repo_progress(self, event: RepositoryOperationProgress) -> None:
        """Handle repository operation progress."""
        if event.operation_id in self.task_map:
            display_name = self._truncate_name(event.repository_name)
            self.progress.update(
                self.task_map[event.operation_id],
                description=f"[cyan]{event.message}: {display_name}[/cyan]"
            )
    
    def _on_repo_completed(self, event: RepositoryOperationCompleted) -> None:
        """Handle repository operation completion."""
        if event.operation_id in self.task_map:
            display_name = self._truncate_name(event.repository_name)
            self.progress.update(
                self.task_map[event.operation_id],
                description=f"[green]✓ {event.operation_type.value.title()}: {display_name}[/green]",
                completed=1
            )
        
        if self.overall_task_id is not None:
            self.progress.advance(self.overall_task_id, 1)
    
    def _on_repo_failed(self, event: RepositoryOperationFailed) -> None:
        """Handle repository operation failure."""
        if event.operation_id in self.task_map:
            display_name = self._truncate_name(event.repository_name)
            self.progress.update(
                self.task_map[event.operation_id],
                description=f"[red]✗ Failed: {display_name} - {event.error_message}[/red]",
                completed=1
            )
        
        if self.overall_task_id is not None:
            self.progress.advance(self.overall_task_id, 1)
    
    def _on_repo_skipped(self, event: RepositoryOperationSkipped) -> None:
        """Handle repository operation skip."""
        if event.operation_id in self.task_map:
            display_name = self._truncate_name(event.repository_name)
            self.progress.update(
                self.task_map[event.operation_id],
                description=f"[yellow]⊘ Skipped: {display_name} - {event.reason}[/yellow]",
                completed=1
            )
        
        if self.overall_task_id is not None:
            self.progress.advance(self.overall_task_id, 1)
    
    @staticmethod
    def _truncate_name(name: str, max_length: int = 30) -> str:
        """Truncate long repository names for display."""
        if len(name) > max_length:
            return name[:max_length - 3] + "..."
        return name