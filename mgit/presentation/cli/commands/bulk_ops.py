"""Bulk operation CLI commands (clone-all, pull-all)."""

from pathlib import Path
from typing import Optional, List
import asyncio

import typer
from typer import Argument, Option
from rich.console import Console

from mgit.domain.models.operations import OperationType, UpdateMode, OperationOptions
from mgit.domain.models.context import OperationContext
from mgit.application.container import get_container
from mgit.presentation.cli.progress import CliProgressHandler


app = typer.Typer(help="Bulk repository operations")


async def _execute_bulk_operation(
    operation_type: OperationType,
    project: str,
    target_path: Path,
    concurrency: int,
    update_mode: UpdateMode,
    exclude_repos: Optional[List[str]] = None,
    include_repos: Optional[List[str]] = None,
    dry_run: bool = False,
) -> None:
    """Execute a bulk operation with progress tracking."""
    console = Console()
    
    # Get dependencies from container
    container = get_container()
    service = container.bulk_operation_service
    event_bus = container.event_bus
    
    # Create operation context
    options = OperationOptions(
        concurrency=concurrency,
        update_mode=update_mode,
        exclude_repos=exclude_repos or [],
        include_repos=include_repos or [],
        dry_run=dry_run,
    )
    
    context = OperationContext(
        project=project,
        target_path=target_path,
        options=options,
    )
    
    # Execute operation with progress tracking
    with CliProgressHandler(event_bus, console) as progress_handler:
        if operation_type == OperationType.CLONE:
            await service.clone_all(context)
        else:  # PULL
            await service.pull_all(context)
    
    # Display summary
    if context.errors:
        console.print(f"\n[red]Operation completed with {len(context.errors)} errors[/red]")
        for error in context.errors:
            console.print(f"  [red]✗[/red] {error.repository_name}: {error.error_message}")
    else:
        console.print(f"\n[green]Operation completed successfully![/green]")


@app.command("clone-all")
def clone_all(
    project: str = Argument(..., help="The project to clone repositories from"),
    destination: Path = Argument(..., help="The destination directory for cloned repositories"),
    concurrency: int = Option(4, "-c", "--concurrency", help="Number of concurrent operations"),
    update_mode: UpdateMode = Option(UpdateMode.SKIP, "-u", "--update", help="How to handle existing repositories"),
    exclude: Optional[List[str]] = Option(None, "-e", "--exclude", help="Repositories to exclude"),
    include: Optional[List[str]] = Option(None, "-i", "--include", help="Only include these repositories"),
    dry_run: bool = Option(False, "--dry-run", help="Show what would be done without doing it"),
) -> None:
    """Clone all repositories from a project."""
    try:
        asyncio.run(
            _execute_bulk_operation(
                operation_type=OperationType.CLONE,
                project=project,
                target_path=destination,
                concurrency=concurrency,
                update_mode=update_mode,
                exclude_repos=exclude,
                include_repos=include,
                dry_run=dry_run,
            )
        )
    except KeyboardInterrupt:
        typer.echo("\nOperation cancelled by user", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@app.command("pull-all")
def pull_all(
    project: str = Argument(..., help="The project to pull repositories from"),
    repositories_path: Path = Argument(..., help="The directory containing the repositories"),
    concurrency: int = Option(4, "-c", "--concurrency", help="Number of concurrent operations"),
    exclude: Optional[List[str]] = Option(None, "-e", "--exclude", help="Repositories to exclude"),
    include: Optional[List[str]] = Option(None, "-i", "--include", help="Only include these repositories"),
    dry_run: bool = Option(False, "--dry-run", help="Show what would be done without doing it"),
) -> None:
    """Pull updates for all repositories in a project."""
    try:
        asyncio.run(
            _execute_bulk_operation(
                operation_type=OperationType.PULL,
                project=project,
                target_path=repositories_path,
                concurrency=concurrency,
                update_mode=UpdateMode.PULL,  # Pull operations always pull
                exclude_repos=exclude,
                include_repos=include,
                dry_run=dry_run,
            )
        )
    except KeyboardInterrupt:
        typer.echo("\nOperation cancelled by user", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)