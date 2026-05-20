from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class TestResult(Enum):
    PASS = "pass"  # nosec
    FAIL = "fail"
    SKIP = "skip"
    NOT_RUN = "not_run"


@dataclass
class SectionReport:
    name: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    details: list[str] = field(default_factory=list)

    def get_pct(self) -> float:
        return (self.passed / self.total * 100) if self.total > 0 else 0.0


@dataclass
class ValidationReport:
    sections: dict[str, SectionReport] = field(default_factory=dict)
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    ci_mode: bool = False
    exit_code: int = 0

    def add_section(self, name: str) -> SectionReport:
        section = SectionReport(name=name)
        self.sections[name] = section
        return section

    def summary(self) -> str:
        total = sum(s.total for s in self.sections.values())
        passed = sum(s.passed for s in self.sections.values())
        failed = sum(s.failed for s in self.sections.values())
        skipped = sum(s.skipped for s in self.sections.values())
        pct = (passed / total * 100) if total > 0 else 0
        lines = [
            "=" * 60,
            "  Pure3270 Validation Report",
            "=" * 60,
            "",
        ]
        for name, section in self.sections.items():
            lines.append(
                f"  {name}: {section.passed}/{section.total} ({section.get_pct():.0f}%)"
            )
        lines.append("")
        lines.append(
            f"  Total: {passed}/{total} passed ({pct:.0f}%), {failed} failed, {skipped} skipped"
        )
        if self.ci_mode:
            lines.append(f"  CI mode: {'PASS' if self.exit_code == 0 else 'FAIL'}")
        return "\n".join(lines)

    def to_json(self) -> dict[str, Any]:
        return {
            "sections": {
                name: {
                    "total": s.total,
                    "passed": s.passed,
                    "failed": s.failed,
                    "skipped": s.skipped,
                    "details": s.details,
                }
                for name, s in self.sections.items()
            },
            "ci_mode": self.ci_mode,
            "exit_code": self.exit_code,
        }
