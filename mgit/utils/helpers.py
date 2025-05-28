"""Utility helper functions for mgit."""

import re
from urllib.parse import urlparse, urlunparse, unquote


def embed_pat_in_url(repo_url: str, pat: str) -> str:
    """
    Rewrite repo_url to embed the PAT as credentials:
      https://org@dev.azure.com ->
        https://PersonalAccessToken:PAT@dev.azure.com
    That way 'git clone' won't prompt for credentials.
    """
    parsed = urlparse(repo_url)
    # Some ADOS remoteUrls look like:
    # 'https://org@dev.azure.com/org/project/_git/repo'
    # We'll embed 'PersonalAccessToken:pat@' as netloc
    
    # Extract the hostname without any existing username
    hostname = parsed.hostname or parsed.netloc
    port = f":{parsed.port}" if parsed.port else ""
    
    # Create new netloc with PAT credentials
    netloc_with_pat = f"PersonalAccessToken:{pat}@{hostname}{port}"
    
    # Rebuild the URL
    return urlunparse((
        parsed.scheme,
        netloc_with_pat,
        parsed.path,
        parsed.params,
        parsed.query,
        parsed.fragment
    ))


def sanitize_repo_name(repo_url: str) -> str:
    """
    Extract and sanitize repository name from URL for use as a directory name.
    Handles URL encoding, spaces, and special characters.

    Example:
      Input: https://dev.azure.com/org/project/_git/Repo%20Name%20With%20Spaces
      Output: Repo_Name_With_Spaces
    """
    # Extract repo name from URL
    parsed = urlparse(repo_url)
    path_parts = parsed.path.strip('/').split('/')
    
    # The repository name is typically the last part of the path
    if path_parts and path_parts[-1]:
        repo_name = path_parts[-1]
    else:
        # Fallback to using the path or netloc
        repo_name = parsed.path.strip('/') or parsed.netloc
    
    # URL decode the name (handles %20 -> space, etc.)
    repo_name = unquote(repo_name)
    
    # Replace spaces and problematic characters with underscores
    # This includes: spaces, slashes, backslashes, colons, etc.
    repo_name = re.sub(r'[^\w\-.]', '_', repo_name)
    
    # Remove multiple consecutive underscores
    repo_name = re.sub(r'_+', '_', repo_name)
    
    # Remove leading/trailing underscores
    repo_name = repo_name.strip('_')
    
    return repo_name or "unnamed_repo"