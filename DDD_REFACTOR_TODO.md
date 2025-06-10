# DDD Refactoring TODO - Session State

## Current Status (2024-12-09)

We completed 5 architecture review iterations on the Domain-Driven Design refactoring. The refactoring reduced `__main__.py` from 1,636 lines to 331 lines by implementing a clean 4-layer architecture.

## Critical Issues Found and Fixed

### ✅ Fixed in commit a52b78b:
1. **manager_v2 import error** - Changed to use existing `manager` module
2. **Async/sync mismatch** - Fixed bulk operation service to handle sync list return

### ❌ Still Need Fixing:

#### CRITICAL - Prevents Runtime
1. **Missing Domain Fields**: `OperationOptions` is missing `exclude_repos` and `include_repos` fields that presentation layer expects
2. **Infrastructure adapter paths**: Container expects adapters in `infrastructure/adapters/` but they're in `infrastructure/`
3. **Event data type mismatch**: Progress handler expects `repository_name` string but `RepositoryOperationStarted` has `repository` object
4. **Async/sync boundary in provider adapter**: Still uses problematic thread pool execution

#### HIGH - Major Issues
1. **Missing `list` command**: The powerful wildcard query command (`mgit list "*/*/*"`) exists in main branch but wasn't ported to refactored code
2. **Broken `bulk` subcommand**: Registered but doesn't work - might want to remove it entirely
3. **Provider adapter async handling**: The sync/async boundary is fundamentally broken
4. **Git status implementation**: Currently returns hardcoded values

#### MEDIUM - Important
1. **Pipeline implementations**: Created but not actually used by the service
2. **Event bus type safety**: Needs better typing
3. **Missing test coverage**: No tests for the refactored architecture

## Test Results

### Working Commands:
- ✅ `mgit --version`
- ✅ `mgit --help`
- ✅ `mgit config --list`
- ✅ `mgit config --show <provider>`
- ✅ `mgit list "*/*/*"` (but only because it's running main branch code)

### Broken Commands:
- ❌ `mgit clone-all` - Fails with "async for requires __aiter__" error
- ❌ `mgit pull-all` - Same async error
- ❌ `mgit bulk` subcommand - Not found

## Key Architectural Issues

1. **Impedance Mismatch**: The DDD refactoring created a sync interface (`ProviderOperations`) but the underlying system is async
2. **Lost Features**: Several command options were removed (--dry-run, --exclude, --include)
3. **Incomplete Migration**: Some commands exist in multiple places or weren't fully migrated

## Next Steps

1. **Fix critical runtime errors** - Make basic clone/pull work
2. **Resolve async/sync boundaries** - Either make interfaces async or fix adapters
3. **Port missing features** - Especially the `list` command with wildcard support
4. **Add comprehensive tests** - The refactoring has no test coverage
5. **Remove or fix `bulk` subcommand** - Currently just causes confusion

## Architecture Decisions to Make

1. Should `ProviderOperations` interface be async?
2. Should we keep the pipeline pattern or simplify?
3. Should domain events be required or optional?
4. How to handle the provider manager's event loop detection?

## Testing Commands

```bash
# From worktree directory:
cd /opt/mgit-worktrees/feature-modularize-main-126

# Test basic CLI
poetry run python -m mgit --version
poetry run python -m mgit --help

# Test problematic commands
poetry run python -m mgit clone-all "CSE" ./test-clone --config ado_pdidev -c 1

# The error you'll see:
# ERROR    Error fetching repository list: 'async for' requires an object with __aiter__ method, got list
```

## File Locations

- Main refactored entry: `mgit/__main__.py` (331 lines)
- Domain models: `mgit/domain/models/`
- Application services: `mgit/application/services/bulk_operation_service.py`
- Infrastructure adapters: `mgit/infrastructure/git_adapter.py`, `provider_adapter.py`
- Presentation layer: `mgit/presentation/cli/commands/bulk_ops.py`

## Session Context

We were in the middle of end-to-end testing when we discovered that the refactored code has fundamental async/sync issues that prevent basic operations from working. The architecture is sound but the implementation has critical gaps.

The main branch code works fine, so this is purely an issue with the refactoring implementation, not the concepts.

## Deep Analysis of Core Problems

### 1. The Async/Sync Impedance Mismatch (ROOT CAUSE)

**The Problem**: The original monolithic code evolved organically with async operations. The DDD refactoring tried to create clean interfaces but created a fundamental mismatch:

- **Infrastructure Reality**: `ProviderManager.list_repositories()` detects if called from async context and switches behavior
- **Application Interface**: `ProviderOperations.list_repositories()` is defined as sync returning `List[Repository]`
- **Adapter Attempt**: `ProviderManagerAdapter` tries to bridge this with thread pools and `asyncio.run()`
- **Result**: "async for requires __aiter__" error because of nested event loop conflicts

**Why This Matters**: This isn't just a bug - it's a fundamental architectural flaw. The abstraction doesn't match the reality of the underlying system.

### 2. Lost Domain Knowledge

**What Got Lost**:
- The `list` command with powerful wildcard queries (`*/*/*`) - a KEY feature
- Command options: `--dry-run`, `--exclude`, `--include` 
- The intricate event loop management logic
- Provider-specific handling nuances

**Why**: The refactoring focused on structure over preserving functionality. Classic case of "the operation was a success but the patient died."

### 3. Over-Engineering vs. Pragmatism

**Over-Engineered**:
- Event bus for a CLI that doesn't need real-time events
- Pipeline pattern for operations that are fundamentally simple
- Separate bulk_operation_service when the operations aren't that complex
- Multiple layers of abstraction for what amounts to "list repos, then clone them"

**Under-Engineered**:
- No proper async/sync boundary handling
- No tests for the new architecture
- Incomplete implementations (hardcoded git status)
- Missing error aggregation and recovery

## Recommended Plan of Attack

### Phase 1: Make It Work (Critical - 1-2 days)

**Goal**: Get basic clone-all and pull-all working without errors

1. **Fix the Async/Sync Boundary**
   - Option A: Make `ProviderOperations` interface fully async
   - Option B: Make provider adapters handle async internally with proper event loop isolation
   - **Recommendation**: Option A - embrace async all the way up

2. **Fix Import Paths**
   ```python
   # Move adapters to expected location or fix imports
   mkdir -p mgit/infrastructure/adapters/
   mv mgit/infrastructure/*_adapter.py mgit/infrastructure/adapters/
   ```

3. **Add Missing Domain Fields**
   ```python
   # In OperationOptions
   exclude_repos: List[str] = field(default_factory=list)
   include_repos: List[str] = field(default_factory=list)
   ```

4. **Fix Event Data Types**
   - Standardize on string fields for repository identification
   - Make events consistent across the entire flow

### Phase 2: Restore Lost Features (High Priority - 2-3 days)

1. **Port the `list` Command**
   - The query parser exists but isn't wired up
   - This is a beloved feature that must be restored

2. **Restore Missing Options**
   - Add back --exclude and --include (already in domain model)
   - Implement proper filtering logic

3. **Fix Git Status**
   - Replace hardcoded implementation with real git commands
   - Use existing status logic from main branch

### Phase 3: Simplify and Stabilize (Medium Priority - 2-3 days)

1. **Question Everything**
   - Do we need the event bus? (Probably not)
   - Do we need pipelines? (Maybe, but simpler)
   - Do we need bulk as a subcommand? (No, remove it)

2. **Add Comprehensive Tests**
   - Unit tests for each layer
   - Integration tests for commands
   - Mock the provider API calls

3. **Document the Architecture**
   - Why each decision was made
   - How to add new providers
   - How to add new commands

### Phase 4: Optimize the Architecture (Low Priority - Optional)

1. **Consider Alternative Patterns**
   - Command pattern instead of services
   - Simpler adapter pattern without full DDD
   - Direct async commands without service layer

2. **Performance Improvements**
   - Better concurrency management
   - Smarter error recovery
   - Progress reporting optimization

## Critical Decision Points

### 1. Async All The Way?
**Current**: Mixed sync/async interfaces
**Recommendation**: Make application layer async, let Typer handle the sync boundary at CLI level

### 2. Event Bus - Keep or Kill?
**Current**: Complex event system for progress tracking
**Recommendation**: Simplify to direct callbacks or remove entirely

### 3. Domain Purity vs. Pragmatism?
**Current**: Pure domain models with no behavior
**Recommendation**: Add behavior to domain models (e.g., `Repository.get_clone_path()`)

### 4. Service Layer Thickness?
**Current**: Thick service layer with all logic
**Recommendation**: Thin service layer, push logic down to domain or up to commands

## Alternative Architecture Proposal

Instead of 4 layers, consider 3:

1. **CLI Layer** (Presentation)
   - Typer commands
   - Progress display
   - Error formatting

2. **Core Layer** (Domain + Application)
   - Repository operations
   - Provider abstraction
   - Business logic

3. **Infrastructure Layer**
   - Git operations
   - Provider API calls
   - Configuration

This would be simpler while still maintaining separation of concerns.

## Risk Assessment

**High Risk**:
- Current architecture may be fundamentally incompatible with async providers
- May need to revert to monolithic approach with better organization

**Medium Risk**:
- Team may not understand DDD patterns
- Over-abstraction may make debugging harder

**Low Risk**:
- Performance is unlikely to be worse
- Can always fall back to main branch

## Recommendation

**Short Term**: Fix critical issues to make it work
**Long Term**: Consider simplifying the architecture

The DDD pattern is good for large systems with complex domains. For a CLI tool that essentially does "list repos and clone them", it might be overkill. A simpler modular architecture might serve better.

## Command Reference Table

| Command | Option | Short | Type | Default | Description |
|---------|--------|-------|------|---------|-------------|
| **login** | --config | -cfg | TEXT | None | Named provider configuration to test |
| | --provider | -p | TEXT | None | Provider type (azuredevops, github, bitbucket) |
| | --name | -n | TEXT | None | Name for new provider configuration |
| | --org | -o | TEXT | None | Provider organization/workspace URL |
| | --token | -t | TEXT | None | Access token (PAT/API token) |
| | --store/--no-store | | BOOL | store | Store new configuration in config file |
| **clone-all** | project | | TEXT | Required | Project name (positional argument) |
| | rel_path | | TEXT | Required | Relative path to clone into (positional) |
| | --config | -cfg | TEXT | None | Named provider configuration |
| | --url | -u | TEXT | None | Organization URL (auto-detects provider) |
| | --concurrency | -c | INT | 4 | Number of concurrent clone operations |
| | --update-mode | -um | ENUM | skip | How to handle existing folders (skip/pull/force) |
| **pull-all** | project | | TEXT | Required | Project name (positional argument) |
| | rel_path | | TEXT | Required | Relative path where repositories exist |
| | --config | -cfg | TEXT | None | Named provider configuration |
| | --concurrency | -c | INT | 4 | Number of concurrent pull operations |
| | --update-mode | -um | ENUM | skip | How to handle existing folders (skip/pull/force) |
| **config** | --list | -l | FLAG | | List all configured providers |
| | --show | -s | TEXT | None | Show details for a specific provider |
| | --set-default | -d | TEXT | None | Set the default provider |
| | --remove | -r | TEXT | None | Remove a provider configuration |
| | --global | -g | FLAG | | Show global settings |
| **list** | query | | TEXT | Required | Query pattern (org/project/repo) - **NOT IN REFACTORED CODE** |
| | --provider | -p | TEXT | None | Provider configuration name |
| | --format | -f | TEXT | table | Output format (table, json) |
| | --limit | -l | INT | None | Maximum results to return |
| **status** | path | | PATH | . | The path to scan for repositories |
| | --concurrency | -c | INT | 10 | Number of concurrent status checks |
| | --output | -o | TEXT | table | Output format (table, json) |
| | --show-clean/--all | | FLAG | | Show all repositories, not just dirty |
| | --fetch | | FLAG | | Run 'git fetch' before checking status |
| | --fail-on-dirty | | FLAG | | Exit with error code if any repo has changes |
| **generate-env** | | | | | Generate sample environment file |

### Missing from Refactored Code:
- ❌ `list` command with wildcard support (exists in main, not in refactor)
- ❌ `--dry-run` option for clone-all/pull-all
- ❌ `--exclude` option for clone-all/pull-all
- ❌ `--include` option for clone-all/pull-all