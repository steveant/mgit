# mgit Error Handling System

This module provides a comprehensive, standardized error handling system for the mgit tool.

## Exception Hierarchy

```
MgitError (base exception)
├── ConfigurationError      # Config file/value issues
├── AuthenticationError     # Auth/credential failures  
├── ConnectionError         # Network/connection issues
├── RepositoryOperationError # Git operation failures
├── ProjectNotFoundError    # Project not found
├── OrganizationNotFoundError # Org not found/accessible
├── ValidationError         # Input validation failures
├── FileSystemError        # File/directory issues
├── ProviderError          # Provider-specific errors
├── CLIError              # CLI command issues
└── RetryExhausted        # All retry attempts failed
```

## Key Features

### 1. Error Handler Decorators

```python
from mgit.exceptions import error_handler, async_error_handler

@error_handler()
def my_command():
    # Automatically handles MgitError exceptions
    # Shows user-friendly messages
    # Exits with appropriate code
    pass

@async_error_handler()
async def my_async_command():
    # Same but for async functions
    pass
```

### 2. Retry Mechanism with Exponential Backoff

```python
from mgit.exceptions import retry_with_backoff, ConnectionError

@retry_with_backoff(
    retries=5,
    delay=1.0,
    backoff=2.0,
    exceptions=(ConnectionError,)
)
def fetch_data():
    # Automatically retries on ConnectionError
    # Delays: 1s, 2s, 4s, 8s, 16s
    pass
```

### 3. Error Context Manager

```python
from mgit.exceptions import error_context, RepositoryOperationError

with error_context(
    "clone repository",
    transform={GitError: RepositoryOperationError},
    details={"repo": "myrepo"}
):
    # Transforms GitError to RepositoryOperationError
    # Adds operation context
    git.clone(repo_url)
```

### 4. Validation Utilities

```python
from mgit.exceptions import validate_url, validate_path

# Validate URLs
validate_url("https://dev.azure.com/org", provider="azuredevops")

# Validate paths
path = validate_path("/some/path", must_exist=True)
```

### 5. Error Reporting

```python
from mgit.exceptions import create_error_report

try:
    # operation
except Exception as e:
    report = create_error_report(
        e,
        operation="clone",
        repository="myrepo",
        url="https://..."
    )
    print(report.format_for_display())
    logger.error(report.format_for_log())
```

## Usage Examples

### Basic Error Handling

```python
from mgit.exceptions import (
    AuthenticationError,
    error_handler,
    validate_url
)

@error_handler()
def login(org_url: str, pat: str):
    validate_url(org_url)
    
    if not pat:
        raise AuthenticationError("PAT token required")
    
    # Perform login...
```

### Network Operations with Retry

```python
from mgit.exceptions import (
    ConnectionError,
    retry_with_backoff
)

@retry_with_backoff(exceptions=(ConnectionError,))
def download_file(url: str):
    # Will retry on ConnectionError
    response = requests.get(url)
    if response.status_code >= 500:
        raise ConnectionError(f"Server error: {response.status_code}")
    return response.content
```

### Contextual Error Transformation

```python
from mgit.exceptions import error_context, FileSystemError

with error_context(
    "create project directory",
    transform={PermissionError: FileSystemError},
    details={"path": "/projects/new"}
):
    os.makedirs("/projects/new")
```

## Exit Codes

Each exception type has a specific exit code:

- `1`: General MgitError
- `2`: AuthenticationError
- `3`: ConnectionError  
- `4`: RepositoryOperationError
- `5`: ProjectNotFoundError
- `6`: OrganizationNotFoundError
- `7`: ValidationError
- `8`: FileSystemError
- `9`: ProviderError
- `10`: CLIError
- `11`: RetryExhausted
- `130`: KeyboardInterrupt (Ctrl+C)

## Best Practices

1. **Use specific exceptions**: Choose the most specific exception type for the error
2. **Include context**: Always provide meaningful error messages and details
3. **Use decorators**: Apply `@error_handler()` to all CLI commands
4. **Validate inputs**: Use validation utilities before operations
5. **Retry network ops**: Use `@retry_with_backoff()` for network operations
6. **Transform errors**: Use `error_context()` to convert low-level errors

## Integration

To use in your mgit commands:

```python
from mgit.exceptions import (
    error_handler,
    ValidationError,
    validate_url,
    validate_path
)

@app.command()
@error_handler()
def my_command(url: str, path: str):
    # Validation
    validate_url(url, provider="github")
    dest = validate_path(path)
    
    # Your command logic
    if error_condition:
        raise ValidationError("Something went wrong", field="url")
```

The error handler will automatically:
- Catch exceptions
- Display user-friendly messages
- Log full details
- Exit with appropriate code