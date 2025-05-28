"""
mgit.commands.auth - Authentication and credential management commands

This module provides CLI commands for managing credentials across
different Git providers.
"""

import typer
from rich.console import Console
from rich.table import Table
from typing import Optional
import sys

from ..auth import CredentialManager, ProviderType
from ..auth.models import Credential


app = typer.Typer(help="Manage credentials for Git providers")
console = Console()


def _get_manager() -> CredentialManager:
    """Get credential manager instance with error handling."""
    try:
        return CredentialManager()
    except RuntimeError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def store(
    provider: str = typer.Argument(..., help="Provider type (azure-devops, github, bitbucket)"),
    name: str = typer.Argument(..., help="Credential name/identifier"),
    token: Optional[str] = typer.Option(None, "--token", "-t", help="Token/password value"),
    username: Optional[str] = typer.Option(None, "--username", "-u", help="Associated username"),
    url: Optional[str] = typer.Option(None, "--url", help="Associated URL"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Description"),
    prompt: bool = typer.Option(True, "--prompt/--no-prompt", help="Prompt for token if not provided"),
):
    """Store a credential for a Git provider."""
    manager = _get_manager()
    
    # Get token interactively if not provided
    if not token:
        if prompt:
            token = typer.prompt("Enter token/password", hide_input=True)
        else:
            console.print("[red]Error: Token is required[/red]")
            raise typer.Exit(1)
    
    # Prepare metadata
    metadata = {}
    if description:
        metadata["description"] = description
    
    try:
        # Store the credential
        cred = manager.store_credential(
            provider=provider,
            name=name,
            credential=token,
            username=username,
            url=url,
            metadata=metadata
        )
        
        # Validate the credential format
        if not manager.validate_credential(cred):
            console.print(f"[yellow]Warning: Credential format may be invalid for {provider}[/yellow]")
        
        console.print(f"[green]✓[/green] Credential stored: {provider}:{name}")
        if username:
            console.print(f"  Username: {username}")
        if url:
            console.print(f"  URL: {url}")
        
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Failed to store credential: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def get(
    provider: str = typer.Argument(..., help="Provider type"),
    name: str = typer.Argument(..., help="Credential name"),
    show_value: bool = typer.Option(False, "--show-value", "-s", help="Display the actual credential value"),
):
    """Retrieve a stored credential."""
    manager = _get_manager()
    
    cred = manager.get_credential(provider, name)
    if not cred:
        console.print(f"[red]Credential not found: {provider}:{name}[/red]")
        raise typer.Exit(1)
    
    # Display credential info
    console.print(f"[bold]Credential: {provider}:{name}[/bold]")
    console.print(f"  Value: {cred.value if show_value else cred.mask_value()}")
    if cred.username:
        console.print(f"  Username: {cred.username}")
    if cred.url:
        console.print(f"  URL: {cred.url}")
    if cred.metadata.get("description"):
        console.print(f"  Description: {cred.metadata['description']}")
    if cred.created_at:
        console.print(f"  Created: {cred.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    if cred.updated_at and cred.updated_at != cred.created_at:
        console.print(f"  Updated: {cred.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")


@app.command()
def delete(
    provider: str = typer.Argument(..., help="Provider type"),
    name: str = typer.Argument(..., help="Credential name"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Delete a stored credential."""
    manager = _get_manager()
    
    # Check if credential exists
    cred = manager.get_credential(provider, name)
    if not cred:
        console.print(f"[red]Credential not found: {provider}:{name}[/red]")
        raise typer.Exit(1)
    
    # Confirm deletion
    if not force:
        confirm = typer.confirm(f"Delete credential {provider}:{name}?")
        if not confirm:
            console.print("Deletion cancelled")
            raise typer.Exit(0)
    
    # Delete the credential
    if manager.delete_credential(provider, name):
        console.print(f"[green]✓[/green] Deleted credential: {provider}:{name}")
    else:
        console.print(f"[red]Failed to delete credential[/red]")
        raise typer.Exit(1)


@app.command(name="list")
def list_credentials(
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="Filter by provider"),
    show_values: bool = typer.Option(False, "--show-values", "-s", help="Show actual credential values"),
):
    """List stored credentials."""
    manager = _get_manager()
    
    try:
        credentials = manager.list_credentials(provider)
    except Exception as e:
        console.print(f"[red]Failed to list credentials: {e}[/red]")
        raise typer.Exit(1)
    
    if not credentials:
        if provider:
            console.print(f"No credentials found for provider: {provider}")
        else:
            console.print("No credentials found")
        return
    
    # Create table
    table = Table(title="Stored Credentials")
    table.add_column("Provider", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Value", style="yellow")
    table.add_column("Username")
    table.add_column("URL")
    table.add_column("Created")
    
    # Add rows
    for cred in credentials:
        table.add_row(
            cred.provider.value,
            cred.name,
            cred.value if show_values else cred.mask_value(),
            cred.username or "",
            cred.url or "",
            cred.created_at.strftime('%Y-%m-%d') if cred.created_at else ""
        )
    
    console.print(table)


@app.command()
def info():
    """Display information about the credential storage backend."""
    manager = _get_manager()
    
    info = manager.get_storage_info()
    
    console.print("[bold]Credential Storage Information[/bold]")
    console.print(f"  Backend: {info['backend']}")
    console.print(f"  Available: {'Yes' if info['available'] else 'No'}")
    
    if 'storage_path' in info:
        console.print(f"  Storage Path: {info['storage_path']}")
    
    # Show supported providers
    console.print("\n[bold]Supported Providers:[/bold]")
    for provider in ProviderType:
        console.print(f"  • {provider.value}")


@app.command()
def validate(
    provider: str = typer.Argument(..., help="Provider type"),
    name: str = typer.Argument(..., help="Credential name"),
):
    """Validate a stored credential format."""
    manager = _get_manager()
    
    cred = manager.get_credential(provider, name)
    if not cred:
        console.print(f"[red]Credential not found: {provider}:{name}[/red]")
        raise typer.Exit(1)
    
    if manager.validate_credential(cred):
        console.print(f"[green]✓[/green] Credential format is valid for {provider}")
    else:
        console.print(f"[red]✗[/red] Credential format appears invalid for {provider}")
        
        # Provider-specific hints
        if cred.provider == ProviderType.AZURE_DEVOPS:
            console.print("  Azure DevOps PATs should be at least 52 characters")
        elif cred.provider == ProviderType.GITHUB:
            console.print("  GitHub tokens should start with: ghp_, gho_, ghu_, ghs_, or ghr_")
        elif cred.provider == ProviderType.BITBUCKET:
            console.print("  BitBucket app passwords should be at least 20 characters")


if __name__ == "__main__":
    app()