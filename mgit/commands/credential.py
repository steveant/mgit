"""
CLI commands for credential management.

This module provides commands for storing, retrieving, and managing
credentials through the mgit CLI.
"""

import typer
from rich.console import Console
from rich.table import Table
from typing import Optional

from mgit.auth import CredentialManager, Provider
from mgit.auth.manager import get_credential_manager

console = Console()
app = typer.Typer(help="Manage credentials for various git providers")


@app.command("store")
def store_credential(
    provider: str = typer.Argument(..., help="Provider name (azure_devops, github, bitbucket, gitlab, generic)"),
    name: str = typer.Argument(..., help="Credential name (e.g., 'default', 'work', 'personal')"),
    token: str = typer.Option(None, "--token", "-t", help="Authentication token (will prompt if not provided)"),
    username: Optional[str] = typer.Option(None, "--username", "-u", help="Username (optional)"),
    url: Optional[str] = typer.Option(None, "--url", help="Associated URL (optional)"),
):
    """Store a credential securely."""
    try:
        # Convert provider string to enum
        provider_enum = Provider(provider.lower())
    except ValueError:
        console.print(f"[red]Invalid provider: {provider}[/red]")
        console.print("Valid providers: azure_devops, github, bitbucket, gitlab, generic")
        raise typer.Exit(code=1)
    
    # Prompt for token if not provided
    if not token:
        token = typer.prompt("Enter authentication token", hide_input=True)
    
    # Get credential manager
    manager = get_credential_manager()
    
    # Store the credential
    success = manager.store_credential(
        provider=provider_enum,
        name=name,
        token=token,
        username=username,
        url=url
    )
    
    if success:
        console.print(f"[green]✓[/green] Credential '{name}' stored successfully for {provider}")
    else:
        console.print(f"[red]✗[/red] Failed to store credential")
        raise typer.Exit(code=1)


@app.command("get")
def get_credential(
    provider: str = typer.Argument(..., help="Provider name"),
    name: str = typer.Argument(..., help="Credential name"),
    show_token: bool = typer.Option(False, "--show-token", help="Show the actual token (default: masked)"),
):
    """Retrieve a stored credential."""
    try:
        provider_enum = Provider(provider.lower())
    except ValueError:
        console.print(f"[red]Invalid provider: {provider}[/red]")
        raise typer.Exit(code=1)
    
    manager = get_credential_manager()
    credential = manager.get_credential(provider_enum, name)
    
    if not credential:
        console.print(f"[yellow]No credential found for {provider}/{name}[/yellow]")
        raise typer.Exit(code=1)
    
    # Display credential info
    console.print(f"\n[bold]Credential: {credential.name}[/bold]")
    console.print(f"Provider: {credential.provider.value}")
    if credential.username:
        console.print(f"Username: {credential.username}")
    if credential.url:
        console.print(f"URL: {credential.url}")
    
    if show_token:
        console.print(f"Token: {credential.token}")
    else:
        console.print(f"Token: {credential.mask_token()}")
    
    if credential.created_at:
        console.print(f"Created: {credential.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    if credential.updated_at:
        console.print(f"Updated: {credential.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")


@app.command("delete")
def delete_credential(
    provider: str = typer.Argument(..., help="Provider name"),
    name: str = typer.Argument(..., help="Credential name"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Delete a stored credential."""
    try:
        provider_enum = Provider(provider.lower())
    except ValueError:
        console.print(f"[red]Invalid provider: {provider}[/red]")
        raise typer.Exit(code=1)
    
    # Confirm deletion unless forced
    if not force:
        confirm = typer.confirm(f"Delete credential '{name}' for {provider}?")
        if not confirm:
            console.print("[yellow]Deletion cancelled[/yellow]")
            raise typer.Exit()
    
    manager = get_credential_manager()
    success = manager.delete_credential(provider_enum, name)
    
    if success:
        console.print(f"[green]✓[/green] Credential '{name}' deleted for {provider}")
    else:
        console.print(f"[red]✗[/red] Failed to delete credential")
        raise typer.Exit(code=1)


@app.command("list")
def list_credentials(
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="Filter by provider"),
    show_tokens: bool = typer.Option(False, "--show-tokens", help="Show actual tokens (default: masked)"),
):
    """List all stored credentials."""
    manager = get_credential_manager()
    
    # Get provider filter if specified
    provider_filter = None
    if provider:
        try:
            provider_filter = Provider(provider.lower())
        except ValueError:
            console.print(f"[red]Invalid provider: {provider}[/red]")
            raise typer.Exit(code=1)
    
    # Get credentials
    credentials = manager.list_credentials(provider_filter)
    
    if not credentials:
        if provider_filter:
            console.print(f"[yellow]No credentials found for {provider}[/yellow]")
        else:
            console.print("[yellow]No credentials found[/yellow]")
        return
    
    # Create table
    table = Table(title="Stored Credentials")
    table.add_column("Provider", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Username", style="blue")
    table.add_column("Token", style="yellow")
    table.add_column("URL", style="magenta")
    table.add_column("Updated", style="white")
    
    # Add rows
    for cred in credentials:
        token_display = cred.token if show_tokens else cred.mask_token()
        updated = cred.updated_at.strftime("%Y-%m-%d") if cred.updated_at else "N/A"
        
        table.add_row(
            cred.provider.value,
            cred.name,
            cred.username or "-",
            token_display,
            cred.url or "-",
            updated
        )
    
    console.print(table)


@app.command("migrate")
def migrate_credentials():
    """Migrate credentials from config files to secure storage."""
    from mgit.config.manager import load_config_file
    
    console.print("Checking for credentials in config files...")
    
    config_values = load_config_file()
    manager = get_credential_manager()
    
    if manager.migrate_from_config(config_values):
        console.print("[green]✓[/green] Successfully migrated credentials to secure storage")
        console.print("\n[yellow]Note:[/yellow] You can now remove PAT values from your config files")
    else:
        console.print("[yellow]No credentials found to migrate[/yellow]")


@app.command("test")
def test_credential(
    provider: str = typer.Argument(..., help="Provider name"),
    name: str = typer.Argument(..., help="Credential name"),
):
    """Test a credential by attempting to authenticate."""
    try:
        provider_enum = Provider(provider.lower())
    except ValueError:
        console.print(f"[red]Invalid provider: {provider}[/red]")
        raise typer.Exit(code=1)
    
    manager = get_credential_manager()
    credential = manager.get_credential(provider_enum, name)
    
    if not credential:
        console.print(f"[red]No credential found for {provider}/{name}[/red]")
        raise typer.Exit(code=1)
    
    console.print(f"Testing credential '{name}' for {provider}...")
    
    # Provider-specific testing
    if provider_enum == Provider.AZURE_DEVOPS:
        from mgit import AzDevOpsManager
        
        if not credential.url:
            console.print("[red]Azure DevOps credential requires a URL[/red]")
            raise typer.Exit(code=1)
        
        ado = AzDevOpsManager(organization_url=credential.url, pat=credential.token)
        if ado.test_connection():
            console.print(f"[green]✓[/green] Successfully authenticated to {credential.url}")
        else:
            console.print(f"[red]✗[/red] Authentication failed")
            raise typer.Exit(code=1)
    
    # TODO: Add tests for other providers
    else:
        console.print(f"[yellow]Test not implemented for {provider} provider[/yellow]")


if __name__ == "__main__":
    app()