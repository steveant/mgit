# Python Files Requiring Field Name Updates

## Analysis Methodology

Systematic check of ALL Python files with old field references to determine what actually needs changing vs what's correct for backward compatibility.

## Files That Are CORRECT As-Is (No Changes Needed)

### 1. Provider Implementation Files
- **mgit/providers/azdevops.py** - Reads `organization_url` and `pat` ✅ CORRECT
- **mgit/providers/github.py** - Reads `pat` ✅ CORRECT  
- **mgit/providers/bitbucket.py** - Reads `app_password` ✅ CORRECT

**Reasoning**: These providers are SUPPOSED to read old field names because `ProviderManager` maps unified fields (`url`, `token`) to provider-specific fields (`organization_url`, `pat`, `app_password`) for backward compatibility. This is the correct design pattern.

### 2. Backward Compatibility Layer
- **mgit/providers/manager.py** - Contains field mapping logic ✅ CORRECT

**Reasoning**: This is the translation layer that enables users to use unified fields while providers continue using their original field names.

## Files Requiring Updates (8 files)

### 1. Critical CLI Logic (3 files)

#### mgit/__main__.py
**Lines needing updates**:
- Line 83: `--pat` CLI flag alias (decide: keep for compatibility or remove?)
- Lines 197, 201: Provider detection checking old field names
```python
# CURRENT (checking old fields):
if config.get("azure_devops", {}).get("pat"):
if config.get("bitbucket", {}).get("pat"):

# SHOULD BE (checking unified fields):
if config.get("azure_devops", {}).get("token"):
if config.get("bitbucket", {}).get("token"):
```

#### mgit/git/utils.py
**Function needing update**:
- `embed_pat_in_url(url: str, pat: str)` function signature and implementation
```python
# CURRENT:
def embed_pat_in_url(url: str, pat: str) -> str:

# SHOULD BE:
def embed_token_in_url(url: str, token: str) -> str:
```

#### mgit/security/patches.py  
**Lines needing updates**:
- Lines 296, 306: `getattr(self, "organization_url", "unknown")`
```python
# CURRENT:
organization=getattr(self, "organization_url", "unknown"),

# SHOULD BE:
organization=getattr(self, "url", "unknown"),
```

### 2. Test Files (5 files)

#### tests/conftest.py
**Test fixtures with old field names**:
- Line 334: `"token": "test-pat-token"` (naming)
- Line 489: URLs with embedded PATs

#### tests/unit/test_git.py
**Test cases for embed_pat_in_url**:
- Lines 171-183: All test cases need to use new function name
- Test data with "pat" parameters

#### tests/unit/test_utils.py  
**Test cases with PAT references**:
- Lines 23-37: Tests for `embed_pat_in_url` function
- Lines 191-206: Test configs with `"pat": "base-pat"`

#### tests/unit/test_providers.py
**Test data with old field names**:
- Line 215: `{"organization": "...", "pat": "token"}`
- Line 217: `{"username": "user", "app_password": "pass"}`

#### tests/integration/test_auth_commands.py
**Environment variable references**:
- Lines 85-86: `AZURE_DEVOPS_ORG_URL`, `AZURE_DEVOPS_PAT`
- **Decision**: Keep for backward compatibility testing or update?

## Summary

### Critical Production Code: 3 files
1. **mgit/__main__.py** - Provider detection logic
2. **mgit/git/utils.py** - Function signature change  
3. **mgit/security/patches.py** - Attribute access

### Test Infrastructure: 5 files
1. **tests/conftest.py** - Test fixtures
2. **tests/unit/test_git.py** - Unit tests
3. **tests/unit/test_utils.py** - Unit tests
4. **tests/unit/test_providers.py** - Unit tests
5. **tests/integration/test_auth_commands.py** - Integration tests

## Decision Points

### 1. CLI Flag Compatibility
Keep `--pat` as alias for `--token`? 
- **Pro**: Backward compatibility for users' scripts
- **Con**: Perpetuates old terminology

### 2. Function Naming
Change `embed_pat_in_url` to `embed_token_in_url`?
- **Pro**: Consistent terminology
- **Con**: Breaking change for any external callers
- **Recommendation**: Change it - it's an internal utility

### 3. Test Environment Variables
Update integration tests to use new environment variable names?
- **Pro**: Tests validate new patterns
- **Con**: Need to support old patterns for real users
- **Recommendation**: Test both old and new for backward compatibility

## Total: 8 Python Files Need Updates

This is significantly less than the ~33 total files with field references because most are in documentation (15+ files) or are correctly implementing backward compatibility patterns.