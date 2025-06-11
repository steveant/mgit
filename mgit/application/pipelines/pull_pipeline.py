"""Pipeline for pull-all operations."""

from pathlib import Path
from typing import List, Optional
import asyncio

from mgit.domain.models.operations import OperationType, OperationResult
from mgit.domain.models.context import OperationContext
from mgit.domain.models.repository import Repository
from mgit.application.ports import GitOperations, ProviderOperations, EventBus
from mgit.utils.logging import get_logger


logger = get_logger(__name__)


class PullAllPipeline:
    """Pipeline for pulling updates to all repositories in a project."""
    
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
        """Execute the pull-all pipeline."""
        logger.info(f"Starting pull-all pipeline for project: {context.project}")
        
        # Step 1: Find local repositories
        local_repos = self._find_local_repositories(context)
        
        # Step 2: Filter repositories based on include/exclude
        filtered_repos = self._filter_local_repositories(local_repos, context)
        
        # Step 3: Pull repositories concurrently
        result = await self._pull_repositories(filtered_repos, context)
        
        logger.info(f"Pull-all pipeline completed. Success: {result.successful}, Failed: {result.failed}")
        return result
    
    def _find_local_repositories(self, context: OperationContext) -> List[Path]:
        """Find all local Git repositories in the target path."""
        repos = []
        for item in context.target_path.iterdir():
            if item.is_dir() and self.git_adapter.repository_exists(item):
                repos.append(item)
        
        logger.info(f"Found {len(repos)} local repositories")
        return repos
    
    def _filter_local_repositories(self, repositories: List[Path], context: OperationContext) -> List[Path]:
        """Filter local repositories based on include/exclude patterns."""
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
    
    async def _pull_repositories(self, repositories: List[Path], context: OperationContext) -> OperationResult:
        """Pull repositories with concurrency control."""
        semaphore = asyncio.Semaphore(context.options.concurrency)
        results = await asyncio.gather(
            *[self._pull_single_repository(repo, context, semaphore) for repo in repositories],
            return_exceptions=True
        )
        
        # Aggregate results
        successful = sum(1 for r in results if r is True)
        failed = sum(1 for r in results if r is not True)
        
        return OperationResult(
            total_repositories=len(repositories),
            successful=successful,
            failed=failed,
            skipped=0,  # No skipping in pull pipeline
        )
    
    async def _pull_single_repository(
        self, 
        repo_path: Path, 
        context: OperationContext, 
        semaphore: asyncio.Semaphore
    ) -> bool:
        """Pull updates for a single repository."""
        async with semaphore:
            try:
                if context.options.dry_run:
                    logger.info(f"DRY RUN: Would pull {repo_path.name}")
                    return True
                
                # Pull the repository
                success = await self.git_adapter.pull_repository(repo_path)
                if success:
                    logger.info(f"Successfully pulled: {repo_path.name}")
                else:
                    logger.error(f"Failed to pull: {repo_path.name}")
                
                return success
                
            except Exception as e:
                logger.error(f"Error pulling {repo_path.name}: {e}")
                return False