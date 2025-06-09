#!/usr/bin/env python3
"""Test script for the refactored CLI."""

import sys
import subprocess
from pathlib import Path

# Add worktree to path
sys.path.insert(0, str(Path(__file__).parent))

def test_cli_help():
    """Test CLI help command."""
    print("Testing CLI help...")
    result = subprocess.run(
        [sys.executable, "-m", "mgit", "--help"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent
    )
    print(f"Exit code: {result.returncode}")
    if result.returncode == 0:
        print("✓ CLI help works!")
        print("\nOutput preview:")
        print(result.stdout[:200] + "...")
    else:
        print("✗ CLI help failed!")
        print("Error:", result.stderr)
    return result.returncode == 0

def test_imports():
    """Test all modular imports."""
    print("\nTesting modular imports...")
    try:
        # Domain layer
        from mgit.domain.models.operations import OperationType, UpdateMode
        from mgit.domain.models.repository import Repository
        from mgit.domain.models.context import OperationContext
        from mgit.domain.events import BulkOperationStarted
        print("✓ Domain layer imports work")
        
        # Application layer
        from mgit.application.services.bulk_operation_service import BulkOperationService
        from mgit.application.container import DIContainer
        from mgit.application.ports import EventBus, GitOperations, ProviderOperations
        print("✓ Application layer imports work")
        
        # Infrastructure layer
        from mgit.infrastructure.event_bus import InMemoryEventBus
        from mgit.infrastructure.adapters.git_adapter import GitManagerAdapter
        from mgit.infrastructure.adapters.provider_adapter import ProviderManagerAdapter
        print("✓ Infrastructure layer imports work")
        
        # Presentation layer
        from mgit.presentation.cli.commands.bulk_ops import clone_all, pull_all
        from mgit.presentation.cli.progress.progress_handler import CliProgressHandler
        print("✓ Presentation layer imports work")
        
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False

def test_container():
    """Test dependency injection container."""
    print("\nTesting DI container...")
    try:
        from mgit.application.container import get_container, reset_container
        
        reset_container()
        container = get_container()
        
        # Test singleton behavior
        config1 = container.config_manager
        config2 = container.config_manager
        assert config1 is config2, "Container should return same instance"
        print("✓ Container singleton behavior works")
        
        # Test lazy loading
        reset_container()
        container = get_container()
        assert container._config_manager is None, "Should not be initialized yet"
        _ = container.config_manager
        assert container._config_manager is not None, "Should be initialized now"
        print("✓ Container lazy loading works")
        
        return True
    except Exception as e:
        print(f"✗ Container test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing refactored mgit architecture...\n")
    
    tests = [
        test_imports,
        test_container,
        test_cli_help,
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print(f"\n{'='*50}")
    passed = sum(results)
    total = len(results)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("✅ All tests passed! The refactored architecture is working.")
    else:
        print("❌ Some tests failed. Please check the errors above.")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())