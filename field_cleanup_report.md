# Field Name Cleanup Report

This report documents all occurrences of old field names and patterns that need to be cleaned up in the mgit codebase.

## Summary of Old Field Names to Clean Up
- `pat` → `token` (unified field name)
- `organization_url` → `url` (unified field name)
- `app_password` → `token` (unified field name for BitBucket)
- `default_workspace` → `workspace` (remove "default_" prefix)
- `org` (when used as a field) → `url` (unified field name)

## Occurrences by File

### Configuration Files

#### `/mgit/config/yaml_manager.py`
- **Lines 356-357**: Migration mapping `"AZURE_DEVOPS_ORG_URL": ("provider", "azuredevops", "org_url")` and `"AZURE_DEVOPS_EXT_PAT": ("provider", "azuredevops", "pat")`
  - Change to: Map to unified fields `url` and `token`
- **Lines 359-360**: Migration mapping `"GITHUB_ORG_URL": ("provider", "github", "org_url")` and `"GITHUB_PAT": ("provider", "github", "token")`
  - Change to: Map to unified fields `url` and `token`
- **Lines 362-363**: Migration mapping `"BITBUCKET_ORG_URL": ("provider", "bitbucket", "org_url")` and `"BITBUCKET_APP_PASSWORD": ("provider", "bitbucket", "app_password")`
  - Change to: Map to unified fields `url` and `token`

### Provider Implementations

#### `/mgit/providers/manager.py`
- **Lines 182-183**: Field mapping for Azure DevOps:
  ```python
  self._config["organization_url"] = self._config["url"]
  self._config["pat"] = self._config["token"]
  ```
  - Status: This is the correct mapping logic to maintain backward compatibility
  - Action: Keep but add comment explaining it's for backward compatibility

- **Lines 186-187**: Field mapping for GitHub:
  ```python
  self._config["pat"] = self._config["token"]
  ```
  - Status: This is the correct mapping logic to maintain backward compatibility
  - Action: Keep but add comment explaining it's for backward compatibility

- **Lines 190-191**: Field mapping for BitBucket:
  ```python
  self._config["username"] = self._config["user"]
  self._config["app_password"] = self._config["token"]
  ```
  - Status: This is the correct mapping logic to maintain backward compatibility
  - Action: Keep but add comment explaining it's for backward compatibility

#### `/mgit/providers/azdevops.py`
- **Lines 45-46**: Reading old field names:
  ```python
  self.organization_url = config.get("organization_url", "")
  self.pat = config.get("pat", "")
  ```
  - Action: These are correctly using the mapped values from ProviderManager
  - No change needed as ProviderManager handles the mapping

#### `/mgit/providers/bitbucket.py`
- **Lines 75-76**: Reading old field names:
  ```python
  self.username = config.get("username", "")
  self.app_password = config.get("app_password", "")
  ```
  - Action: These are correctly using the mapped values from ProviderManager
  - No change needed as ProviderManager handles the mapping

#### `/mgit/providers/github.py`
- **Line 82**: Reading old field name:
  ```python
  self.pat = config.get("pat", "")
  ```
  - Action: This is correctly using the mapped value from ProviderManager
  - No change needed as ProviderManager handles the mapping

### CLI Commands

#### `/mgit/__main__.py`
- **Line 73**: Checking for old field names in config display:
  ```python
  "****" if provider_config.get("pat") or provider_config.get("token") else "Not set"
  ```
  - Action: Remove fallback check for "pat", use only "token"
  
- **Lines 111-117**: Setting token fields based on provider:
  ```python
  if provider_key == "github":
      config[provider_key]["token"] = token
  else:
      config[provider_key]["pat"] = token
  ```
  - Action: Always use "token" field for all providers

### Security Module

#### `/mgit/security/credentials.py`
- **Line 24**: Pattern name `"bitbucket_app_password"`
  - Action: Rename to `"bitbucket_token"` for consistency
- **Line 35**: Sensitive field `"pat"`
  - Action: Keep as it's for masking any occurrence
- **Line 42**: Sensitive field `"app_password"`
  - Action: Keep as it's for masking any occurrence
- **Line 333**: Function name `validate_bitbucket_app_password`
  - Action: Rename to `validate_bitbucket_token`

### Documentation

#### `/README.md`
- **Line 314**: Example configuration showing `app_password`:
  ```yaml
  app_password: your-bitbucket-app-password
  ```
  - Action: Change to `token: your-bitbucket-app-password` with comment explaining it's an app password

### Test Files

#### `/tests/integration/test_auth_commands.py`
- **Lines 85-86**: Environment variables `AZURE_DEVOPS_ORG_URL` and `AZURE_DEVOPS_PAT`
  - Action: These are legacy environment variable names for backward compatibility
  - No change needed, but could add newer unified names as alternatives

## Recommendations

1. **Field Mapping Logic**: The current field mapping logic in `ProviderManager._validate_config()` is correctly handling the translation from unified fields to provider-specific fields. This should be retained for backward compatibility.

2. **Migration Path**: The migration logic in `yaml_manager.py` should be updated to migrate old field names to the new unified structure.

3. **Documentation**: Update all documentation and examples to use the unified field names consistently.

4. **Security Module**: The security module correctly treats all variations as sensitive fields for masking, which is appropriate.

5. **CLI Updates**: The CLI should be updated to always use unified field names when saving configurations.

## Action Items

1. Update `__main__.py` to use unified field names when saving configurations
2. Update README.md to show unified field structure in examples
3. Add comments to field mapping logic explaining it's for backward compatibility
4. Update migration mappings to use unified field names as targets
5. Consider adding a configuration validator that warns users about deprecated field names