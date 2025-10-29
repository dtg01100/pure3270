#!/usr/bin/env python3
"""
Trace Replayer Module

Provides functionality to replay 3270 trace files and extract screen buffer state.
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List

from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.protocol.data_stream import DataStreamParser

logger = logging.getLogger(__name__)


class Replayer:
    """
    Replayer class for processing 3270 trace files.

    Parses trace files containing hex-encoded data streams and feeds them
    through a DataStreamParser to reconstruct screen buffer state.
    """

    def __init__(self) -> None:
        """Initialize the Replayer with default screen buffer and parser."""
        self.screen_buffer = ScreenBuffer(rows=24, cols=80)
        self.parser = DataStreamParser(self.screen_buffer)

    def replay(self, trace_file: str) -> Dict[str, Any]:
        """
        Replay a trace file and return the resulting screen state.

        Args:
            trace_file: Path to the trace file to replay

        Returns:
            Dict containing:
                - screen_buffer: The ScreenBuffer instance
                - ascii_screen: ASCII representation of the screen
                - fields: List of field information

        Raises:
            FileNotFoundError: If trace file doesn't exist
            ValueError: If trace parsing fails
        """
        trace_path = Path(trace_file)
        if not trace_path.exists():
            raise FileNotFoundError(f"Trace file not found: {trace_file}")

        logger.info(f"Replaying trace file: {trace_file}")

        # Parse the trace file into records
        records = self._parse_trace(trace_file)
        if not records:
            logger.warning("No valid records found in trace file")
            return self._get_screen_state()

        logger.info(f"Processing {len(records)} records from trace")

        # Process each record through the parser
        for idx, record in enumerate(records):
            try:
                logger.debug(
                    f"Processing record {idx + 1}/{len(records)} ({len(record)} bytes)"
                )
                self.parser.parse(record)
            except Exception as e:
                logger.warning(f"Failed to parse record {idx + 1}: {e}")
                continue

        return self._get_screen_state()

    def _parse_trace(self, trace_path: str) -> List[bytes]:
        """
        Parse a trace file into a list of byte records.

        Args:
            trace_path: Path to the trace file

        Returns:
            List of byte records extracted from the trace
        """
        records = []

        try:
            with open(trace_path, "r", encoding="utf-8", errors="replace") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    # Only process lines starting with < or > (direction indicators)
                    if line.startswith("<") or line.startswith(">"):
                        # Format: < 0xOFFSET   HEXDATA
                        # Extract hex data after the offset
                        match = re.match(
                            r"[<>]\s+0x[0-9a-fA-F]+\s+([0-9a-fA-F]+)", line
                        )
                        if match:
                            hex_data = match.group(1)
                            try:
                                data = bytes.fromhex(hex_data)
                                records.append(data)
                            except ValueError as e:
                                logger.warning(
                                    f"Could not parse hex data on line {line_num}: {e}"
                                )
                        else:
                            logger.debug(
                                f"Skipping unrecognized line format on line {line_num}: {line}"
                            )
        except Exception as e:
            raise ValueError(f"Error parsing trace file: {e}")

        return records

    def _get_screen_state(self) -> Dict[str, Any]:
        """
        Get the current screen state as a dictionary.

        Returns:
            Dict with screen_buffer, ascii_screen, and fields
        """
        # Get ASCII screen representation
        ascii_screen = self.screen_buffer.ascii_buffer

        # Get field information
        fields = []
        for field in self.screen_buffer.fields:
            field_info = {
                "start": field.start,
                "end": field.end,
                "protected": field.protected,
                "content": field.get_content() if hasattr(field, "get_content") else "",
            }
            fields.append(field_info)

        return {
            "screen_buffer": self.screen_buffer,
            "ascii_screen": ascii_screen,
            "fields": fields,
        }
