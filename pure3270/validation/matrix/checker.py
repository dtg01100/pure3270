import importlib
import os
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

RFC_DIR = Path(__file__).parent


class Requirement:
    def __init__(self, data: dict[str, Any], section: str):
        self.id: str = data["id"]
        self.text: str = data["text"]
        self.rfc_keyword: str = data["rfc_keyword"]
        self.status: str = data["status"]
        self.tests: list[str] = data.get("tests", [])
        self.section = section

    def is_tested(self) -> bool:
        return self.status == "tested"

    def has_resolvable_tests(self) -> bool:
        return len(self.stale_tests()) == 0

    def stale_tests(self) -> list[str]:
        return [t for t in self.tests if not _resolve_test_ref(t)]


def _resolve_test_ref(ref: str) -> bool:
    try:
        if "::" in ref:
            module_path, func_name = ref.split("::", 1)
            func_name = func_name.replace("::", ".")
            if "." in func_name:
                class_name, method_name = func_name.rsplit(".", 1)
                mod = importlib.import_module(module_path)
                cls = getattr(mod, class_name, None)
                if cls is None:
                    return False
                return hasattr(cls, method_name)
            else:
                mod = importlib.import_module(module_path)
                return hasattr(mod, func_name)
        return False
    except (ImportError, AttributeError):
        return False


class RfcMatrix:
    def __init__(self) -> None:
        self.requirements: list[Requirement] = []
        self._loaded = False

    def load_all(self) -> None:
        for fname in sorted(os.listdir(RFC_DIR)):
            if fname.endswith(".yaml"):
                with open(RFC_DIR / fname) as f:
                    data = yaml.safe_load(f)
                for section in data.get("sections", []):
                    for req_data in section.get("requirements", []):
                        self.requirements.append(
                            Requirement(req_data, section["section"])
                        )
        self._loaded = True

    def get_summary(self) -> dict[str, Any]:
        if not self._loaded:
            self.load_all()
        total = len(self.requirements)
        tested = sum(1 for r in self.requirements if r.is_tested())
        missing = sum(1 for r in self.requirements if r.status == "missing")
        partial = sum(1 for r in self.requirements if r.status == "partial")
        stale = sum(len(r.stale_tests()) for r in self.requirements)
        return {
            "total": total,
            "tested": tested,
            "missing": missing,
            "partial": partial,
            "stale_test_refs": stale,
            "pct": (tested / total * 100) if total > 0 else 0,
        }

    def get_missing(self) -> list[Requirement]:
        if not self._loaded:
            self.load_all()
        return [r for r in self.requirements if r.status == "missing"]
