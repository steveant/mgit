"""Provider-specific exceptions.

This module defines the exception hierarchy for provider-related errors.
"""

from typing import Optional
from datetime import datetime


class ProviderError(Exception):
    """Base exception for provider errors."""
    pass


class AuthenticationError(ProviderError):
    """Authentication failed."""
    pass


class ConfigurationError(ProviderError):
    """Invalid provider configuration."""
    pass


class ConnectionError(ProviderError):
    """Connection to provider failed."""
    pass


class RateLimitError(ProviderError):
    """Rate limit exceeded."""
    
    def __init__(self, message: str, reset_time: Optional[datetime] = None):
        """Initialize rate limit error.
        
        Args:
            message: Error message
            reset_time: When the rate limit will reset
        """
        super().__init__(message)
        self.reset_time = reset_time


class ProviderNotFoundError(ProviderError):
    """Provider type not found."""
    pass


class RepositoryNotFoundError(ProviderError):
    """Repository not found."""
    pass


class OrganizationNotFoundError(ProviderError):
    """Organization/workspace not found."""
    pass


class ProjectNotFoundError(ProviderError):
    """Project not found."""
    pass


class PermissionError(ProviderError):
    """Insufficient permissions."""
    pass


class APIError(ProviderError):
    """Generic API error from provider."""
    
    def __init__(self, message: str, status_code: Optional[int] = None):
        """Initialize API error.
        
        Args:
            message: Error message
            status_code: HTTP status code if applicable
        """
        super().__init__(message)
        self.status_code = status_code