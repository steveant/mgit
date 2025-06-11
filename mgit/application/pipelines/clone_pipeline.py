"""Pipeline for clone-all operations."""

from pathlib import Path
from typing import List, Optional
import asyncio

from mgit.domain.models.operations import OperationType, OperationResult
from mgit.domain.models.context import OperationContext
from mgit.domain.models.repository import Repository
from mgit.application.ports import GitOperations, ProviderOperations, EventBus
from mgit.utils.logging import get_logger


logger = get_logger(__name__)


class CloneAllPipeline:
    """Pipeline for cloning all repositories in a project."""
    
    def __init__(
        self,
        provider_adapter: ProviderOperations,
        git_adapter: GitOperations,
        event_bus: EventBus,
    ):
        self.provider_adapter = provider_adapter
        self.git_adapter = git_adapter
        self.event_bus = event_bus
    
    async def execute(self, context: OperationContext) -> OperationResult:
        """Execute the clone-all pipeline."""
        logger.info(f"Starting clone-all pipeline for project: {context.project}")
        
        # Step 1: List repositories
        repositories = self._get_repositories(context)
        
        # Step 2: Filter repositories based on include/exclude
        filtered_repos = self._filter_repositories(repositories, context)
        
        # Step 3: Clone repositories concurrently
        result = await self._clone_repositories(filtered_repos, context)
        
        logger.info(f"Clone-all pipeline completed. Success: {result.successful}, Failed: {result.failed}")
        return result
    
    def _get_repositories(self, context: OperationContext) -> List[Repository]:
        """Get list of repositories from provider."""
        try:
            return self.provider_adapter.list_repositories(context.project)
        except Exception as e:
            logger.error(f"Failed to list repositories: {e}")
            return []
    
    def _filter_repositories(self, repositories: List[Repository], context: OperationContext) -> List[Repository]:
        """Filter repositories based on include/exclude patterns."""
        filtered = repositories
        
        # Apply include filter
        if context.options.include_repos:
            filtered = [
                repo for repo in filtered
                if any(pattern in repo.name for pattern in context.options.include_repos)
            ]
        
        # Apply exclude filter  
        if context.options.exclude_repos:
            filtered = [
                repo for repo in filtered
                if not any(pattern in repo.name for pattern in context.options.exclude_repos)
            ]
        
        logger.info(f"Filtered {len(repositories)} repositories to {len(filtered)}")
        return filtered
    
    async def _clone_repositories(self, repositories: List[Repository], context: OperationContext) -> OperationResult:
        """Clone repositories with concurrency control."""
        semaphore = asyncio.Semaphore(context.options.concurrency)
        results = await asyncio.gather(
            *[self._clone_single_repository(repo, context, semaphore) for repo in repositories],
            return_exceptions=True
        )
        
        # Aggregate results
        successful = sum(1 for r in results if r is True)
        failed = sum(1 for r in results if r is not True)
        
        return OperationResult(
            total_repositories=len(repositories),
            successful=successful,
            failed=failed,
            skipped=0,  # No skipping in clone pipeline
        )
    
    async def _clone_single_repository(
        self, 
        repository: Repository, 
        context: OperationContext, 
        semaphore: asyncio.Semaphore
    ) -> bool:
        """Clone a single repository."""
        async with semaphore:
            try:
                if context.options.dry_run:
                    logger.info(f"DRY RUN: Would clone {repository.name}")
                    return True
                
                # Check if repository already exists
                repo_path = context.target_path / repository.name
                if repo_path.exists():
                    # Handle based on update mode
                    if context.options.update_mode.value == "skip":
                        logger.info(f"Skipping existing repository: {repository.name}")
                        return True
                    elif context.options.update_mode.value == "force":
                        # Remove existing directory
                        import shutil
                        shutil.rmtree(repo_path)
                    # For pull mode, we'd pull instead of clone
                
                # Clone the repository
                success = await self.git_adapter.clone_repository(repository, context.target_path)
                if success:
                    logger.info(f"Successfully cloned: {repository.name}")
                else:
                    logger.error(f"Failed to clone: {repository.name}")
                
                return success
                
            except Exception as e:
                logger.error(f"Error cloning {repository.name}: {e}")
                return False