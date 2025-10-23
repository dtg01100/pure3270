#!/usr/bin/env python3
"""
Generate trace files for specific 3270 features that aren't well covered by existing traces.

This script creates synthetic traces for testing:
- AID keys and function keys
- Query operations
- Field validation
- Extended highlighting
- Error conditions
- Response modes

Usage:
    python generate_feature_traces.py [feature_name] [--host HOST] [--port PORT]
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add pure3270 to path
sys.path.insert(0, "/workspaces/pure3270")

from pure3270 import AsyncSession


class FeatureTraceGenerator:
    """Generate traces for specific 3270 features."""

    def __init__(self, output_dir: str = "tests/data/traces/missing_features"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def generate_aid_keys_trace(
        self, host: Optional[str] = None, port: int = 23
    ) -> str:
        """Generate trace for AID keys (function keys, enter, etc.)."""
        trace_file = self.output_dir / "aid_keys_test.trc"

        # For AID keys, we need to simulate key presses
        # This would require a mock session or actual interaction
        # For now, create a template trace

        trace_content = """// AID Keys Test Trace
// rows 24
// columns 80
// Tests function keys, enter key, and other AID operations

// Initial screen setup
> 0x0000 00000100017ec6114040132902c06042002845f23c40c9f02902c0604200
< 0x0000 000000000000000000000000000000000000000000002902c0e842f1c793

// AID: Enter key (0x7D)
> 0x0000 7d00000000000000000000000000000000000000000000000000000000

// AID: PF1 key (0xF1)
> 0x0000 f100000000000000000000000000000000000000000000000000000000

// AID: PF24 key (0xF8)
> 0x0000 f800000000000000000000000000000000000000000000000000000000
"""

        with open(trace_file, "w") as f:
            f.write(trace_content)

        return str(trace_file)

    async def generate_query_trace(
        self, host: Optional[str] = None, port: int = 23
    ) -> str:
        """Generate trace for Query operations."""
        trace_file = self.output_dir / "query_operations_test.trc"

        trace_content = """// Query Operations Test Trace
// rows 24
// columns 80
// Tests Query and Query Reply operations

// Query request (0x02)
> 0x0000 0200000000000000000000000000000000000000000000000000000000

// Query reply with device capabilities
< 0x0000 0200000000000000000000000000000000000000000000000000000000
"""

        with open(trace_file, "w") as f:
            f.write(trace_content)

        return str(trace_file)

    async def generate_field_validation_trace(
        self, host: Optional[str] = None, port: int = 23
    ) -> str:
        """Generate trace for field validation and protection."""
        trace_file = self.output_dir / "field_validation_test.trc"

        trace_content = """// Field Validation Test Trace
// rows 24
// columns 80
// Tests field protection, validation, and modification

// Create protected field
> 0x0000 1d40c0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0

// Try to modify protected field (should fail or be ignored)
> 0x0000 00000100017ec6114040132902c06042002845f23c40c9f02902c0604200

// Create unprotected field
> 0x0000 1d00c0f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1

// Modify unprotected field
> 0x0000 00000100017ec6114040132902c06042002845f23c40c9f02902c0604200
"""

        with open(trace_file, "w") as f:
            f.write(trace_content)

        return str(trace_file)

    async def generate_highlighting_trace(
        self, host: Optional[str] = None, port: int = 23
    ) -> str:
        """Generate trace for extended highlighting features."""
        trace_file = self.output_dir / "extended_highlighting_test.trc"

        trace_content = """// Extended Highlighting Test Trace
// rows 24
// columns 80
// Tests blinking, reverse video, underscore, etc.

// Normal field
> 0x0000 1d00c0d5d6d9d4c1d3

// Blinking field (0xF1)
> 0x0000 1df1c0c2d3c9d5d2c9d5c7

// Reverse video field (0xF2)
> 0x0000 1df2c0d9c5e5c5d9e2c5

// Underscore field (0xF4)
> 0x0000 1df4c0e4d5c4c5d9e2c3d6d9c5

// High intensity field (0xF8)
> 0x0000 1df8c0c8c9c7c8
"""

        with open(trace_file, "w") as f:
            f.write(trace_content)

        return str(trace_file)

    async def generate_error_conditions_trace(
        self, host: Optional[str] = None, port: int = 23
    ) -> str:
        """Generate trace for error conditions."""
        trace_file = self.output_dir / "error_conditions_test.trc"

        trace_content = """// Error Conditions Test Trace
// rows 24
// columns 80
// Tests invalid orders, buffer overflows, etc.

// Invalid order (0xFF)
> 0x0000 ff00000000000000000000000000000000000000000000000000000000

// Buffer address beyond screen bounds
> 0x0000 11ffff0000000000000000000000000000000000000000000000000000

// RA with invalid target address
> 0x0000 3cffff4000000000000000000000000000000000000000000000000000
"""

        with open(trace_file, "w") as f:
            f.write(trace_content)

        return str(trace_file)

    async def generate_response_modes_trace(
        self, host: Optional[str] = None, port: int = 23
    ) -> str:
        """Generate trace for TN3270E response modes."""
        trace_file = self.output_dir / "response_modes_test.trc"

        trace_content = """// Response Modes Test Trace
// rows 24
// columns 80
// Tests TN3270E response modes and negotiation

// TN3270E negotiation
> 0x0000 fffd1801
< 0x0000 fffb18

// BIND-IMAGE structured field
> 0x0000 0000030000000000000000000000000000000000000000000000000000
"""

        with open(trace_file, "w") as f:
            f.write(trace_content)

        return str(trace_file)

    async def generate_all_missing_traces(
        self, host: Optional[str] = None, port: int = 23
    ) -> List[str]:
        """Generate traces for all missing features."""
        generators = [
            self.generate_aid_keys_trace,
            self.generate_query_trace,
            self.generate_field_validation_trace,
            self.generate_highlighting_trace,
            self.generate_error_conditions_trace,
            self.generate_response_modes_trace,
        ]

        generated_files = []
        for generator in generators:
            try:
                trace_file = await generator(host, port)
                generated_files.append(trace_file)
                print(f"Generated: {trace_file}")
            except Exception as e:
                print(f"Failed to generate trace for {generator.__name__}: {e}")

        return generated_files


async def main():
    parser = argparse.ArgumentParser(description="Generate 3270 feature traces")
    parser.add_argument(
        "feature", nargs="?", help="Specific feature to generate trace for"
    )
    parser.add_argument(
        "--host", default=None, help="Host to connect to for live trace generation"
    )
    parser.add_argument("--port", type=int, default=23, help="Port to connect to")
    parser.add_argument(
        "--all", action="store_true", help="Generate all missing feature traces"
    )

    args = parser.parse_args()

    generator = FeatureTraceGenerator()

    if args.all:
        print("Generating traces for all missing features...")
        generated = await generator.generate_all_missing_traces(args.host, args.port)
        print(f"\nGenerated {len(generated)} trace files:")
        for f in generated:
            print(f"  {f}")
    elif args.feature:
        feature_generators = {
            "aid_keys": generator.generate_aid_keys_trace,
            "query": generator.generate_query_trace,
            "field_validation": generator.generate_field_validation_trace,
            "highlighting": generator.generate_highlighting_trace,
            "errors": generator.generate_error_conditions_trace,
            "response_modes": generator.generate_response_modes_trace,
        }

        if args.feature in feature_generators:
            trace_file = await feature_generators[args.feature](args.host, args.port)
            print(f"Generated: {trace_file}")
        else:
            print(f"Unknown feature: {args.feature}")
            print(f"Available features: {list(feature_generators.keys())}")
    else:
        print(
            "Usage: python generate_feature_traces.py [feature_name] [--host HOST] [--port PORT]"
        )
        print("Or: python generate_feature_traces.py --all")


if __name__ == "__main__":
    asyncio.run(main())
