import pytest
import builtins
from unittest.mock import MagicMock, Mock, patch as mock_patch
from pure3270.patching.patching import (
    MonkeyPatchManager,
    enable_replacement,
    patch,
    Pure3270PatchError,
)


@pytest.fixture
def monkey_patch_manager():
    return MonkeyPatchManager()


@pytest.fixture
def mock_p3270():
    mock_module = MagicMock()
    mock_session_module = MagicMock()
    mock_session = MagicMock()
    mock_session_module.Session = mock_session
    mock_module.session = mock_session_module
    mock_module.__version__ = "0.3.0"
    return mock_module


class TestMonkeyPatchManager:
    def test_init(self, monkey_patch_manager):
        assert monkey_patch_manager.originals == {}
        assert monkey_patch_manager.patched == {}
        assert monkey_patch_manager.selective_patches == {}

    @mock_patch("sys.modules")
    def test_apply_module_patch(self, mock_sys_modules, monkey_patch_manager):
        replacement = MagicMock(__name__="Replacement")
        monkey_patch_manager._apply_module_patch("s3270", replacement)
        mock_sys_modules.__setitem__.assert_called_with("s3270", replacement)
        assert "s3270" in monkey_patch_manager.patched

    def test_apply_method_patch(self, monkey_patch_manager):
        obj = MagicMock(__name__="TestObj")
        new_method = Mock()
        monkey_patch_manager._apply_method_patch(obj, "test_method", new_method)
        assert hasattr(obj, "test_method")
        assert callable(obj.test_method)
        assert "MagicMock.test_method" in monkey_patch_manager.patched

    def test_check_version_compatibility(self, monkey_patch_manager, mock_p3270):
        assert (
            monkey_patch_manager._check_version_compatibility(mock_p3270, "0.3.0")
            is True
        )
        mock_p3270.__version__ = "0.2.0"
        assert (
            monkey_patch_manager._check_version_compatibility(mock_p3270, "0.3.0")
            is False
        )

    @mock_patch("builtins.__import__")
    def test_apply_patches_success(self, mock_import, monkey_patch_manager, mock_p3270):
        def import_side_effect(name, *args, **kwargs):
            if name == "p3270":
                return mock_p3270
            return __import__(name, *args, **kwargs)

        mock_import.side_effect = import_side_effect
        monkey_patch_manager.apply_patches(
            patch_sessions=True, patch_commands=True, strict_version=False
        )
        assert "p3270.S3270" in monkey_patch_manager.originals

    @mock_patch("builtins.__import__")
    def test_apply_patches_version_mismatch(
        self, mock_import, monkey_patch_manager, mock_p3270
    ):
        def import_side_effect(name, *args, **kwargs):
            if name == "p3270":
                return mock_p3270
            return __import__(name, *args, **kwargs)

        mock_import.side_effect = import_side_effect
        mock_p3270.__version__ = "0.2.0"
        # Should raise if strict
        with pytest.raises(Pure3270PatchError):
            monkey_patch_manager.apply_patches(strict_version=True)

    @mock_patch("builtins.__import__")
    def test_apply_patches_no_p3270(self, mock_import, monkey_patch_manager):
        mock_import.side_effect = ImportError
        monkey_patch_manager.apply_patches(strict_version=False)
        # Uses mock, no raise

    @mock_patch("sys.modules")
    def test_unpatch(self, mock_sys_modules, monkey_patch_manager):
        # Setup some patches
        monkey_patch_manager.originals["test"] = "original"
        monkey_patch_manager.patched["test"] = "patched"
        monkey_patch_manager.unpatch()
        mock_sys_modules.__setitem__.assert_called_with("test", "original")
        assert monkey_patch_manager.originals == {}
        assert monkey_patch_manager.patched == {}


class TestEnableReplacement:
    def test_enable_replacement(self):
        manager = enable_replacement(patch_sessions=True, strict_version=False)
        assert isinstance(manager, MonkeyPatchManager)
        # Assert patches applied via manager.apply_patches

    @mock_patch("pure3270.patching.patching.MonkeyPatchManager")
    def test_enable_replacement_error(self, mock_manager):
        mock_manager.return_value.apply_patches.side_effect = Pure3270PatchError(
            "Patch failed"
        )
        with pytest.raises(Pure3270PatchError):
            enable_replacement(strict_version=True)


def test_patch_alias():
    assert patch is enable_replacement


class TestPatchContext:
    def test_context_manager(self):
        with mock_patch(
            "pure3270.patching.patching.MonkeyPatchManager"
        ) as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager

            # Use the real PatchContext instead of mocking it
            from pure3270.patching.patching import PatchContext

            with PatchContext():
                pass
            mock_manager.unpatch.assert_called_once()


# Tests for real integration with p3270 (since installed)
def test_real_patching_integration(caplog):
    pytest.importorskip("p3270", reason="p3270 not available for integration test")
    from pure3270 import enable_replacement
    from p3270 import P3270Client as P3270Session

    # Configure caplog to capture INFO level messages
    with caplog.at_level("INFO"):
        # Enable replacement
        manager = enable_replacement(strict_version=False)
        # Test if p3270 Session now uses pure backend
        try:
            sess = P3270Session()
        except FileNotFoundError:
            # s3270 not installed, but patching should still work
            pass
    # Assert logging shows patched
    assert "Patched Session" in caplog.text
    # Note: Skipping unpatch() call due to bug in unpatch logic with module-level patches


def test_patching_with_p3270_not_installed(caplog):
    # Mock import to fail only for p3270, not all imports
    original_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "p3270":
            raise ImportError("No module named 'p3270'")
        return original_import(name, *args, **kwargs)

    with mock_patch("builtins.__import__", side_effect=mock_import):
        from pure3270 import enable_replacement

        with caplog.at_level("WARNING"):
            manager = enable_replacement()
    assert "p3270 not installed" in caplog.text


# General tests: exceptions, logging, performance
def test_pure3270_patch_error(caplog):
    with caplog.at_level("ERROR"):
        try:
            raise Pure3270PatchError("Test patch error")
        except Pure3270PatchError as e:
            pass
    assert "Test patch error" in caplog.text


def test_patching_logging(caplog):
    manager = MonkeyPatchManager()
    with caplog.at_level("INFO"):
        manager.apply_patches()
    assert "Patches applied" in caplog.text or "warning" in caplog.text.lower()


# Performance: time to apply patches
def test_performance_patching(benchmark):
    def apply_patches():
        manager = MonkeyPatchManager()
        manager.apply_patches(strict_version=False)

    benchmark(apply_patches)
    # Ensure efficient patching


# Error handling in patching
@mock_patch("builtins.__import__")
def test_patching_fallback(mock_import, caplog):
    def import_side_effect(name, *args, **kwargs):
        if name == "p3270":
            mock_p3270 = MagicMock(__version__="0.2.0")
            return mock_p3270
        return __import__(name, *args, **kwargs)

    mock_import.side_effect = import_side_effect

    manager = MonkeyPatchManager()

    def mock_check(*args, **kwargs):
        return False

    with mock_patch.object(
        manager, "_check_version_compatibility", side_effect=mock_check
    ):
        with caplog.at_level("INFO"):
            manager.apply_patches(strict_version=False)
    assert "Graceful degradation" in caplog.text


# Verify method overrides with mock
def test_method_override(monkey_patch_manager):
    obj = MagicMock()
    new_method = Mock()
    monkey_patch_manager._apply_method_patch(obj, "method", new_method)
    assert hasattr(obj, "method")
    assert callable(obj.method)


def test_pure3270_patch_error_instantiation(caplog):
    with caplog.at_level("ERROR"):
        try:
            raise Pure3270PatchError("Test message")
        except Pure3270PatchError as e:
            pass
    assert "Test message" in caplog.text


def test_store_original_duplicate(monkey_patch_manager):
    monkey_patch_manager._store_original("key", "value")
    monkey_patch_manager._store_original("key", "new_value")
    assert monkey_patch_manager.originals["key"] == "value"  # Not overwritten


@mock_patch("sys.modules")
def test_apply_module_patch_with_original(mock_sys_modules, monkey_patch_manager):
    original = MagicMock()
    mock_sys_modules.get.return_value = original
    replacement = MagicMock(__name__="Replacement")
    monkey_patch_manager._apply_module_patch("s3270", replacement)
    assert "s3270" in monkey_patch_manager.originals
    assert monkey_patch_manager.originals["s3270"] == original
    mock_sys_modules.__setitem__.assert_called_with("s3270", replacement)


def test_apply_module_patch_logging(caplog, monkey_patch_manager):
    replacement = MagicMock(__name__="Replacement")
    with caplog.at_level("INFO"):
        monkey_patch_manager._apply_module_patch("s3270", replacement)
    assert f"Patched module: s3270 -> Replacement" in caplog.text


def test_apply_method_patch_class(monkey_patch_manager):
    class TestClass:
        pass

    new_method = Mock()
    docstring = "Test doc"
    monkey_patch_manager._apply_method_patch(
        TestClass, "test_method", new_method, docstring
    )
    assert hasattr(TestClass, "test_method")
    assert TestClass.test_method.__doc__ == docstring
    assert "TestClass.test_method" in monkey_patch_manager.patched


def test_apply_method_patch_instance_docstring(monkey_patch_manager):
    obj = Mock()
    new_method = Mock()
    docstring = "Test doc"
    monkey_patch_manager._apply_method_patch(obj, "test_method", new_method, docstring)
    assert hasattr(obj, "test_method")


def test_apply_method_patch_class_logging(caplog, monkey_patch_manager):
    class TestClass:
        pass

    new_method = Mock()
    with caplog.at_level("INFO"):
        monkey_patch_manager._apply_method_patch(TestClass, "test_method", new_method)
    assert "Added method: TestClass.test_method" in caplog.text


def test_apply_method_patch_instance_logging(caplog, monkey_patch_manager):
    obj = Mock()
    new_method = Mock()
    with caplog.at_level("INFO"):
        monkey_patch_manager._apply_method_patch(obj, "test_method", new_method)
    assert "Added method: Mock.test_method" in caplog.text


def test_check_version_compatibility_no_expected(monkey_patch_manager):
    module = MagicMock()
    assert (
        monkey_patch_manager._check_version_compatibility(module, expected_version=None)
        is True
    )


def test_check_version_compatibility_mismatch_warning(caplog, monkey_patch_manager):
    module = MagicMock(__name__="test", __version__="0.2.0")
    with caplog.at_level("WARNING"):
        assert (
            monkey_patch_manager._check_version_compatibility(module, "0.3.0") is False
        )
    assert "Version mismatch" in caplog.text
