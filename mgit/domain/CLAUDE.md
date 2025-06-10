# Domain Layer - Pure Models with No Behavior

## 📊 Overview

This layer contains "pure" domain models - data classes with no behavior. This is a controversial DDD choice.

## Design Philosophy Issues

### Current Approach: Anemic Domain Model
All models are just data containers:
```python
@dataclass
class Repository:
    name: str
    clone_url: str
    ssh_url: str
    # ... just data, no methods
```

### What's Missing: Rich Domain Model
In true DDD, domain objects have behavior:
```python
@dataclass 
class Repository:
    name: str
    clone_url: str
    
    def get_folder_name(self) -> str:
        """Domain logic for how repos map to folders"""
        return sanitize_repo_name(self.clone_url)
    
    def should_skip(self, options: OperationOptions) -> bool:
        """Domain logic for filtering"""
        if self.is_disabled:
            return True
        if options.exclude_repos and self.name in options.exclude_repos:
            return True
        return False
```

## Current Structure

### models/repository.py
- `Repository`: Just data fields
- `RepositoryOperation`: Tracks operation state
- No business logic

### models/operations.py  
- `OperationOptions`: Missing `exclude_repos` and `include_repos` fields!
- `UpdateMode`: Simple enum
- `OperationResult`: Just counters

### models/context.py
- `OperationContext`: Accumulates state
- Mixes concerns (options, operations, errors)

### events.py
- Many event types
- But nothing subscribes to them
- Over-engineered for a CLI

## Problems with Pure Data Models

1. **Logic Scattered**: Business rules spread across services
2. **Anemic Domain**: Models can't enforce their own invariants  
3. **Missing Validation**: No guarantee data is valid
4. **Primitive Obsession**: Using strings where objects would be better

## Example: The Clone Path Problem

Currently:
```python
# Logic in service layer
sanitized_name = sanitize_repo_name(repo.clone_url)
repo_folder = context.target_path / sanitized_name
```

Better:
```python
# Logic in domain
repo_folder = repo.get_local_path(context.target_path)
```

## Events Over-Engineering

We have events for everything:
- `BulkOperationStarted`
- `RepositoryOperationStarted` 
- `RepositoryOperationProgress`
- `RepositoryOperationCompleted`
- etc.

But:
- Nothing subscribes to display progress
- Events are fire-and-forget
- No event sourcing or replay
- Just complexity without benefit

## Missing Domain Concepts

1. **FilterSpec**: Encapsulate include/exclude logic
2. **ClonePath**: Handle path sanitization  
3. **ProviderCredentials**: Validate and mask tokens
4. **ConcurrencyLimit**: Provider-specific limits

## Recommendations

### Option 1: Add Behavior to Models
Make domain models responsible for their logic:
- Repository knows how to filter itself
- Operation knows how to execute itself
- Context validates its own state

### Option 2: Simplify to DTOs
If keeping anemic models, just call them DTOs:
- Be honest about the pattern
- Don't pretend it's DDD
- Simplify the architecture

### Option 3: Service-Oriented
Put all logic in services:
- Domain models as pure data
- Services as stateless functions  
- Simpler than fake DDD

## The Real Issue

This isn't really Domain-Driven Design. It's a layered architecture with DDD naming. Real DDD would:
- Start with the domain problem
- Model rich domain objects
- Let the architecture emerge

Instead, we started with an architecture and forced the domain into it.