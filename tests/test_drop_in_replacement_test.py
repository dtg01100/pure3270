import base64
import json
import os
from typing import Any

from drop_in_replacement_test import compare_script_results


def write_results(path: str, payload: Any) -> None:
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)


def test_compare_script_results_with_padding_only(tmp_path: Any, capsys: Any) -> None:
    # Both sides produce the same raw bytes but different trimmed lengths
    raw = b"\x40" * 179  # EBCDIC space repeated
    raw_b64 = base64.b64encode(raw).decode("ascii")

    pure_results = {
        "steps": [
            {"action": "connect"},
            {"action": "get_screen", "screen_length": 179, "raw_base64": raw_b64},
        ],
        "screenshots": [
            {"step": 1, "action": "connect", "content": ""},
            {
                "step": 2,
                "action": "get_screen",
                "content": "",
                "length": 179,
                "raw_base64": raw_b64,
            },
        ],
        "final_screen": "",
        "raw_final_base64": raw_b64,
        "status": "completed",
    }

    p3270_results = {
        "steps": [
            {"action": "connect"},
            {"action": "get_screen", "screen_length": 23, "raw_base64": raw_b64},
        ],
        "screenshots": [
            {"step": 1, "action": "connect", "content": ""},
            {
                "step": 2,
                "action": "get_screen",
                "content": "",
                "length": 23,
                "raw_base64": raw_b64,
            },
        ],
        "final_screen": "",
        "raw_final_base64": raw_b64,
        "status": "completed",
    }

    pr = tmp_path / "pure3270_script_results.json"
    rr = tmp_path / "p3270_script_results.json"
    write_results(pr, pure_results)
    write_results(rr, p3270_results)

    # Run compare_script_results in working directory with these files
    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        # Verify raw_base64 values are present and match in our artificial data
        with open(pr, "r") as f:
            prj = json.load(f)
        with open(rr, "r") as f:
            rrj = json.load(f)
        pstep = prj.get("steps", [])[1]
        rstep = rrj.get("steps", [])[1]
        assert pstep.get("raw_base64") == rstep.get("raw_base64")
        ok = compare_script_results()
        assert ok is True
        # Now enable strict mode - we should get a failure (padding treated as bug)
        os.environ["PURE3270_FAIL_ON_PADDING"] = "1"
        try:
            ok2 = compare_script_results()
            assert ok2 is False
        finally:
            del os.environ["PURE3270_FAIL_ON_PADDING"]
        # Ensure it prints a MINOR differences message (non-fatal)
        captured = capsys.readouterr()
        assert (
            "MINOR DIFFERENCES" in captured.out
            or "NO DIFFERENCES FOUND" in captured.out
        )
    finally:
        os.chdir(cwd)


def test_compare_script_results_with_raw_difference(tmp_path: Any) -> None:
    # Both sides produce different raw bytes -> should fail
    raw_a = b"\x40" * 179
    raw_b = b"\x41" * 23
    b64a = base64.b64encode(raw_a).decode("ascii")
    b64b = base64.b64encode(raw_b).decode("ascii")

    pure_results = {
        "steps": [
            {"action": "connect"},
            {"action": "get_screen", "screen_length": 179, "raw_base64": b64a},
        ],
        "screenshots": [
            {"step": 1, "action": "connect", "content": ""},
            {
                "step": 2,
                "action": "get_screen",
                "content": "",
                "length": 179,
                "raw_base64": b64a,
            },
        ],
        "final_screen": "",
        "raw_final_base64": b64a,
        "status": "completed",
    }

    p3270_results = {
        "steps": [
            {"action": "connect"},
            {"action": "get_screen", "screen_length": 23, "raw_base64": b64b},
        ],
        "screenshots": [
            {"step": 1, "action": "connect", "content": ""},
            {
                "step": 2,
                "action": "get_screen",
                "content": "                       ",
                "length": 23,
                "raw_base64": b64b,
            },
        ],
        "final_screen": "",
        "raw_final_base64": b64b,
        "status": "completed",
    }

    pr = tmp_path / "pure3270_script_results.json"
    rr = tmp_path / "p3270_script_results.json"
    write_results(pr, pure_results)
    write_results(rr, p3270_results)

    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        ok = compare_script_results()
        assert ok is False
    finally:
        os.chdir(cwd)


def test_compare_script_results_writes_artifacts(tmp_path: Any) -> None:
    # Basic test: create synthetic results and ensure compare_script_results
    # copies expected artifacts into artifact_dir
    import shutil

    raw_a = b"\x40" * 10
    b64a = base64.b64encode(raw_a).decode("ascii")

    pure_results = {
        "steps": [
            {"action": "connect"},
            {"action": "get_screen", "screen_length": 10, "raw_base64": b64a},
        ],
        "screenshots": [
            {"step": 1, "action": "connect", "content": ""},
            {
                "step": 2,
                "action": "get_screen",
                "content": "",
                "length": 10,
                "raw_base64": b64a,
            },
        ],
        "final_screen": "",
        "raw_final_base64": b64a,
        "s3270_tracer_tracefile": "tracefile.trc",
        "status": "completed",
    }

    p3270_results = {
        "steps": [
            {"action": "connect"},
            {"action": "get_screen", "screen_length": 10, "raw_base64": b64a},
        ],
        "screenshots": [
            {"step": 1, "action": "connect", "content": ""},
            {
                "step": 2,
                "action": "get_screen",
                "content": "",
                "length": 10,
                "raw_base64": b64a,
            },
        ],
        "final_screen": "",
        "raw_final_base64": b64a,
        "status": "completed",
    }

    # Place result JSONs in tmp_path and a fake tracefile
    pr = tmp_path / "pure3270_script_results.json"
    rr = tmp_path / "p3270_script_results.json"
    pr.write_text(json.dumps(pure_results, indent=2))
    rr.write_text(json.dumps(p3270_results, indent=2))
    # create a fake tracefile
    (tmp_path / "tracefile.trc").write_text("trace data")

    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        dest_dir = tmp_path / "artifacts"
        ok = compare_script_results(artifact_dir=str(dest_dir))
        assert ok is True
        # artifacts should include the JSONs and the tracefile copy
        assert (dest_dir / "pure3270_script_results.json").exists()
        assert (dest_dir / "p3270_script_results.json").exists()
        assert (dest_dir / "tracefile.trc").exists()
    finally:
        os.chdir(cwd)


def test_compare_script_results_step_by_step_detects_diffs(tmp_path: Any) -> None:
    # Step-by-step difference detection with raw bytes different
    raw_a = b"A"
    raw_b = b"B"
    b64a = base64.b64encode(raw_a).decode("ascii")
    b64b = base64.b64encode(raw_b).decode("ascii")

    pure_results = {
        "steps": [
            {"action": "connect"},
            {"action": "get_screen", "screen_length": 1, "raw_base64": b64a},
        ],
        "screenshots": [
            {"step": 1, "action": "connect", "content": ""},
            {
                "step": 2,
                "action": "get_screen",
                "content": "A",
                "length": 1,
                "raw_base64": b64a,
            },
        ],
        "final_screen": "",
        "raw_final_base64": b64a,
        "status": "completed",
    }

    p3270_results = {
        "steps": [
            {"action": "connect"},
            {"action": "get_screen", "screen_length": 1, "raw_base64": b64b},
        ],
        "screenshots": [
            {"step": 1, "action": "connect", "content": ""},
            {
                "step": 2,
                "action": "get_screen",
                "content": "B",
                "length": 1,
                "raw_base64": b64b,
            },
        ],
        "final_screen": "",
        "raw_final_base64": b64b,
        "status": "completed",
    }

    pr = tmp_path / "pure3270_script_results.json"
    rr = tmp_path / "p3270_script_results.json"
    write_results(pr, pure_results)
    write_results(rr, p3270_results)

    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        ok = compare_script_results(compare_steps=True)
        assert ok is False
    finally:
        os.chdir(cwd)


def test_compare_script_results_step_by_step_padding_handling(tmp_path: Any) -> None:
    # Per-step padding/trimming difference when raw bytes identical
    raw = b"\x40" * 179
    raw_b64 = base64.b64encode(raw).decode("ascii")

    pure_results = {
        "steps": [
            {"action": "connect"},
            {"action": "get_screen", "screen_length": 179, "raw_base64": raw_b64},
        ],
        "screenshots": [
            {"step": 1, "action": "connect", "content": ""},
            {
                "step": 2,
                "action": "get_screen",
                "content": "",
                "length": 179,
                "raw_base64": raw_b64,
            },
        ],
        "final_screen": "",
        "raw_final_base64": raw_b64,
        "status": "completed",
    }

    p3270_results = {
        "steps": [
            {"action": "connect"},
            {"action": "get_screen", "screen_length": 23, "raw_base64": raw_b64},
        ],
        "screenshots": [
            {"step": 1, "action": "connect", "content": ""},
            {
                "step": 2,
                "action": "get_screen",
                "content": "",
                "length": 23,
                "raw_base64": raw_b64,
            },
        ],
        "final_screen": "",
        "raw_final_base64": raw_b64,
        "status": "completed",
    }

    pr = tmp_path / "pure3270_script_results.json"
    rr = tmp_path / "p3270_script_results.json"
    write_results(pr, pure_results)
    write_results(rr, p3270_results)

    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        # Non-strict should accept (minor)
        ok = compare_script_results(compare_steps=True, strict=False)
        assert ok is True
        # Strict should fail
        ok2 = compare_script_results(compare_steps=True, strict=True)
        assert ok2 is False
    finally:
        os.chdir(cwd)
