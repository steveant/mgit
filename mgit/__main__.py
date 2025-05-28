#!/usr/bin/env python3

import asyncio
import json
import logging
import os
import shutil
import subprocess # Needed for CalledProcessError exception
import sys
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress
from rich.prompt import Confirm # Added import
import typer

# Azure DevOps SDK imports
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
from azure.devops.v7_1.git import GitClient, GitRepository
from azure.devops.v7_1.core import CoreClient, TeamProjectReference
from azure.devops.exceptions import ClientRequestError, AzureDevOpsAuthenticationError

# Local imports
from mgit.constants import DEFAULT_VALUES, __version__, UpdateMode
from mgit.logging import setup_logging, MgitFormatter, ConsoleFriendlyRichHandler
from mgit.config.manager import get_config_value, CONFIG_DIR, CONFIG_FILE, load_config_file, save_config_file
from mgit.git import GitManager, embed_pat_in_url, sanitize_repo_name
from mgit.commands.auth import app as auth_app

# Configuration loading order:
# 1. Environment variables (highest priority)
# 2. Global config file in ~/.config/mgit/config
# 3. Default values (lowest priority)

# First load environment variables
load_dotenv(
    dotenv_path=None,
    verbose=True,
    override=True,
)

# Config directory creation is handled by the config module

# -----------------------------------------------------------------------------
# Logging Setup
# -----------------------------------------------------------------------------

# Set up logging using the new logging module
logger = setup_logging(
    config_dir=CONFIG_DIR,
    log_filename=get_config_value("LOG_FILENAME"),
    log_level=get_config_value("LOG_LEVEL"),
    console_level=get_config_value("CON_LEVEL")
)

console = Console()
app = typer.Typer(
    name="mgit",
    help=f"Multi-Git CLI Tool v{__version__} - A utility for managing repositories across " # Updated version will be picked up here automatically
    "multiple git platforms (Azure DevOps, GitHub, BitBucket) with bulk operations.",
    add_completion=False,
    no_args_is_help=True,
)

def version_callback(value: bool):
    if value:
        print(f"mgit version: {__version__}") # Updated version will be picked up here automatically
        raise typer.Exit()

@app.callback()
def main_options(
    version: Optional[bool] = typer.Option(
        None, "--version", callback=version_callback, is_eager=True,
        help="Show the application's version and exit."
    )
):
    """
    Multi-Git CLI Tool - Manage repos across multiple git platforms easily.
    """
    pass


# Add auth subcommand
app.add_typer(auth_app, name="auth", help="Manage credentials for Git providers")


# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------
# Git-related helper functions moved to mgit.git.utils


# -----------------------------------------------------------------------------
# Azure DevOps Manager
# -----------------------------------------------------------------------------
class AzDevOpsManager:
    def __init__(self, organization_url: Optional[str] = None, pat: Optional[str] = None):
        # Get organization URL and PAT, prioritizing arguments, then config/env
        self.ado_org = organization_url or get_config_value("AZURE_DEVOPS_ORG_URL")
        self.ado_pat = pat or get_config_value("AZURE_DEVOPS_EXT_PAT")

        # Ensure the URL is properly formatted
        if self.ado_org and not self.ado_org.startswith(("http://", "https://")):
            self.ado_org = f"https://{self.ado_org}"

        self.connection: Optional[Connection] = None
        self.core_client: Optional[CoreClient] = None
        self.git_client: Optional[GitClient] = None

        if not self.ado_org or not self.ado_pat:
            logger.debug("Organization URL or PAT not provided. Cannot initialize SDK connection.")
            # Allow initialization but connection will fail later if needed
            return

        try:
            # Initialize connection
            credentials = BasicAuthentication('', self.ado_pat)
            self.connection = Connection(base_url=self.ado_org, creds=credentials)

            # Get clients
            self.core_client = self.connection.clients.get_core_client()
            self.git_client = self.connection.clients.get_git_client()
            logger.debug("Azure DevOps SDK connection and clients initialized for %s", self.ado_org)
        except Exception as e:
            logger.error("Failed to initialize Azure DevOps SDK connection: %s", e)
            # Set clients to None to indicate failure
            self.connection = None
            self.core_client = None
            self.git_client = None
            # Don't raise here, let commands handle the lack of connection

    def test_connection(self) -> bool:
        """Tests the SDK connection by trying to list projects."""
        if not self.core_client:
            logger.error("Cannot test connection: SDK client not initialized.")
            return False
        try:
            # A simple call to verify authentication and connection
            self.core_client.get_projects()
            logger.debug("SDK connection test successful.")
            return True
        except (AzureDevOpsAuthenticationError, ClientRequestError) as e:
            logger.error("SDK connection test failed: %s", e)
            return False
        except Exception as e:
            logger.error("Unexpected error during SDK connection test: %s", e)
            return False

    def get_project(self, project_name_or_id: str) -> Optional[TeamProjectReference]:
        """Get project details by name or ID."""
        if not self.core_client:
            logger.error("Cannot get project: SDK client not initialized.")
            return None
        try:
            return self.core_client.get_project(project_name_or_id)
        except Exception as e:
            logger.error(f"Failed to get project '{project_name_or_id}': {e}")
            return None

    # Removed check_az_cli_installed and ensure_ado_ext_installed
    # Removed is_logged_into_az_devops and login_to_az_devops (handled by __init__ and test_connection)
    # Removed configure_az_devops (handled by SDK client initialization)


# -----------------------------------------------------------------------------
# Git Manager
# -----------------------------------------------------------------------------
# GitManager class moved to mgit.git.manager


@app.command()
def clone_all(
    project: str = typer.Argument(
        ..., help="Azure DevOps project name."
    ),
    rel_path: str = typer.Argument(
        ..., help="Relative path to clone into."
    ),
    url: Optional[str] = typer.Argument(
        None,
        help="Organization URL (defaults to "
        f"{DEFAULT_VALUES['AZURE_DEVOPS_ORG_URL']} if not provided).",
    ),
    concurrency: int = typer.Option(
        int(get_config_value("DEFAULT_CONCURRENCY", "4")),
        "--concurrency",
        "-c",
        help="Number of concurrent clone operations.",
    ),
    update_mode: UpdateMode = typer.Option(
        get_config_value("DEFAULT_UPDATE_MODE", "skip"),
        "--update-mode",
        "-u",
        help=(
            "How to handle existing folders: "
            "'skip' => do nothing if folder exists, "
            "'pull' => attempt a 'git pull' if it's a valid repo, "
            "'force' => remove the folder and clone fresh."
        ),
    ),
):
    """
    Clone all repositories from Azure DevOps project.
    """

    # Determine organization URL
    org_url = url or get_config_value("AZURE_DEVOPS_ORG_URL")
    if not org_url:
        logger.error("Azure DevOps organization URL is not configured. Use --url or set AZURE_DEVOPS_ORG_URL.")
        raise typer.Exit(code=1)

    # Initialize managers
    ado = AzDevOpsManager(organization_url=org_url) # PAT is picked up from env/config by default
    git_manager = GitManager()

    # Check connection/authentication
    if not ado.connection or not ado.git_client or not ado.core_client:
         logger.error(
             "Failed to initialize Azure DevOps SDK connection. "
             "Ensure AZURE_DEVOPS_ORG_URL and AZURE_DEVOPS_EXT_PAT are correctly set."
         )
         raise typer.Exit(code=1)

    if not ado.test_connection():
        logger.error(
            "Failed to connect or authenticate to Azure DevOps at %s. "
            "Ensure PAT is valid and has correct permissions.",
            ado.ado_org
        )
        raise typer.Exit(code=1)

    # Get project ID
    logger.debug(f"Fetching project details for: {project}")
    project_details = ado.get_project(project)
    if not project_details:
        logger.error(f"Could not find project '{project}' in organization '{ado.ado_org}'.")
        raise typer.Exit(code=1)
    project_id = project_details.id
    logger.debug(f"Found project ID: {project_id}")


    # Prepare local folder
    target_path = Path.cwd() / rel_path
    target_path.mkdir(parents=True, exist_ok=True)

    # List repos using SDK
    logger.debug(f"Fetching repository list for project ID: {project_id}...")
    try:
        # Note: The SDK returns GitRepository objects directly
        repos: list[GitRepository] = ado.git_client.get_repositories(project=project_id)
        logger.info(f"Found {len(repos)} repositories in project '{project}'.")
    except Exception as e:
        logger.error(f"Error fetching repository list via SDK: {e}")
        raise typer.Exit(code=1)

    if not repos:
        logger.info(f"No repositories found in project '{project}'.")
        return # Exit gracefully if no repos

    failures = []
    confirmed_force_remove = False # Flag to track user confirmation

    # --- Pre-check for force mode ---
    dirs_to_remove = []
    if update_mode == UpdateMode.force:
        logger.debug("Checking for existing directories to remove (force mode)...")
        for repo in repos:
            repo_url = repo.remote_url
            sanitized_name = sanitize_repo_name(repo_url)
            repo_folder = target_path / sanitized_name
            if repo_folder.exists():
                dirs_to_remove.append((repo.name, sanitized_name, repo_folder))

        if dirs_to_remove:
            console.print("[bold yellow]Force mode selected. The following existing directories will be REMOVED:[/bold yellow]")
            for _, s_name, _ in dirs_to_remove:
                console.print(f" - {s_name}")
            if Confirm.ask("Proceed with removing these directories and cloning fresh?", default=False):
                confirmed_force_remove = True
                logger.info("User confirmed removal of existing directories.")
            else:
                logger.warning("User declined removal. Force mode aborted for existing directories.")
                # Optionally, switch mode or just let the tasks skip later
                # For simplicity, we'll let the tasks handle skipping based on confirmed_force_remove flag
    # --- End Pre-check ---


    async def do_clones():
        """
        Process repos asynchronously with a concurrency
        limit and a progress bar. lso embed the PAT in the remote URL.
        Handle each repo's failure gracefully, storing it in 'failures'.
        """
        sem = asyncio.Semaphore(concurrency)

        # Keep track of individual repo tasks
        repo_tasks = {}

        with Progress() as progress:
            overall_task_id = progress.add_task(
                "[green]Processing Repositories...",
                total=len(repos),
            )

            async def process_one_repo(repo: GitRepository): # repo is now a GitRepository object
                repo_name = repo.name
                repo_url = repo.remote_url # Use remote_url from SDK object
                is_disabled = repo.is_disabled # Use is_disabled attribute
                display_name = repo_name[:30] + "..." if len(repo_name) > 30 else repo_name

                # Add a task for this specific repo early
                repo_task_id = progress.add_task(f"[grey50]Pending: {display_name}[/grey50]", total=1, visible=True)
                repo_tasks[repo_name] = repo_task_id

                async with sem:
                    # Check if repository is disabled
                    if is_disabled:
                        logger.info(f"Skipping disabled repository: {repo_name}")
                        failures.append((repo_name, "repository is disabled"))
                        progress.update(repo_task_id, description=f"[yellow]Disabled: {display_name}[/yellow]", completed=1)
                        progress.advance(overall_task_id, 1)
                        return

                    # Sanitize the repository name for filesystem use
                    # Use the actual repo name for the folder, sanitize the URL for logging/cloning if needed
                    # but the folder name should match the repo name ideally.
                    # Let's use the sanitized name based on the URL for consistency with previous behavior.
                    sanitized_name = sanitize_repo_name(repo_url)
                    if sanitized_name != repo_name:
                         logger.debug(
                             f"Using sanitized name '{sanitized_name}' for repository '{repo_name}' folder"
                         )

                    repo_folder = target_path / sanitized_name
                    # Decide how to handle if folder already exists
                    if repo_folder.exists():
                        if update_mode == UpdateMode.skip:
                            logger.info(f"Skipping existing repo folder: {sanitized_name}")
                            progress.update(repo_task_id, description=f"[blue]Skipped (exists): {display_name}[/blue]", completed=1)
                            progress.advance(overall_task_id, 1)
                            return
                        elif update_mode == UpdateMode.pull:
                            progress.update(repo_task_id, description=f"[cyan]Pulling: {display_name}...", visible=True)
                            if (
                                repo_folder / ".git"
                            ).exists():
                                # Attempt to do a pull
                                try:
                                    await git_manager.git_pull(repo_folder)
                                    progress.update(repo_task_id, description=f"[green]Pulled (update): {display_name}[/green]", completed=1)
                                except subprocess.CalledProcessError as e:
                                    logger.warning(f"Pull failed for {repo_name}: {e}")
                                    failures.append((repo_name, "pull failed"))
                                    progress.update(repo_task_id, description=f"[red]Pull Failed (update): {display_name}[/red]", completed=1)
                            else:
                                msg = "Folder exists but is not a git repo."
                                logger.warning(f"{repo_name}: {msg}")
                                failures.append((repo_name, msg))
                                progress.update(repo_task_id, description=f"[yellow]Skipped (not repo): {display_name}[/yellow]", completed=1)
                            progress.advance(overall_task_id, 1)
                            return
                        elif update_mode == UpdateMode.force:
                            # Check if removal was confirmed AND this dir was marked
                            should_remove = confirmed_force_remove and any(rf == repo_folder for _, _, rf in dirs_to_remove)
                            if should_remove:
                                progress.update(repo_task_id, description=f"[magenta]Removing: {display_name}...", visible=True)
                                logger.info(f"Removing existing folder: {sanitized_name}")
                                try:
                                    shutil.rmtree(repo_folder)
                                    # Removal successful, fall through to clone
                                except Exception as e:
                                    failures.append((repo_name, f"Failed removing old folder: {e}"))
                                    progress.update(repo_task_id, description=f"[red]Remove Failed: {display_name}[/red]", completed=1)
                                    progress.advance(overall_task_id, 1)
                                    return
                            else:
                                # Either user declined or this specific folder wasn't marked (shouldn't happen with current logic, but safe check)
                                logger.warning(f"Skipping removal of existing folder (not confirmed): {sanitized_name}")
                                progress.update(repo_task_id, description=f"[blue]Skipped (force declined/not applicable): {display_name}[/blue]", completed=1)
                                progress.advance(overall_task_id, 1)
                                return
                    # If we made it here:
                    # - Folder didn't exist OR
                    # - Force mode was confirmed AND removal succeeded
                    progress.update(repo_task_id, description=f"[cyan]Cloning: {display_name}...", visible=True)
                    pat_url = embed_pat_in_url(repo_url, ado.ado_pat) # Use PAT from AzDevOpsManager instance
                    try:
                        # Use the sanitized name for the directory argument
                        await git_manager.git_clone(pat_url, target_path, sanitized_name)
                        progress.update(repo_task_id, description=f"[green]Cloned: {display_name}[/green]", completed=1)
                    except subprocess.CalledProcessError as e:
                        # Use the sanitized name for the directory argument
                        await git_manager.git_clone(pat_url, target_path, sanitized_name)
                        progress.update(repo_task_id, description=f"[green]Cloned: {display_name}[/green]", completed=1)
                    except subprocess.CalledProcessError as e:
                        logger.warning(f"Clone failed for {repo_name}: {e}")
                        failures.append((repo_name, "clone failed"))
                        progress.update(repo_task_id, description=f"[red]Clone Failed: {display_name}[/red]", completed=1)

                    progress.advance(overall_task_id, 1)

            # Iterate through the GitRepository objects from the SDK
            await asyncio.gather(*(process_one_repo(repo) for repo in repos))

    logger.info(
        "Processing all repositories for project: "
        "%s into '%s' with update_mode='%s'",
        project,
        target_path,
        update_mode,
    )
    asyncio.run(do_clones())

    # Summarize
    if failures:
        logger.warning("Some repositories had issues:")
        for repo_name, reason in failures:
            logger.warning(f" - {repo_name}: {reason}")
    else:
        logger.info(
            "All repositories processed successfully with no errors."
        )


# -----------------------------------------------------------------------------
# pull_all Command
# -----------------------------------------------------------------------------
@app.command()
def pull_all(
    project: str = typer.Argument(
        ..., help="Azure DevOps project name."
    ),
    rel_path: str = typer.Argument(
        ..., help="Relative path where repositories exist."
    ),
):
    """
    Pull the latest changes for all repositories
    in the specified relative path.
    """
    # Determine organization URL (needed for AzDevOpsManager initialization)
    org_url = get_config_value("AZURE_DEVOPS_ORG_URL")
    if not org_url:
        logger.error("Azure DevOps organization URL is not configured. Set AZURE_DEVOPS_ORG_URL.")
        raise typer.Exit(code=1)

    # Initialize managers
    ado = AzDevOpsManager(organization_url=org_url)
    git_manager = GitManager()

    # Check connection/authentication
    if not ado.connection or not ado.git_client or not ado.core_client:
         logger.error(
             "Failed to initialize Azure DevOps SDK connection. "
             "Ensure AZURE_DEVOPS_ORG_URL and AZURE_DEVOPS_EXT_PAT are correctly set."
         )
         raise typer.Exit(code=1)

    if not ado.test_connection():
        logger.error(
            "Failed to connect or authenticate to Azure DevOps at %s. "
            "Ensure PAT is valid and has correct permissions.",
            ado.ado_org
        )
        raise typer.Exit(code=1)

    # Get project ID
    logger.debug(f"Fetching project details for: {project}")
    project_details = ado.get_project(project)
    if not project_details:
        logger.error(f"Could not find project '{project}' in organization '{ado.ado_org}'.")
        raise typer.Exit(code=1)
    project_id = project_details.id
    logger.debug(f"Found project ID: {project_id}")

    # Check target path
    target_path = Path.cwd() / rel_path
    if not target_path.exists() or not target_path.is_dir():
        logger.error(f"Target path does not exist or is not a directory: {target_path}")
        raise typer.Exit(code=1)

    # List repos using SDK
    logger.debug(f"Fetching repository list for project ID: {project_id}...")
    try:
        repos: list[GitRepository] = ado.git_client.get_repositories(project=project_id)
        logger.info(f"Found {len(repos)} repositories in project '{project}' to check for pulling.")
    except Exception as e:
        logger.error(f"Error fetching repository list via SDK: {e}")
        raise typer.Exit(code=1)

    if not repos:
        logger.info(f"No repositories found in project '{project}'.")
        return

    async def do_pulls():
        failures = []
        repo_tasks = {} # Keep track of individual repo tasks

        # Use Progress bar for visual feedback
        with Progress() as progress:
            overall_task_id = progress.add_task("[cyan]Pulling repositories...", total=len(repos))

            for repo in repos: # repo is GitRepository object
                repo_name = repo.name
                repo_url = repo.remote_url # Needed for sanitization consistency
                is_disabled = repo.is_disabled
                display_name = repo_name[:30] + "..." if len(repo_name) > 30 else repo_name

                # Add task for this repo
                repo_task_id = progress.add_task(f"[grey50]Pending: {display_name}[/grey50]", total=1, visible=True)
                repo_tasks[repo_name] = repo_task_id

                if is_disabled:
                    logger.info(f"Skipping disabled repository: {repo_name}")
                    failures.append((repo_name, "repository is disabled"))
                    progress.update(repo_task_id, description=f"[yellow]Disabled: {display_name}[/yellow]", completed=1)
                    progress.advance(overall_task_id, 1)
                    continue

                # Use sanitized name to find the local directory, consistent with clone_all
                sanitized_name = sanitize_repo_name(repo_url)
                if sanitized_name != repo_name:
                    logger.debug(
                        f"Checking sanitized path '{sanitized_name}' for repository '{repo_name}'"
                    )

                repo_dir = target_path / sanitized_name
                if (
                    repo_dir.exists()
                    and (repo_dir / ".git").exists()
                ):
                    try:
                        progress.update(repo_task_id, description=f"[cyan]Pulling: {display_name}...", visible=True)
                        await git_manager.git_pull(repo_dir)
                        progress.update(repo_task_id, description=f"[green]Pulled: {display_name}[/green]", completed=1)
                    except subprocess.CalledProcessError as e:
                        logger.warning(f"Pull failed for {repo_name}: {e}")
                        failures.append((repo_name, "pull failed"))
                        progress.update(repo_task_id, description=f"[red]Pull Failed: {display_name}[/red]", completed=1)
                else:
                    logger.warning(f"Repository path is missing or not a git repo: {repo_dir}")
                    failures.append((repo_name, "local directory missing or not a git repo"))
                    progress.update(repo_task_id, description=f"[yellow]Skipped (missing): {display_name}[/yellow]", completed=1)

                progress.advance(overall_task_id, 1) # Advance overall progress

        if failures:
            logger.warning(
                "Some repositories had issues during pull:"
            )
            for name, reason in failures:
                logger.warning(f" - {name}: {reason}")
        else:
            logger.info(
                "All repositories have been pulled successfully."
            )

    logger.info(
        f"Pulling all repositories for project: {project} in '{target_path}'"
    )
    asyncio.run(do_pulls())


# -----------------------------------------------------------------------------
# generate_env Command
# -----------------------------------------------------------------------------
@app.command(help="Generate a sample environment file with configuration options.")
def generate_env():
    """
    Generate a detailed sample environment file with all configuration options.

    This command creates a .env.sample file with example values and detailed
    comments explaining each configuration option. Users can copy this file
    to .env to set local environment variables.
    """
    env_content = """# Azure DevOps CLI Configuration Sample
# Copy this file to .env to configure environment variables
# Or use ~/.config/ado-cli/config for global settings

# Azure DevOps organization URL (required)
AZURE_DEVOPS_ORG_URL=https://www.visualstudio.com

# Personal Access Token for authentication (required)
# Can also be set in ~/.config/ado-cli/config
AZURE_DEVOPS_EXT_PAT=<YOUR_PERSONAL_ACCESS_TOKEN>

# Log file name (default: ado-cli.log)
LOG_FILENAME=ado-cli.log

# Logging level for file logs (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=DEBUG

# Logging level for console output (DEBUG, INFO, WARNING, ERROR)
CON_LEVEL=INFO

# Default concurrency for repository operations (default: 4)
# Higher values speed up cloning multiple repositories but increase resource usage
DEFAULT_CONCURRENCY=4

# Default update mode when repositories already exist:
# - skip: Don't touch existing repositories
# - pull: Try to git pull if it's a valid git repository
# - force: Remove existing folder and clone fresh
DEFAULT_UPDATE_MODE=skip
"""

    counter = 0
    new_file = Path(".env.sample")
    while new_file.exists():
        counter += 1
        new_file = Path(f".env.sample{counter}")

    with new_file.open("w", encoding="utf-8") as wf:
        wf.write(env_content)

    console.print(f"[green]✓[/green] Created {new_file} with detailed configuration options.")

# For backward compatibility
@app.command(hidden=True)
def gen_env():
    """Alias for generate_env command (deprecated)."""
    generate_env()


# -----------------------------------------------------------------------------
# login Command
# -----------------------------------------------------------------------------
@app.command(help="Login to Azure DevOps and validate credentials.")
def login(
    organization: Optional[str] = typer.Option(
        None, "--org", "-o", help="Azure DevOps organization URL (optional, uses config/env if not provided)."
    ),
    pat: Optional[str] = typer.Option(
        None, "--pat", "-p", help="Personal Access Token (optional, uses config/env if not provided)."
    ),
    store: bool = typer.Option(
        False, # Default to False for explicit login command
        "--store/--no-store",
        help="Store provided credentials in global config file (~/.config/ado-cli/config)."
    )
):
    """
    Validate Azure DevOps credentials and optionally store them.

    Tests connection using PAT from arguments, environment variables,
    or global config file. If --store is used, saves the provided
    (or discovered) organization URL and PAT to the global config.
    """
    # Initialize with provided args (or None to use config/env)
    ado = AzDevOpsManager(organization_url=organization, pat=pat)

    # Prompt if still missing after checking args/config/env
    if not ado.ado_org:
         ado.ado_org = typer.prompt(
             "Enter Azure DevOps organization URL",
             default=DEFAULT_VALUES["AZURE_DEVOPS_ORG_URL"]
         )
         # Re-initialize if org was prompted
         ado = AzDevOpsManager(organization_url=ado.ado_org, pat=ado.ado_pat)

    if not ado.ado_pat:
         ado.ado_pat = typer.prompt(
             "Enter Personal Access Token (PAT)",
             hide_input=True
         )
         # Re-initialize if PAT was prompted
         ado = AzDevOpsManager(organization_url=ado.ado_org, pat=ado.ado_pat)

    # Ensure URL format is correct after potential prompt
    if ado.ado_org and not ado.ado_org.startswith(("http://", "https://")):
        ado.ado_org = f"https://{ado.ado_org}"
        # Re-initialize if URL format changed
        ado = AzDevOpsManager(organization_url=ado.ado_org, pat=ado.ado_pat)


    # Test the connection
    if ado.test_connection():
        console.print(f"[green]✓[/green] Successfully connected to Azure DevOps organization: {ado.ado_org}")

        # Store credentials if requested and if they were provided/discovered
        if store and ado.ado_org and ado.ado_pat:
            should_store = True
            if CONFIG_FILE.exists():
                 # Ask for confirmation before overwriting
                 should_store = Confirm.ask(f"Overwrite existing credentials in {CONFIG_FILE}?", default=False)

            if should_store:
                # Use the potentially prompted/formatted values
                store_credentials(ado.ado_org, ado.ado_pat)
            else:
                console.print("[yellow]Credentials not stored.[/yellow]")
        elif store:
             logger.warning("Could not store credentials as organization URL or PAT was missing.")

    else:
        console.print(f"[red]✗[/red] Failed to connect/authenticate to {ado.ado_org}. Please check URL and PAT.")
        raise typer.Exit(code=1)


def store_credentials(organization: str, pat: str):
    """Store credentials in global config file for future use."""
    # Create config directory if it doesn't exist
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # Read existing config if available
    config_values = load_config_file()

    # Update with new values
    config_values["AZURE_DEVOPS_ORG_URL"] = organization
    config_values["AZURE_DEVOPS_EXT_PAT"] = pat

    # Write back to config file
    save_config_file(config_values)
    console.print(f"[green]✓[/green] Credentials stored in {CONFIG_FILE}")


# -----------------------------------------------------------------------------
# config Command
# -----------------------------------------------------------------------------
@app.command(help="Set or view global configuration settings for ado-cli.")
def config(
    show: bool = typer.Option(False, "--show", help="Show current global configuration and exit."),
    organization: Optional[str] = typer.Option(
        None, "--org", help="Default Azure DevOps organization URL."
    ),
    concurrency: Optional[int] = typer.Option(
        None, "--concurrency", help="Default concurrency for clone operations."
    ),
    update_mode: Optional[UpdateMode] = typer.Option(
        None, "--update-mode", help="Default update mode (skip, pull, force)."
    ),
):
    """
    Configure global settings for ado-cli.

    This command allows you to set default values for common parameters
    that will be used across all invocations of ado-cli.
    """
    # Create config directory if it doesn't exist
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # Read existing config if available
    config_values: Dict[str, Any] = load_config_file()

    # If show option is specified, display current config and exit
    if show:
        console.print("[bold]Current global configuration:[/bold]")
        if config_values:
            for key, value in config_values.items():
                # Mask the PAT token when displaying
                if key == "AZURE_DEVOPS_EXT_PAT":
                    masked_value = value[:4] + "*" * (len(value) - 8) + value[-4:] if len(value) > 8 else "*" * len(value)
                    console.print(f"  {key}={masked_value}")
                else:
                    console.print(f"  {key}={value}")
        else:
            console.print("  No global configuration set.")
        return

    # Update config values with provided options
    if organization:
        # Ensure URL format is correct
        if not organization.startswith(("http://", "https://")):
            organization = f"https://{organization}"
        config_values["AZURE_DEVOPS_ORG_URL"] = organization

    if concurrency is not None:
        config_values["DEFAULT_CONCURRENCY"] = str(concurrency)

    if update_mode is not None:
        config_values["DEFAULT_UPDATE_MODE"] = update_mode.value # Store enum value

    # Write updated config
    save_config_file(config_values)
    console.print(f"[green]✓[/green] Configuration updated successfully in {CONFIG_FILE}")


# The callback is no longer needed since we're using Typer's built-in help


def main():
    # Call the app directly - Typer will handle no args case with help
    app()


# Needed for Windows-specific behavior (not called on Linux/Mac)
def entrypoint():
    """Entry point for the application when packaged."""
    main()


if __name__ == "__main__":
    main()
