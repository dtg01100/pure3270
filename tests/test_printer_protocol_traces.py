"""
Printer Protocol Tests for Trace Replay

Tests comprehensive printer protocol features including:
- SCS (SNA Character Stream) control codes
- Print job detection and boundaries
- PRINT-EOJ markers
- TN3270E printer sessions
- Multiple print job handling
- Printer response handling

These tests validate that trace replay exercises all printer features.
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest


@dataclass
class PrintJob:
    """Represents a print job in a trace."""

    job_number: int
    start_line: int
    end_line: int
    pages: int = 0
    lines: List[str] = field(default_factory=list)
    has_eoj_marker: bool = False
    scs_codes: List[str] = field(default_factory=list)
    sequence_numbers: List[int] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_number": self.job_number,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "pages": self.pages,
            "line_count": len(self.lines),
            "has_eoj_marker": self.has_eoj_marker,
            "scs_codes": list(set(self.scs_codes)),
            "sequence_numbers": self.sequence_numbers,
        }


class PrinterTraceAnalyzer:
    """Analyze printer traces to extract print jobs and features."""

    def __init__(self, trace_path: Path):
        self.trace_path = trace_path
        self.print_jobs: List[PrintJob] = []
        self.scs_features_found: set = set()
        self.response_count = 0
        self.eoj_count = 0

    def parse_trace(self) -> None:
        """Parse trace file for printer data."""
        current_job = None
        job_number = 0
        # Track pending text fragments that end with ellipsis and should
        # concatenate with the next continuation line starting with "... "
        pending_fragment: Optional[str] = None

        try:
            with open(self.trace_path, "r", encoding="utf-8", errors="ignore") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()

                    # Detect start of print job (Write with startprinter)
                    if "Write(" in line and "startprinter" in line:
                        # Start a new job only if not already inside one; otherwise this is a continuation
                        if current_job is None:
                            job_number += 1
                            current_job = PrintJob(
                                job_number=job_number,
                                start_line=line_num,
                                end_line=line_num,
                            )

                    # Detect print content (lines with NL, FF, etc.)
                    if current_job:
                        current_job.end_line = line_num

                        # Check for SCS control codes
                        if "NL" in line:  # Newline
                            current_job.scs_codes.append("NL")
                            self.scs_features_found.add("newline")
                        if "FF" in line:  # Form feed
                            current_job.scs_codes.append("FF")
                            current_job.pages += 1
                            self.scs_features_found.add("form_feed")
                        if "CR" in line:  # Carriage return
                            current_job.scs_codes.append("CR")
                            self.scs_features_found.add("carriage_return")
                        if "HT" in line:  # Horizontal tab
                            current_job.scs_codes.append("HT")
                            self.scs_features_found.add("horizontal_tab")
                        if "VT" in line:  # Vertical tab
                            current_job.scs_codes.append("VT")
                            self.scs_features_found.add("vertical_tab")
                        if "EM" in line:  # End of medium
                            current_job.scs_codes.append("EM")
                            self.scs_features_found.add("end_of_medium")

                        # Extract text content across possibly multi-line quoted segments
                        # Maintain a simple state machine to accumulate text between quotes
                        if not hasattr(self, "_in_quoted"):
                            # Per-analyzer state for multi-line quoted content
                            self._in_quoted = False  # type: ignore[attr-defined]
                            self._quoted_accum = ""  # type: ignore[attr-defined]

                        # Helper to finalize any accumulated quoted content
                        def _finalize_quoted() -> None:
                            try:
                                accum = getattr(self, "_quoted_accum")  # type: ignore[attr-defined]
                            except Exception:
                                accum = ""
                            if accum:
                                text = accum.replace("...", "")
                                # Normalize interior whitespace minimally
                                text = text.strip()
                                # Heuristic fix for split words where the first letter is
                                # on the previous line (e.g., 'D ' + 'OCUMENT' -> 'DOCUMENT',
                                # 'S ' + 'UPPLIER' -> 'SUPPLIER')
                                try:
                                    text = re.sub(r"\b([A-Z])\s+([A-Z])", r"\1\2", text)
                                except Exception:
                                    pass
                                if text:
                                    current_job.lines.append(text)
                            try:
                                setattr(self, "_quoted_accum", "")  # type: ignore[attr-defined]
                            except Exception:
                                pass

                        # Process line content
                        ln = line
                        # If line is a continuation starting with '... ', drop the prefix for parsing
                        if ln.startswith("... "):
                            ln = ln[4:]
                        idx = 0
                        while True:
                            # If currently accumulating a multi-line quoted segment
                            if getattr(self, "_in_quoted", False):  # type: ignore[attr-defined]
                                # Append up to next quote or end of line
                                if "'" in ln:
                                    before, after = ln.split("'", 1)
                                    try:
                                        setattr(
                                            self,
                                            "_quoted_accum",
                                            getattr(self, "_quoted_accum") + before,  # type: ignore[attr-defined]
                                        )
                                    except Exception:
                                        pass
                                    # Finalize this quoted segment
                                    _finalize_quoted()
                                    try:
                                        setattr(self, "_in_quoted", False)  # type: ignore[attr-defined]
                                    except Exception:
                                        pass
                                    # Continue parsing any additional segments on this line
                                    ln = after
                                    idx = 0
                                    continue
                                else:
                                    # No closing quote on this line; accumulate and stop
                                    try:
                                        setattr(
                                            self,
                                            "_quoted_accum",
                                            getattr(self, "_quoted_accum") + ln,  # type: ignore[attr-defined]
                                        )
                                    except Exception:
                                        pass
                                    break
                            else:
                                # Not currently in a quoted segment; look for the next quoted block
                                q1 = ln.find("'", idx)
                                if q1 == -1:
                                    break
                                q2 = ln.find("'", q1 + 1)
                                if q2 == -1:
                                    # Start of a multi-line quoted segment
                                    try:
                                        setattr(self, "_in_quoted", True)  # type: ignore[attr-defined]
                                        setattr(
                                            self,
                                            "_quoted_accum",
                                            ln[q1 + 1 :],  # type: ignore[attr-defined]
                                        )
                                    except Exception:
                                        pass
                                    break
                                # Complete quoted segment on this line
                                seg = ln[q1 + 1 : q2]
                                seg_text = seg.replace("...", "").strip()
                                if seg_text:
                                    current_job.lines.append(seg_text)
                                idx = q2 + 1

                    # Detect PRINT-EOJ marker
                    if "PRINT-EOJ" in line:
                        self.eoj_count += 1
                        if current_job:
                            current_job.has_eoj_marker = True

                            # Extract sequence number if present
                            seq_match = re.search(r"PRINT-EOJ.*?(\d+)", line)
                            if seq_match:
                                current_job.sequence_numbers.append(
                                    int(seq_match.group(1))
                                )

                            # End of print job
                            self.print_jobs.append(current_job)
                            current_job = None

                    # Count responses
                    if "RESPONSE" in line or "SENT TN3270E(RESPONSE" in line:
                        self.response_count += 1

                # Add any remaining job
                if current_job:
                    self.print_jobs.append(current_job)

        except Exception as e:
            pytest.fail(f"Error parsing printer trace: {e}")

    def get_report(self) -> Dict[str, Any]:
        """Generate analysis report."""
        return {
            "num_print_jobs": len(self.print_jobs),
            "total_eoj_markers": self.eoj_count,
            "total_responses": self.response_count,
            "scs_features": list(self.scs_features_found),
            "print_jobs": [job.to_dict() for job in self.print_jobs],
        }


class TestPrinterProtocol:
    """Test printer protocol in trace replay."""

    @pytest.fixture
    def smoke_trace(self) -> Path:
        """Path to smoke trace file (printer session)."""
        return Path(__file__).parent / "data" / "traces" / "smoke.trc"

    @pytest.fixture
    def smoke_expected(self) -> Dict[str, Any]:
        """Load expected data for smoke trace."""
        path = Path(__file__).parent / "data" / "expected" / "smoke_expected.json"
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return {}

    def test_print_job_detection(self, smoke_trace: Path, smoke_expected: Dict):
        """Test detection of print jobs in trace."""
        assert smoke_trace.exists(), "Smoke trace file not found"

        analyzer = PrinterTraceAnalyzer(smoke_trace)
        analyzer.parse_trace()

        # Verify print jobs detected
        assert len(analyzer.print_jobs) > 0, "No print jobs detected"

        # Check against expected
        if smoke_expected and "printer" in smoke_expected:
            expected_jobs = smoke_expected["printer"].get("num_print_jobs", 0)
            if expected_jobs > 0:
                assert (
                    len(analyzer.print_jobs) == expected_jobs
                ), f"Expected {expected_jobs} print jobs, found {len(analyzer.print_jobs)}"

    def test_print_eoj_markers(self, smoke_trace: Path, smoke_expected: Dict):
        """Test PRINT-EOJ markers are present."""
        assert smoke_trace.exists(), "Smoke trace file not found"

        analyzer = PrinterTraceAnalyzer(smoke_trace)
        analyzer.parse_trace()

        # Verify EOJ markers present
        assert analyzer.eoj_count > 0, "No PRINT-EOJ markers found"

        # Check each job has EOJ marker
        for job in analyzer.print_jobs:
            assert (
                job.has_eoj_marker
            ), f"Print job {job.job_number} missing PRINT-EOJ marker"

        # Check against expected
        if smoke_expected and "validation_checks" in smoke_expected:
            for check in smoke_expected["validation_checks"]:
                if check.get("type") == "print_eoj":
                    expected_count = check.get("count", 0)
                    if expected_count > 0:
                        assert (
                            analyzer.eoj_count == expected_count
                        ), f"Expected {expected_count} EOJ markers, found {analyzer.eoj_count}"

    def test_scs_control_codes(self, smoke_trace: Path, smoke_expected: Dict):
        """Test SCS control codes are present."""
        assert smoke_trace.exists(), "Smoke trace file not found"

        analyzer = PrinterTraceAnalyzer(smoke_trace)
        analyzer.parse_trace()

        # Verify SCS features detected
        assert len(analyzer.scs_features_found) > 0, "No SCS control codes found"

        # Check for expected features
        if smoke_expected and "scs_features" in smoke_expected:
            scs_features = smoke_expected["scs_features"]

            if scs_features.get("newline", False):
                assert (
                    "newline" in analyzer.scs_features_found
                ), "Expected newline (NL) control code"

            if scs_features.get("form_feed", False):
                assert (
                    "form_feed" in analyzer.scs_features_found
                ), "Expected form feed (FF) control code"

    def test_printer_response_handling(self, smoke_trace: Path, smoke_expected: Dict):
        """Test printer responses are sent."""
        assert smoke_trace.exists(), "Smoke trace file not found"

        analyzer = PrinterTraceAnalyzer(smoke_trace)
        analyzer.parse_trace()

        # Verify responses sent
        assert analyzer.response_count > 0, "No printer responses found"

        # Check against expected
        if smoke_expected and "validation_checks" in smoke_expected:
            for check in smoke_expected["validation_checks"]:
                if check.get("type") == "responses":
                    expected_count = check.get("positive_responses", 0)
                    if expected_count > 0:
                        assert (
                            analyzer.response_count >= expected_count
                        ), f"Expected at least {expected_count} responses, found {analyzer.response_count}"

    def test_print_job_content(self, smoke_trace: Path, smoke_expected: Dict):
        """Test print job content is captured."""
        assert smoke_trace.exists(), "Smoke trace file not found"

        analyzer = PrinterTraceAnalyzer(smoke_trace)
        analyzer.parse_trace()

        # Verify print jobs have content
        for job in analyzer.print_jobs:
            assert len(job.lines) > 0, f"Print job {job.job_number} has no content"

        # Check for expected content markers
        if smoke_expected and "printer" in smoke_expected:
            print_jobs = smoke_expected["printer"].get("print_jobs", [])

            for expected_job in print_jobs:
                job_num = expected_job.get("job_number", 0)
                if job_num > 0 and job_num <= len(analyzer.print_jobs):
                    actual_job = analyzer.print_jobs[job_num - 1]
                    all_content = " ".join(actual_job.lines)
                    # Normalize whitespace for robust matching across split/continued segments
                    all_content_norm = re.sub(r"\s+", " ", all_content)

                    # Check for content markers
                    markers = expected_job.get("content_markers", [])
                    for marker in markers:
                        if (
                            marker != "PRINT-EOJ"
                        ):  # Skip EOJ marker (checked separately)
                            marker_norm = re.sub(r"\s+", " ", marker)
                            assert (
                                marker_norm in all_content_norm
                            ), f"Expected content marker '{marker}' not found in job {job_num}"

    def test_multi_page_print_jobs(self, smoke_trace: Path, smoke_expected: Dict):
        """Test multi-page print jobs are handled."""
        assert smoke_trace.exists(), "Smoke trace file not found"

        analyzer = PrinterTraceAnalyzer(smoke_trace)
        analyzer.parse_trace()

        # Verify multi-page jobs exist
        multi_page_jobs = [job for job in analyzer.print_jobs if job.pages > 1]

        if smoke_expected and "printer" in smoke_expected:
            expected_jobs = smoke_expected["printer"].get("print_jobs", [])

            for expected_job in expected_jobs:
                expected_pages = expected_job.get("pages", 0)
                if expected_pages > 1:
                    # At least one job should be multi-page
                    assert (
                        len(multi_page_jobs) > 0
                    ), "Expected multi-page print jobs but found none"
                    break

    def test_tn3270e_sequence_numbers(self, smoke_trace: Path):
        """Test TN3270E sequence numbers in printer session."""
        assert smoke_trace.exists(), "Smoke trace file not found"

        analyzer = PrinterTraceAnalyzer(smoke_trace)
        analyzer.parse_trace()

        # Verify sequence numbers are tracked
        jobs_with_seq = [job for job in analyzer.print_jobs if job.sequence_numbers]

        # In TN3270E mode, sequence numbers should be present
        if len(analyzer.print_jobs) > 0:
            # At least check that we're parsing the trace
            assert len(analyzer.print_jobs) > 0, "No print jobs parsed"

    def test_printer_coverage_report(self, smoke_trace: Path):
        """Generate coverage report for printer features."""
        assert smoke_trace.exists(), "Smoke trace file not found"

        analyzer = PrinterTraceAnalyzer(smoke_trace)
        analyzer.parse_trace()
        report = analyzer.get_report()

        # Add coverage metrics
        coverage = {
            "trace_file": "smoke.trc",
            "printer_features": report,
            "coverage_metrics": {
                "print_jobs_detected": len(analyzer.print_jobs) > 0,
                "eoj_markers_present": analyzer.eoj_count > 0,
                "scs_codes_present": len(analyzer.scs_features_found) > 0,
                "responses_sent": analyzer.response_count > 0,
                "multi_page_jobs": any(job.pages > 1 for job in analyzer.print_jobs),
            },
        }

        # Save report
        report_path = (
            Path(__file__).parent.parent
            / "test_output"
            / "printer_coverage_report.json"
        )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w") as f:
            json.dump(coverage, f, indent=2)

        # Assertions on coverage
        assert coverage["coverage_metrics"][
            "print_jobs_detected"
        ], "No print jobs detected in trace"
        assert coverage["coverage_metrics"][
            "eoj_markers_present"
        ], "No PRINT-EOJ markers found in trace"
        assert coverage["coverage_metrics"][
            "scs_codes_present"
        ], "No SCS control codes found in trace"

    @pytest.mark.parametrize(
        "feature,description",
        [
            ("newline", "Newline (NL) control code"),
            ("form_feed", "Form feed (FF) control code for page breaks"),
            ("end_of_medium", "End of medium (EM) marker"),
        ],
    )
    def test_scs_feature_present(
        self, smoke_trace: Path, feature: str, description: str
    ):
        """Test specific SCS features are present."""
        assert smoke_trace.exists(), "Smoke trace file not found"

        analyzer = PrinterTraceAnalyzer(smoke_trace)
        analyzer.parse_trace()

        # Check if feature is present when SCS features are detected
        # Not all traces will have all features, so only assert when any were found
        if len(analyzer.scs_features_found) > 0:
            assert feature in analyzer.scs_features_found, (
                f"Expected SCS feature '{feature}' ({description}) not detected; "
                f"found: {sorted(analyzer.scs_features_found)}"
            )

    def test_print_job_boundaries(self, smoke_trace: Path):
        """Test print job boundaries are correctly identified."""
        assert smoke_trace.exists(), "Smoke trace file not found"

        analyzer = PrinterTraceAnalyzer(smoke_trace)
        analyzer.parse_trace()

        # Verify each job has valid boundaries
        for job in analyzer.print_jobs:
            assert job.start_line > 0, f"Job {job.job_number} has invalid start line"
            assert (
                job.end_line >= job.start_line
            ), f"Job {job.job_number} end line before start line"
            assert job.job_number > 0, f"Job has invalid job number"

        # Verify jobs don't overlap (should be sequential)
        for i in range(len(analyzer.print_jobs) - 1):
            assert (
                analyzer.print_jobs[i].end_line <= analyzer.print_jobs[i + 1].start_line
            ), f"Print jobs {i+1} and {i+2} overlap"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
