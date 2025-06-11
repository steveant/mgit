"""Domain utilities for repository operations."""

import re
from urllib.parse import urlparse


def sanitize_repo_name(repo_url: str) -> str:
    """
    Sanitize repository name from URL for use as directory name.
    
    Args:
        repo_url: Repository URL to extract name from
        
    Returns:
        Sanitized directory name safe for filesystem use
    """
    # Parse URL to get the path component
    parsed = urlparse(repo_url)
    path = parsed.path
    
    # Remove leading/trailing slashes and .git suffix
    path = path.strip('/')
    if path.endswith('.git'):
        path = path[:-4]
    
    # Extract the repository name (last part of the path)
    repo_name = path.split('/')[-1] if '/' in path else path
    
    # Sanitize for filesystem compatibility
    # Remove or replace characters that are problematic for file systems
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', repo_name)
    
    # Remove any remaining problematic characters and clean up
    sanitized = re.sub(r'[^\w\-_.]', '_', sanitized)
    
    # Ensure it's not empty and doesn't start with a dot
    if not sanitized or sanitized.startswith('.'):
        sanitized = f"repo_{sanitized}" if sanitized else "unnamed_repo"
    
    return sanitized


def extract_repo_info(repo_url: str) -> dict:
    """
    Extract repository information from URL.
    
    Args:
        repo_url: Repository URL
        
    Returns:
        Dictionary with repository info (organization, name, etc.)
    """
    parsed = urlparse(repo_url)
    path_parts = parsed.path.strip('/').split('/')
    
    info = {
        'host': parsed.hostname,
        'scheme': parsed.scheme,
        'path': parsed.path,
    }
    
    if len(path_parts) >= 2:
        info['organization'] = path_parts[-2]
        repo_name = path_parts[-1]
        if repo_name.endswith('.git'):
            repo_name = repo_name[:-4]
        info['name'] = repo_name
    
    return info