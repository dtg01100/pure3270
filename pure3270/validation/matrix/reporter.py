from pure3270.validation.matrix.checker import RfcMatrix
from pure3270.validation.report import SectionReport, ValidationReport


def build_rfc_report(matrix: RfcMatrix, report: ValidationReport) -> SectionReport:
    section = report.add_section("RFC Compliance Matrix")
    summary = matrix.get_summary()
    section.total = summary["total"]
    section.passed = summary["tested"]
    section.failed = (
        summary["missing"] + summary["partial"] + summary["stale_test_refs"]
    )

    for req in matrix.get_missing():
        section.details.append(f"  MISSING: §{req.section} - {req.text}")

    missing = matrix.get_missing()
    if missing:
        section.details.append(f"\n  {len(missing)} untested requirements:")
        for req in missing[:10]:
            section.details.append(
                f"    §{req.section} [{req.rfc_keyword}]: {req.text}"
            )

    return section
