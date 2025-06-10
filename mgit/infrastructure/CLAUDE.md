# Infrastructure Layer - Async/Sync Bridge Issues

## ⚠️ CRITICAL PROBLEM IN THIS DIRECTORY

The adapters in this directory have a **fundamental async/sync impedance mismatch** that prevents mgit from working.

## The Problem

### provider_adapter.py
```python
# BROKEN CODE - DO NOT COPY
def list_repositories(self, project: str) -> List[Repository]:
    """List repositories - sync interface over async implementation."""
    return asyncio.run(self._async_list_repositories(project))  # FAILS!
```

**Why it fails**: 
- When called from an async context (which mgit uses), `asyncio.run()` tries to create a new event loop
- But there's already an event loop running
- Result: `RuntimeError: cannot be called from a running event loop`

### What the Original Code Does

The original `ProviderManager` is smart about event loops:
```python
# In the original manager.py
def list_repositories(self, project):
    if self._in_event_loop():
        # Returns an async generator
        return self._list_repositories_async(project)
    else:
        # Returns a regular list
        return self._list_repositories_sync(project)
```

But our adapter tries to force everything to be sync, which breaks this logic.

## Solutions

### Option 1: Make Everything Async (RECOMMENDED)
Change the port interface:
```python
# In application/ports.py
class ProviderOperations(Protocol):
    async def list_repositories(self, project: str) -> List[Repository]:
        ...
```

Then update the adapter:
```python
# In provider_adapter.py
async def list_repositories(self, project: str) -> List[Repository]:
    repos = []
    async for repo in self.provider_manager.list_repositories(project):
        repos.append(repo)
    return repos
```

### Option 2: Proper Event Loop Handling (COMPLEX)
```python
def list_repositories(self, project: str) -> List[Repository]:
    try:
        # Check if we're in an event loop
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No event loop, we can use asyncio.run
        return asyncio.run(self._async_list_repositories(project))
    
    # We're in an event loop, need different approach
    # This gets very complex very quickly
    import concurrent.futures
    import threading
    
    # Run in a thread to avoid event loop conflicts
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(asyncio.run, self._async_list_repositories(project))
        return future.result()
```

## Why This Matters

This isn't just a technical detail - it's the difference between the tool working and not working at all. Every clone/pull operation goes through this adapter, so if it's broken, nothing works.

## Testing the Fix

After making changes, test with:
```bash
poetry run python -m mgit clone-all "CSE" ./test-clone --config ado_pdidev -c 1
```

If you see repositories being cloned, the fix worked. If you see async errors, it didn't.

## Architecture Smell

The fact that we need complex event loop juggling suggests the architecture might be over-engineered for a CLI tool. Consider whether we really need:
- Separate ports and adapters
- Sync interfaces over async implementations  
- Complex event bus for simple progress tracking

Sometimes simpler is better.