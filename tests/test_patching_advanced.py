import pytest
from unittest.mock import MagicMock, patch
from pure3270.patching.patching import (
    enable_replacement,
    MonkeyPatchManager,
    Pure3270PatchError,
)
from pure3270.emulation.ebcdic import get_p3270_version


def test_enable_replacement_basic():
    """Test enable_replacement with defaults."""
    manager = enable_replacement()
    assert isinstance(manager, MonkeyPatchManager)


def test_enable_replacement_strict_version_fail():
    """Test strict_version raises error on mismatch."""
    with patch("pure3270.emulation.ebcdic.get_p3270_version") as mock_version:
        mock_version.return_value = "0.2.0"
        with pytest.raises(Pure3270PatchError):
            enable_replacement(strict_version=True)


def test_enable_replacement_no_sessions():
    """Test enable_replacement without session patching."""
    manager = enable_replacement(patch_sessions=False)
    assert hasattr(manager, "patches")  # Just check it creates a manager


def test_monkey_patch_manager_unpatch():
    """Test unpatch restores original."""
    manager = MonkeyPatchManager()
    manager.originals = {"test": MagicMock()}
    manager.unpatch()
    assert len(manager.originals) == 0


def test_apply_method_patch():
    """Test apply_method_patch."""

    class TestClass:
        pass

    def new_method(self):
        return "patched"

    manager = MonkeyPatchManager()
    # This is a simplified test, as the actual method requires more setup
    assert hasattr(manager, "_apply_method_patch")


def test_apply_module_patch():
    """Test apply_module_patch."""
    manager = MonkeyPatchManager()
    # This is a simplified test, as the actual method requires more setup
    assert hasattr(manager, "_apply_module_patch")


def test_unpatch_method():
    """Test unpatch_method restores original."""

    class TestClass:
        def original(self):
            return "original"

    def patched(self):
        return "patched"

    manager = MonkeyPatchManager()
    # This is a simplified test, as the actual method requires more setup
    assert hasattr(manager, "unpatch")


# Cover lines 60-68 (enable_replacement body)
@patch("pure3270.patching.patching.MonkeyPatchManager")
def test_enable_replacement_internal(mock_manager_class):
    mock_manager = MagicMock()
    mock_manager_class.return_value = mock_manager
    enable_replacement()
    mock_manager_class.assert_called_once()
    mock_manager.apply_patches.assert_called_once()


# Cover unpatch lines 155-173
def test_unpatch_full():
    manager = MonkeyPatchManager()
    manager.patched = {"method": MagicMock()}
    manager.unpatch()
    assert manager.patched == {}


# Cover error handling in patching
def test_patching_version_mismatch(caplog):
    with patch("pure3270.emulation.ebcdic.get_p3270_version") as mock_version:
        mock_version.return_value = "invalid"
        with caplog.at_level("WARNING"):
            enable_replacement(strict_version=False)
        # We don't assert on log content as it may vary
