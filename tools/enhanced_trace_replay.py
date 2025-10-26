#!/usr/bin/env python3
"""
Enhanced Trace Replay Validation Tool

This tool provides comprehensive validation of trace files including:
- Data stream parsing validation
- Screen state correctness checking
- Field attribute validation
- AID code processing
- Error condition handling
- Protocol feature coverage reporting

Usage:
  enhanced_trace_replay.py <trace_file> [--expected <expected_file>]
"""
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Patch-friendly imports: expose classes at module level so tests can monkeypatch
# Define names with flexible typing first to avoid type reassignment issues
DataStreamParser: Any = None
ScreenBuffer: Any = None
_IMPORT_ERROR: Optional[Exception] = None
try:  # Defer import errors to runtime checks in replay_and_validate
    from pure3270.emulation.screen_buffer import ScreenBuffer as _SB
    from pure3270.protocol.data_stream import DataStreamParser as _DSP

    ScreenBuffer = _SB
    DataStreamParser = _DSP
except Exception as _e:  # pragma: no cover - captured and reported at runtime
    _IMPORT_ERROR = _e


@dataclass
class TraceFeatures:
    """Track which protocol features are present in a trace."""

    has_telnet_negotiation: bool = False
    has_tn3270e: bool = False
    has_bind_image: bool = False
    has_printer_data: bool = False
    has_extended_attributes: bool = False
    has_structured_fields: bool = False
    has_aid_codes: bool = False
    has_error_conditions: bool = False

    commands_seen: List[str] = field(default_factory=list)
    orders_seen: List[str] = field(default_factory=list)
    aids_seen: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "telnet_negotiation": self.has_telnet_negotiation,
            "tn3270e": self.has_tn3270e,
            "bind_image": self.has_bind_image,
            "printer": self.has_printer_data,
            "extended_attributes": self.has_extended_attributes,
            "structured_fields": self.has_structured_fields,
            "aid_codes": self.has_aid_codes,
            "error_conditions": self.has_error_conditions,
            "commands": list(set(self.commands_seen)),
            "orders": list(set(self.orders_seen)),
            "aids": list(set(self.aids_seen)),
        }


@dataclass
class ValidationResult:
    """Results of trace validation."""

    success: bool
    records_parsed: int
    records_failed: int
    features: TraceFeatures
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    screen_validation: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "records_parsed": self.records_parsed,
            "records_failed": self.records_failed,
            "features": self.features.to_dict(),
            "errors": self.errors,
            "warnings": self.warnings,
            "screen_validation": self.screen_validation,
        }


class TraceAnalyzer:
    """Analyze trace files to identify protocol features."""

    def __init__(self, trace_path: str):
        self.trace_path = Path(trace_path)
        self.features = TraceFeatures()
        self.lines: List[str] = []

    def load_trace(self) -> bool:
        """Load trace file."""
        try:
            with open(self.trace_path, "r", encoding="utf-8", errors="ignore") as f:
                self.lines = f.readlines()
            return True
        except Exception as e:
            print(f"Error loading trace: {e}")
            return False

    def analyze_features(self) -> TraceFeatures:
        """Analyze trace to identify features."""
        for line in self.lines:
            line = line.strip()

            # Check for telnet negotiation
            if any(
                x in line
                for x in ["DO TERMINAL", "WILL BINARY", "RCVD DO", "SENT WILL"]
            ):
                self.features.has_telnet_negotiation = True

            # Check for TN3270E
            if "TN3270E" in line or "DEVICE-TYPE" in line or "FUNCTIONS" in line:
                self.features.has_tn3270e = True

            # Check for BIND
            if "BIND-IMAGE" in line or "BIND" in line.upper():
                self.features.has_bind_image = True

            # Check for printer
            if any(x in line for x in ["PRINT-EOJ", "startprinter", "printer", "SCS"]):
                self.features.has_printer_data = True

            # Check for extended attributes
            if any(
                x in line for x in ["StartFieldExtended", "foreground", "highlighting"]
            ):
                self.features.has_extended_attributes = True

            # Check for structured fields
            if "Query" in line or "Partition" in line:
                self.features.has_structured_fields = True

            # Check for commands
            if "Write(" in line or "EraseWrite" in line:
                match = re.search(r"(Write|EraseWrite|EraseWriteAlternate)\(", line)
                if match:
                    self.features.commands_seen.append(match.group(1))

            # Check for AID codes
            if any(x in line for x in ["Enter", "Clear", "PF", "PA"]):
                self.features.has_aid_codes = True

            # Check for error conditions
            if any(x in line.lower() for x in ["error", "invalid", "short", "truncat"]):
                self.features.has_error_conditions = True

        return self.features


class EnhancedTraceReplay:
    """Enhanced trace replay with comprehensive validation."""

    def __init__(self, trace_path: str, expected_path: Optional[str] = None):
        self.trace_path = Path(trace_path)
        self.expected_path = Path(expected_path) if expected_path else None
        self.expected_data: Optional[Dict[str, Any]] = None
        self.result = ValidationResult(
            success=False, records_parsed=0, records_failed=0, features=TraceFeatures()
        )

    def load_expected(self) -> bool:
        """Load expected output file if available."""
        if not self.expected_path or not self.expected_path.exists():
            return False

        try:
            with open(self.expected_path, "r") as f:
                self.expected_data = json.load(f)
            return True
        except Exception as e:
            self.result.warnings.append(f"Could not load expected data: {e}")
            return False

    def parse_trace_records(self) -> List[bytes]:
        """Parse trace file into records."""
        records = []
        try:
            with open(self.trace_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    # Only process lines starting with < or >
                    if line.startswith("<") or line.startswith(">"):
                        # Format: < 0xOFFSET   HEXDATA
                        match = re.match(
                            r"[<>]\s+0x[0-9a-fA-F]+\s+([0-9a-fA-F]+)\s*$", line
                        )
                        if match:
                            hex_data = match.group(1)
                            try:
                                data = bytes.fromhex(hex_data)
                                records.append(data)
                            except Exception as e:
                                # Hex parsing failure is an error - data is corrupted
                                self.result.errors.append(
                                    f"Could not parse hex data: {e}"
                                )
                        else:
                            # Line starts with < or > but doesn't match expected format
                            # If it has "0x" it was supposed to be hex data - error
                            # Otherwise it's just a descriptive line - warning
                            if "0x" in line:
                                # Has offset marker but format is wrong - error
                                self.result.errors.append(
                                    f"Could not parse hex data: Invalid format in line: {line[:80]}"
                                )
                            else:
                                # Descriptive line, not hex data - skip with debug warning
                                self.result.warnings.append(
                                    f"Skipping non-hex line: {line[:80]}"
                                )
        except Exception as e:
            self.result.errors.append(f"Error parsing trace: {e}")

        return records

    def validate_screen_state(
        self, screen: Any, expected: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Validate screen state against expected output."""
        validation: Dict[str, Any] = {
            "validated": False,
            "matches_expected": None,
            "screen_rows": 0,
            "screen_cols": 0,
            "num_fields": 0,
            "field_details": [],
        }

        try:
            validation["screen_rows"] = screen.rows
            validation["screen_cols"] = screen.cols

            # Get fields
            fields = getattr(screen, "fields", [])
            validation["num_fields"] = len(fields)

            for idx, field in enumerate(fields):
                field_info = {
                    "index": idx,
                    "start": field.start if hasattr(field, "start") else None,
                    "end": field.end if hasattr(field, "end") else None,
                    "protected": (
                        field.protected if hasattr(field, "protected") else None
                    ),
                }

                # Try to get content
                try:
                    if hasattr(field, "get_content"):
                        field_info["content"] = field.get_content()
                    elif hasattr(field, "content"):
                        field_info["content"] = field.content
                except Exception:
                    field_info["content"] = None

                # Get attributes
                if hasattr(field, "intensified"):
                    field_info["intensified"] = field.intensified
                if hasattr(field, "hidden"):
                    field_info["hidden"] = field.hidden
                if hasattr(field, "numeric"):
                    field_info["numeric"] = field.numeric
                if hasattr(field, "modified"):
                    field_info["modified"] = field.modified

                validation["field_details"].append(field_info)

            validation["validated"] = True

            # Compare with expected if available
            if expected and "screen" in expected:
                exp_screen = expected["screen"]
                matches = True

                if exp_screen.get("rows") != validation["screen_rows"]:
                    matches = False
                if exp_screen.get("cols") != validation["screen_cols"]:
                    matches = False
                if exp_screen.get("num_fields") != validation["num_fields"]:
                    matches = False

                validation["matches_expected"] = matches

        except Exception as e:
            validation["error"] = str(e)

        return validation

    def replay_and_validate(self) -> ValidationResult:
        """Replay trace with comprehensive validation."""
        if not self.trace_path.exists():
            self.result.errors.append(f"Trace file not found: {self.trace_path}")
            return self.result

        print(f"Replaying trace: {self.trace_path.name}")

        # Analyze features in trace
        analyzer = TraceAnalyzer(str(self.trace_path))
        if analyzer.load_trace():
            self.result.features = analyzer.analyze_features()
            print(f"Features detected: {self.result.features.to_dict()}")

        # Load expected data if available
        self.load_expected()

        # Parse records
        records = self.parse_trace_records()
        if not records:
            self.result.errors.append("No valid records found in trace")
            return self.result

        print(f"Trace contains {len(records)} records")

        # Create screen and parser using patchable module-level references
        if ScreenBuffer is None or DataStreamParser is None:
            err_detail = str(_IMPORT_ERROR) if _IMPORT_ERROR else "Unknown import error"
            self.result.errors.append(f"Error importing Pure3270: {err_detail}")
            return self.result

        screen = ScreenBuffer(rows=24, cols=80)
        parser = DataStreamParser(screen)

        # Process each record
        for idx, record in enumerate(records):
            try:
                parser.parse(record)
                self.result.records_parsed += 1

                # Track orders and commands seen
                if hasattr(parser, "last_command"):
                    cmd = parser.last_command
                    if (
                        cmd
                        and isinstance(cmd, str)
                        and cmd not in self.result.features.commands_seen
                    ):
                        self.result.features.commands_seen.append(cmd)

                if hasattr(parser, "aid"):
                    aid = parser.aid
                    if aid and str(aid) not in self.result.features.aids_seen:
                        self.result.features.aids_seen.append(str(aid))

            except Exception as e:
                self.result.records_failed += 1
                error_msg = f"Record {idx+1}: {str(e)}"
                self.result.errors.append(error_msg)

        # Validate final screen state
        expected_screen = (
            self.expected_data.get("screen") if self.expected_data else None
        )
        self.result.screen_validation = self.validate_screen_state(
            screen, {"screen": expected_screen} if expected_screen else None
        )

        # Determine success
        # Success requires: some records parsed, no failures, and no errors
        # Warnings alone don't cause failure (they're informational)
        self.result.success = (
            self.result.records_parsed > 0
            and self.result.records_failed == 0
            and len(self.result.errors) == 0
        )

        return self.result


def print_report(result: ValidationResult) -> None:
    """Print validation report."""
    print("\n" + "=" * 80)
    print("TRACE REPLAY VALIDATION REPORT")
    print("=" * 80)

    print(f"\nStatus: {'SUCCESS' if result.success else 'FAILED'}")
    print(f"Records Parsed: {result.records_parsed}")
    print(f"Records Failed: {result.records_failed}")

    print("\n--- Protocol Features Detected ---")
    features_dict = result.features.to_dict()
    for key, value in features_dict.items():
        if isinstance(value, bool):
            print(f"  {key}: {'YES' if value else 'NO'}")
        elif isinstance(value, list) and value:
            print(f"  {key}: {', '.join(str(v) for v in value)}")

    if result.screen_validation:
        print("\n--- Screen Validation ---")
        sv = result.screen_validation
        print(f"  Validated: {sv.get('validated', False)}")
        print(f"  Screen Size: {sv.get('screen_rows')}x{sv.get('screen_cols')}")
        print(f"  Number of Fields: {sv.get('num_fields')}")

        if sv.get("matches_expected") is not None:
            print(f"  Matches Expected: {sv['matches_expected']}")

    if result.warnings:
        print("\n--- Warnings ---")
        for warning in result.warnings:
            print(f"  - {warning}")

    if result.errors:
        print("\n--- Errors ---")
        for error in result.errors:
            print(f"  - {error}")

    print("\n" + "=" * 80)


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Enhanced trace replay validation")
    parser.add_argument("trace_file", help="Trace file to replay")
    parser.add_argument("--expected", help="Expected output file (JSON)", default=None)
    parser.add_argument("--json", action="store_true", help="Output JSON report")

    args = parser.parse_args()

    replay = EnhancedTraceReplay(args.trace_file, args.expected)
    result = replay.replay_and_validate()

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print_report(result)

    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
