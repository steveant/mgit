#!/usr/bin/env python3
"""
Test script for the mgit auth module.

This script demonstrates and tests the credential management functionality.
"""

import sys
from pathlib import Path

# Add the mgit package to the path
sys.path.insert(0, str(Path(__file__).parent))

from mgit.auth import CredentialManager, ProviderType
from mgit.auth.models import Credential


def test_credential_operations():
    """Test basic credential operations."""
    print("Testing mgit credential management system...\n")
    
    # Initialize manager
    manager = CredentialManager()
    print(f"Storage backend: {manager.get_storage_info()}\n")
    
    # Test storing credentials
    print("1. Testing credential storage:")
    test_creds = [
        ("azure-devops", "default", "test-pat-12345678901234567890123456789012345678901234567890", "user@example.com", "https://dev.azure.com/myorg"),
        ("github", "personal", "ghp_testtoken1234567890123456789012345678", None, None),
        ("bitbucket", "work", "app-password-12345678901234567890", "work@example.com", "https://bitbucket.org/workspace"),
    ]
    
    for provider, name, token, username, url in test_creds:
        try:
            cred = manager.store_credential(
                provider=provider,
                name=name,
                credential=token,
                username=username,
                url=url,
                metadata={"test": True, "description": f"Test {provider} credential"}
            )
            print(f"  ✓ Stored {provider}:{name}")
            
            # Validate
            if manager.validate_credential(cred):
                print(f"    Format: Valid")
            else:
                print(f"    Format: Invalid/Warning")
        except Exception as e:
            print(f"  ✗ Failed to store {provider}:{name}: {e}")
    
    print("\n2. Testing credential retrieval:")
    for provider, name, _, _, _ in test_creds:
        cred = manager.get_credential(provider, name)
        if cred:
            print(f"  ✓ Retrieved {provider}:{name}")
            print(f"    Value: {cred.mask_value()}")
            print(f"    Username: {cred.username or 'N/A'}")
            print(f"    URL: {cred.url or 'N/A'}")
        else:
            print(f"  ✗ Failed to retrieve {provider}:{name}")
    
    print("\n3. Testing credential listing:")
    all_creds = manager.list_credentials()
    print(f"  Total credentials: {len(all_creds)}")
    
    for provider_type in ProviderType:
        provider_creds = manager.list_credentials(provider_type.value)
        print(f"  {provider_type.value}: {len(provider_creds)} credential(s)")
    
    print("\n4. Testing provider credential lookup:")
    # Test URL-based lookup
    cred = manager.get_provider_credential("azure-devops", "https://dev.azure.com/myorg")
    if cred:
        print(f"  ✓ Found credential for Azure DevOps URL: {cred.name}")
    
    # Test default lookup
    cred = manager.get_provider_credential("github")
    if cred:
        print(f"  ✓ Found default GitHub credential: {cred.name}")
    
    print("\n5. Testing credential deletion:")
    for provider, name, _, _, _ in test_creds:
        if manager.delete_credential(provider, name):
            print(f"  ✓ Deleted {provider}:{name}")
        else:
            print(f"  ✗ Failed to delete {provider}:{name}")
    
    # Verify deletion
    remaining = manager.list_credentials()
    print(f"\n  Remaining credentials: {len(remaining)}")
    
    print("\n✅ Credential management tests completed!")


def test_cli_commands():
    """Test CLI commands."""
    print("\n\nTesting CLI commands:")
    print("Try these commands in your terminal:\n")
    
    commands = [
        "python -m mgit auth --help",
        "python -m mgit auth store azure-devops myorg --username user@example.com",
        "python -m mgit auth list",
        "python -m mgit auth get azure-devops myorg",
        "python -m mgit auth validate azure-devops myorg",
        "python -m mgit auth info",
        "python -m mgit auth delete azure-devops myorg",
    ]
    
    for cmd in commands:
        print(f"  $ {cmd}")


if __name__ == "__main__":
    test_credential_operations()
    test_cli_commands()