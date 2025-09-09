"""
Monkey patching utilities for pure3270 compatibility.
Applies patches to align with expected library versions.
"""

import sys
import logging
from unittest.mock import patch as mock_patch
from typing import Optional, Dict, Any
import types
from contextlib import contextmanager

from pure3270.session import AsyncSession as PureSession

logger = logging.getLogger(__name__)


class Pure3270PatchError(Exception):
    """Raised on patching errors."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logger.error(args[0] if args else str(self))


class MonkeyPatchManager:
    """
    Manager for applying monkey patches to modules.

    Handles version checks and patch application for compatibility.
    """

    def __init__(self, patches: Optional[Dict[str, Any]] = None):
        """
        Initialize the patch manager.

        Args:
            patches: Dictionary of patches to apply (module_name: patch_functions).
        """
        self.patches = patches or {}
        self.applied = set()
        self.originals = {}
        self.patched = {}
        self.selective_patches = {}
        logger.info("Initialized MonkeyPatchManager")

    def apply(self, module_name: str) -> bool:
        """
        Apply patches to a specific module.

        Args:
            module_name: Name of the module to patch.

        Returns:
            True if patches were applied successfully.

        Raises:
            ValueError: If module not found or patching fails.
        """
        if module_name in self.applied:
            return True
        module = sys.modules.get(module_name)
        if not module:
            raise ValueError(f"Module {module_name} not found.")
        for patch in self.patches.get(module_name, []):
            patch(module)
        self.applied.add(module_name)
        return True

    def _store_original(self, key: str, value: Any) -> None:
        if key not in self.originals:
            self.originals[key] = value

    def _apply_module_patch(self, module_name: str, replacement: Any) -> None:
        original = sys.modules.get(module_name)
        self._store_original(module_name, original)
        sys.modules[module_name] = replacement
        self.patched[module_name] = replacement
        logger.info(f"Patched module: {module_name} -> {replacement.__name__}")

    def _apply_method_patch(
        self,
        obj: Any,
        method_name: str,
        new_method: Any,
        docstring: Optional[str] = None,
    ) -> None:
        original = getattr(obj, method_name, None)
        if isinstance(obj, type):
            class_name = obj.__name__
        else:
            class_name = type(obj).__name__
        key = f"{class_name}.{method_name}"
        self._store_original(key, original)
        setattr(obj, method_name, new_method)
        if docstring:
            new_method.__doc__ = docstring
        self.patched[key] = new_method
        logger.info(f"Added method: {class_name}.{method_name}")

    def _check_version_compatibility(
        self, module: Any, expected_version: str = "0.3.0"
    ) -> bool:
        actual_version = getattr(module, "__version__", None)
        if actual_version != expected_version:
            logger.warning(
                f"Version mismatch: expected {expected_version}, got {actual_version}"
            )
            logger.info("Graceful degradation: proceeding with partial compatibility")
            return False
        return True

    def apply_patches(
        self,
        patch_sessions: bool = True,
        patch_commands: bool = True,
        strict_version: bool = False,
        expected_version: str = "0.3.0",
    ) -> None:
        try:
            import p3270

            version_compatible = self._check_version_compatibility(
                p3270, expected_version
            )
            if strict_version and not version_compatible:
                raise Pure3270PatchError(
                    f"Version incompatible: {getattr(p3270, '__version__', 'unknown')}"
                )
            if not version_compatible and not strict_version:
                logger.info(
                    "Graceful degradation: Version mismatch but continuing with patching"
                )
            if patch_sessions:
                original = getattr(p3270, "S3270", None)
                self._store_original("p3270.S3270", original)
                setattr(p3270, "S3270", PureSession)
                logger.info("Patched Session")
            logger.info("Patches applied")
        except ImportError as e:
            logger.warning(f"p3270 not installed: {e}")
            if strict_version:
                raise Pure3270PatchError("p3270 required for strict mode")
            self._store_original("p3270.S3270", None)
        except Exception as e:
            logger.error(f"Patch error: {e}")
            raise Pure3270PatchError(str(e))

    def unpatch(self) -> None:
        for key, original in self.originals.items():
            if original is None:
                continue  # Skip None originals
            if "." in key:
                # Method patch
                obj_name, method = key.rsplit(".", 1)
                # Try to reconstruct the object from the name
                try:
                    if obj_name in sys.modules:
                        obj = sys.modules[obj_name]
                    else:
                        # For class methods, try to find the class
                        parts = obj_name.split(".")
                        obj = sys.modules.get(parts[0])
                        if obj and len(parts) > 1:
                            for part in parts[1:]:
                                obj = getattr(obj, part, None)
                                if obj is None:
                                    break
                    if obj is not None:
                        setattr(obj, method, original)
                        logger.debug(f"Restored method {key}")
                except Exception as e:
                    logger.warning(f"Failed to restore method {key}: {e}")
            else:
                # Module patch
                sys.modules[key] = original
                logger.debug(f"Restored module {key}")
        self.originals.clear()
        self.patched.clear()
        logger.info("Unpatched all")


@contextmanager
def PatchContext(patches: Optional[Dict[str, Any]] = None):
    """
    Context manager for temporary patching.

    Args:
        patches: Patches to apply.

    Yields:
        Manager instance.
    """
    manager = MonkeyPatchManager(patches)
    try:
        yield manager
    finally:
        manager.unpatch()


def enable_replacement(
    patch_sessions: bool = True,
    patch_commands: bool = True,
    strict_version: bool = False,
    expected_version: str = "0.3.0",
) -> MonkeyPatchManager:
    """
    Enable replacement patching with version check.

    Args:
        patch_sessions: Whether to patch sessions.
        patch_commands: Whether to patch commands.
        strict_version: Whether to enforce strict version check.
        expected_version: The expected version for compatibility (default "0.3.0").

    Raises:
        ValueError: If version or replacement fails.
    """
    manager = MonkeyPatchManager()
    manager.apply_patches(
        patch_sessions=patch_sessions,
        patch_commands=patch_commands,
        strict_version=strict_version,
        expected_version=expected_version,
    )
    return manager


patch = enable_replacement
