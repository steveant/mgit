# Presentation Layer - Lost Features and Commands

## 🚨 Critical Missing Feature: The `list` Command

The most powerful feature of mgit - wildcard repository listing - was NOT ported to this refactoring!

### What's Missing

In the original `__main__.py` (line 1485-1517):
```python
@app.command(name="list")
def list_command(
    query: str = typer.Argument(..., help="Query pattern (org/project/repo)"),
    ...
):
    """
    List repositories matching query pattern across providers.
    
    Examples:
      mgit list "*/*/*"                    # List all repos from all providers
      mgit list "myorg/*/*"                # List all repos from myorg org
      mgit list "*/*/pay*"                 # List repos ending in 'pay' from any org
    """
```

This command is completely missing from the refactored code, even though:
- The query parser exists in `utils/query_parser.py`
- The listing logic exists in `commands/listing.py`
- Users rely on this for repository discovery

### Other Missing Options

The refactored `clone_all` and `pull_all` commands are missing:
- `--dry-run` - See what would be done without doing it
- `--exclude` - Exclude specific repositories
- `--include` - Include only specific repositories

These exist in the domain model but aren't wired up in the CLI!

## Current Structure Issues

### cli/app.py
- Only creates the Typer app
- Doesn't register the `list` command
- Missing command imports

### cli/commands/bulk_ops.py
- Translates CLI args to domain objects
- Loses several options in translation
- No validation of mutually exclusive options

### cli/commands/base.py
- Empty file - unclear purpose
- Seems like abandoned abstraction

## How Commands Get Lost

1. Original command in `__main__.py` has full implementation
2. Refactoring creates new structure
3. Developer forgets to port all commands
4. No tests to catch missing functionality
5. Result: Key features silently disappear

## The Bulk Subcommand Mystery

There's a `bulk` subcommand registered that:
- Doesn't exist in the original code
- Has no implementation
- Causes "command not found" errors
- Should probably be removed

## Progress Display

The original uses Rich progress bars directly. The refactored version publishes events but nothing subscribes to display them. Result: No progress feedback to users.

## Fix Priority

1. **HIGH**: Restore the `list` command - this is a key feature
2. **HIGH**: Wire up `--exclude` and `--include` options
3. **MEDIUM**: Add proper progress display
4. **LOW**: Add `--dry-run` support
5. **LOW**: Remove the broken `bulk` subcommand

## Command Registration

To add the missing list command:
```python
# In cli/app.py
from mgit.commands.listing import list_command

# Register it
app.command(name="list")(list_command)
```

But wait - this would bypass the whole DDD architecture! This shows the impedance mismatch between Typer's design and DDD patterns.