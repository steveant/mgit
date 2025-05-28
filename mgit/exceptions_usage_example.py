#!/usr/bin/env python3
"""
Example usage of the mgit exception handling system.

This file demonstrates how to use the standardized error handling
in mgit commands and operations.
"""

import asyncio
from typing import Optional

import typer
from mgit.exceptions import (
    AuthenticationError,
    ConnectionError,
    RepositoryOperationError,
    ValidationError,
    error_handler,
    async_error_handler,
    retry_with_backoff,
    error_context,
    temporary_error_handler,
    validate_url,
    validate_path,
    create_error_report,
)

app = typer.Typer()


# Example 1: Using error_handler decorator for CLI commands
@app.command()
@error_handler()
def login(org_url: str, pat: str):
    """Example login command with error handling."""
    # Validate inputs
    validate_url(org_url, provider="azuredevops")
    
    if not pat:
        raise ValidationError("Personal Access Token cannot be empty", field="pat")
    
    # Simulate authentication
    if pat == "invalid":
        raise AuthenticationError("Invalid PAT token", provider="Azure DevOps")
    
    print(f"✓ Successfully logged in to {org_url}")


# Example 2: Using retry_with_backoff for network operations
@retry_with_backoff(retries=3, delay=1.0, exceptions=(ConnectionError,))
def fetch_repositories(project_name: str) -> list:
    """Fetch repositories with automatic retry on connection errors."""
    import random
    
    # Simulate network failure 50% of the time
    if random.random() < 0.5:
        raise ConnectionError(
            "Failed to connect to Azure DevOps",
            url="https://dev.azure.com/example"
        )
    
    return ["repo1", "repo2", "repo3"]


# Example 3: Using error_context for operation-specific error handling
@app.command()
@error_handler()
def clone(repository: str, destination: str):
    """Example clone command with contextual error handling."""
    # Validate destination path
    dest_path = validate_path(destination)
    
    # Use error context for the clone operation
    with error_context(
        "clone repository",
        transform={
            FileNotFoundError: RepositoryOperationError,
            PermissionError: RepositoryOperationError,
        },
        details={"repo": repository, "path": str(dest_path)}
    ):
        # Simulate clone operation
        if repository == "private-repo":
            raise PermissionError("Access denied")
        
        print(f"✓ Cloned {repository} to {dest_path}")


# Example 4: Async command with error handling
@app.command()
@error_handler()
def pull_all(project: str):
    """Example async command that pulls multiple repositories."""
    asyncio.run(async_pull_all(project))


@async_error_handler()
async def async_pull_all(project: str):
    """Async implementation of pull_all."""
    repos = ["repo1", "repo2", "repo3"]
    
    tasks = []
    for repo in repos:
        task = asyncio.create_task(pull_repository(repo))
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for repo, result in zip(repos, results):
        if isinstance(result, Exception):
            print(f"✗ Failed to pull {repo}: {result}")
        else:
            print(f"✓ Pulled {repo}")


async def pull_repository(repo: str):
    """Simulate pulling a repository."""
    await asyncio.sleep(0.1)  # Simulate network delay
    
    if repo == "repo2":
        raise RepositoryOperationError(
            "Pull failed due to conflicts",
            operation="pull",
            repository=repo
        )
    
    return f"Pulled {repo}"


# Example 5: Using temporary_error_handler for specific blocks
@app.command()
def process_files(directory: str, verbose: bool = False):
    """Process files with different error handling based on verbosity."""
    dir_path = validate_path(directory, must_exist=True)
    
    with temporary_error_handler(show_traceback=verbose):
        # This block will show traceback only if verbose=True
        for file in dir_path.iterdir():
            if file.suffix == ".error":
                raise ValidationError(f"Cannot process error files", field=str(file))
            
            print(f"Processing {file}")


# Example 6: Creating detailed error reports
@app.command()
@error_handler(log_traceback=False)
def analyze(repository: str):
    """Example command that generates error reports."""
    try:
        # Simulate analysis that fails
        if repository == "broken-repo":
            raise RepositoryOperationError(
                "Repository structure is invalid",
                operation="analyze",
                repository=repository
            )
        
        print(f"✓ Analysis complete for {repository}")
        
    except RepositoryOperationError as e:
        # Create detailed error report
        report = create_error_report(
            e,
            operation="repository analysis",
            repository=repository,
            checks_performed=["structure", "dependencies", "security"],
            checks_failed=["structure"]
        )
        
        # Log the detailed report
        print("\nError Report:")
        print(report.format_for_display())
        
        # Re-raise to let error_handler handle it
        raise


# Example 7: Custom retry callback
def log_retry_attempt(error: Exception, attempt: int):
    """Custom callback for retry attempts."""
    print(f"⚠ Attempt {attempt} failed: {error}. Retrying...")


@retry_with_backoff(
    retries=3,
    delay=0.5,
    on_retry=log_retry_attempt,
    exceptions=(ConnectionError, RepositoryOperationError)
)
def sync_with_remote(repo: str):
    """Sync with remote repository with custom retry logging."""
    import random
    
    # Simulate failures
    if random.random() < 0.7:  # 70% failure rate
        raise ConnectionError("Network timeout", url=f"https://example.com/{repo}")
    
    return "Sync successful"


if __name__ == "__main__":
    # Run the CLI app
    app()