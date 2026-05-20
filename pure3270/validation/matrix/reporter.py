from pure3270.validation.matrix.checker import RfcMatrix
from pure3270.validation.report import SectionReport, ValidationReport


def build_rfc_report(matrix: RfcMatrix, report: ValidationReport) -> SectionReport:
    section = report.add_section("RFC Compliance Matrix")
    summary = matrix.get_summary()
    section.total = summary["total"]
    section.passed = summary["tested"]
    section.failed = summary["missing"] + summary["partial"]

    for req in matrix.get_missing():
        section.details.append(f"  MISSING: §{req.section} - {req.text}")

    partial_requirements = [r for r in matrix.requirements if r.status == "partial"]
    if partial_requirements:
        section.details.append("")
        section.details.append(f"  PARTIAL ({len(partial_requirements)}):")
        for req in partial_requirements:
            stale = req.stale_tests()
            hint = f" ({len(stale)} stale test refs)" if stale else ""
            section.details.append(
                f"    §{req.section} [{req.rfc_keyword}]{hint}: {req.text}"
            )

    missing = matrix.get_missing()
    if missing:
        section.details.append("")
        section.details.append(f"  MISSING ({len(missing)} untested):")
        for req in missing[:10]:
            section.details.append(
                f"    §{req.section} [{req.rfc_keyword}]: {req.text}"
            )

    return section
