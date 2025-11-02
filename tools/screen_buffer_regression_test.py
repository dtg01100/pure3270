#!/usr/bin/env python3
"""
Screen Buffer Regression Test Tool

Usage:
  screen_buffer_regression_test.py generate <output_dir> <count>
  screen_buffer_regression_test.py run <output_dir>
"""
import json
import os
import random
import sys
from pathlib import Path
from typing import List


def print_usage() -> None:
    print(__doc__)


def generate(output_dir: str, count: int) -> int:
    """Generate <count> screen buffer regression test cases in <output_dir>."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    for i in range(count):
        case = {
            "case": i,
            "rows": 24,
            "cols": 80,
            "fields": [
                {
                    "start": [random.randint(0, 23), random.randint(0, 79)],
                    "end": [random.randint(0, 23), random.randint(0, 79)],
                    "protected": bool(random.getrandbits(1)),
                    "numeric": bool(random.getrandbits(1)),
                    "content": "".join(
                        random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=8)
                    ),
                }
                for _ in range(random.randint(1, 5))
            ],
        }
        fname = Path(output_dir) / f"screen_case_{i}.json"
        with open(fname, "w") as f:
            json.dump(case, f, indent=2)
    print(f"Generated {count} screen buffer cases in {output_dir}")
    return 0


def validate_case(case: dict[str, object]) -> bool:
    """Validate a single screen buffer case."""
    # Validate structure first
    required_keys = {"case", "rows", "cols", "fields"}
    if not required_keys.issubset(case.keys()):
        return False
    if not isinstance(case["fields"], list):
        return False
    for field in case["fields"]:
        if not all(
            k in field for k in ["start", "end", "protected", "numeric", "content"]
        ):
            return False

    # Now exercise Pure3270's screen buffer logic
    try:
        from pure3270.emulation.ebcdic import EBCDICCodec
        from pure3270.emulation.screen_buffer import Field, ScreenBuffer

        codec = EBCDICCodec()

        def safe_int(val: object) -> int:
            if isinstance(val, int):
                return val
            if isinstance(val, str):
                return int(val)
            raise TypeError(f"Cannot convert {val!r} to int")

        rows = safe_int(case["rows"])
        cols = safe_int(case["cols"])
        screen = ScreenBuffer(rows=rows, cols=cols)
        for f in case["fields"]:
            start = tuple(f["start"])
            end = tuple(f["end"])
            protected = f["protected"]
            numeric = f["numeric"]
            # Encode content to EBCDIC bytes
            ebcdic_bytes, _ = codec.encode(f["content"])
            field_obj = Field(
                start=start,
                end=end,
                protected=protected,
                numeric=numeric,
                content=ebcdic_bytes,
            )
            screen.fields.append(field_obj)
        # Optionally, exercise more buffer logic here (e.g., get_field_content, ascii_buffer)
        _ = [screen.get_field_content(i) for i in range(len(screen.fields))]
        _ = screen.ascii_buffer
    except Exception as e:
        print(f"Pure3270 error in case {case['case']}: {e}")
        return False
    return True


def run(output_dir: str) -> int:
    """Validate all screen buffer regression test cases in <output_dir>."""
    files = list(Path(output_dir).glob("screen_case_*.json"))
    if not files:
        print(f"No screen buffer cases found in {output_dir}")
        return 1
    valid = 0
    for fpath in files:
        try:
            with open(fpath, "r") as f:
                case = json.load(f)
            if validate_case(case):
                print(f"Validated {fpath.name}")
                valid += 1
            else:
                print(f"Invalid case: {fpath.name}")
        except Exception as e:
            print(f"Error reading {fpath.name}: {e}")
    print(f"Screen buffer regression test passed for {valid}/{len(files)} cases.")
    return 0 if valid == len(files) else 1


def main() -> None:
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "generate" and len(sys.argv) == 4:
        try:
            count = int(sys.argv[3])
        except ValueError:
            print("Count must be an integer.")
            sys.exit(1)
        sys.exit(generate(sys.argv[2], count))
    elif cmd == "run" and len(sys.argv) == 3:
        sys.exit(run(sys.argv[2]))
    else:
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
