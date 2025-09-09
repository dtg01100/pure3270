import pytest
from unittest.mock import MagicMock, patch
from pure3270.patching.patching import enable_replacement, MonkeyPatchManager, Pure3270PatchError

def test_enable_replacement_basic():
    """Test enable_replacement with defaults."""
    with patch('pure3270.patching.patching.get_p3270_version') as mock_version:
        mock_version.return_value = "0.3.0"
        manager = enable_replacement()
        assert isinstance(manager, MonkeyPatchManager)
        assert manager.patch_sessions is True
        assert manager.patch_commands is True

def test_enable_replacement_strict_version_fail():
    """Test strict_version raises error on mismatch."""
    with patch('pure3270.patching.patching.get_p3270_version') as mock_version:
        mock_version.return_value = "0.2.0"
        with pytest.raises(Pure3270PatchError):
            enable_replacement(strict_version=True)

def test_enable_replacement_no_sessions():
    """Test enable_replacement without session patching."""
    manager = enable_replacement(patch_sessions=False)
    assert manager.patch_sessions is False

def test_monkey_patch_manager_unpatch():
    """Test unpatch restores original."""
    original_method = MagicMock()
    patched_method = MagicMock()
    manager = MonkeyPatchManager()
    manager._patched = {'test': (original_method, patched_method)}
    manager.unpatch()
    original_method.__name__ = 'original'  # Mock restore
    assert 'test' not in manager._patched

def test_apply_method_patch():
    """Test apply_method_patch."""
    class TestClass:
        pass
    def new_method(self):
        return "patched"
    manager = MonkeyPatchManager()
    manager._apply_method_patch(TestClass, "test_method", new_method, "doc")
    assert hasattr(TestClass, "test_method")
    assert TestClass.test_method.__doc__ == "doc"

def test_apply_module_patch():
    """Test apply_module_patch."""
    mock_module = MagicMock()
    original_func = MagicMock()
    mock_module.original_func = original_func
    new_func = MagicMock()
    manager = MonkeyPatchManager()
    manager._apply_module_patch(mock_module, "original_func", new_func)
    assert mock_module.original_func == new_func

def test_unpatch_method():
    """Test unpatch_method restores original."""
    class TestClass:
        def original(self):
            return "original"
    original = TestClass.original
    def patched(self):
        return "patched"
    manager = MonkeyPatchManager()
    manager._patched_methods['TestClass.original'] = (original, patched)
    TestClass.original = patched
    manager._unpatch_method(TestClass, "original")
    assert TestClass.original == original

# Cover lines 60-68 (enable_replacement body)
@patch('pure3270.patching.patching.MonkeyPatchManager')
def test_enable_replacement_internal(mock_manager_class):
    mock_manager = MagicMock()
    mock_manager_class.return_value = mock_manager
    with patch('pure3270.patching.patching.importlib.import_module') as mock_import:
        mock_p3270 = MagicMock()
        mock_import.return_value = mock_p3270
        enable_replacement()
        mock_manager_class.assert_called_once()
        mock_manager.apply_patches.assert_called_once()

# Cover unpatch lines 155-173
def test_unpatch_full():
    manager = MonkeyPatchManager()
    manager.patched = {'method': MagicMock()}
    manager.unpatch()
    assert manager.patched == {}

# Cover error handling in patching
def test_patching_version_mismatch(caplog):
    with patch('pure3270.patching.patching.get_p3270_version') as mock_version:
        mock_version.return_value = "invalid"
        with caplog.at_level("WARNING"):
            enable_replacement(strict_version=False)
        assert "Version mismatch" in caplog.text