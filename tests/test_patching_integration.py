import pytest
from unittest.mock import patch
import sys

from pure3270 import enable_replacement
from pure3270.patching.patching import MonkeyPatchManager, Pure3270PatchError


def test_real_p3270_patching():
    """Test patching with the real p3270 package."""
    # This test requires p3270 to be installed
    pytest.importorskip("p3270", reason="p3270 not available for integration test")

    import p3270

    # Enable replacement
    manager = enable_replacement(strict_version=False)

    # Verify that the patching worked
    assert hasattr(manager, "originals")
    assert "p3270.S3270" in manager.originals

    # Test that we can create a P3270Client
    # Note: We won't actually connect to anything, just test instantiation
    try:
        session = p3270.P3270Client()
        # If we get here, the patching worked (even if s3270 binary is not available)
    except FileNotFoundError:
        # This is expected if s3270 binary is not installed
        # But the patching should still have worked
        pass
    except Exception as e:
        # Any other exception indicates a problem with our patching
        raise e


def test_p3270_version_detection():
    """Test that we can properly detect the p3270 version."""
    pytest.importorskip("p3270", reason="p3270 not available for version test")

    from pure3270.emulation.ebcdic import get_p3270_version

    version = get_p3270_version()

    # Should be a string version number
    assert version is not None
    assert isinstance(version, str)
    # Should match what we know about the installed version
    assert version == "0.1.6"  # This is what we have installed


def test_patching_with_version_check():
    """Test patching with version checking."""
    pytest.importorskip("p3270", reason="p3270 not available for version test")

    # Test with correct version - should work
    manager = enable_replacement(expected_version="0.1.6", strict_version=False)
    assert isinstance(manager, MonkeyPatchManager)

    # Test with wrong version in non-strict mode - should work with warning
    with patch("pure3270.emulation.ebcdic.get_p3270_version") as mock_version:
        mock_version.return_value = "0.1.6"  # Mock the actual version
        manager = MonkeyPatchManager()
        # This should not raise an exception in non-strict mode
        manager.apply_patches(expected_version="0.3.0", strict_version=False)

    # Test with wrong version in strict mode - should raise exception
    with patch("pure3270.emulation.ebcdic.get_p3270_version") as mock_version:
        mock_version.return_value = "0.1.6"  # Mock the actual version
        manager = MonkeyPatchManager()
        with pytest.raises(Pure3270PatchError):
            manager.apply_patches(expected_version="0.3.0", strict_version=True)


def test_patching_unpatch():
    """Test that unpatching works correctly."""
    pytest.importorskip("p3270", reason="p3270 not available for unpatch test")

    import p3270

    # Store the original S3270 class
    original_s3270 = getattr(p3270, "S3270", None)

    # Apply patches
    manager = enable_replacement(strict_version=False)

    # Verify patching worked
    from pure3270.patching.s3270_wrapper import Pure3270S3270Wrapper

    assert p3270.S3270 is Pure3270S3270Wrapper

    # Unpatch
    manager.unpatch()

    # Verify unpatching worked
    assert getattr(p3270, "S3270", None) is original_s3270


if __name__ == "__main__":
    pytest.main([__file__])
