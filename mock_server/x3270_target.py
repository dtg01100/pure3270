"""Helper for running x3270 target as subprocess."""

import subprocess
from pathlib import Path
from typing import Optional


def find_x3270_target() -> Optional[Path]:
    """Find x3270 target.py in Common/test/target."""
    locations = [
        Path("~/x3270/Common/test/target.py").expanduser(),
        Path("/usr/local/share/x3270/Common/test/target.py"),
        Path("Common/test/target.py"),
    ]
    for loc in locations:
        if loc.exists():
            return loc
    return None


def start_x3270_target(
    scenario: str = "menu-f",
    port: int = 8021,
    host: str = "127.0.0.1",
) -> subprocess.Popen[bytes]:
    """Start x3270 target as subprocess.

    Returns the Popen object. Caller should call proc.terminate() when done.
    """
    target_path = find_x3270_target()
    if target_path is None:
        raise RuntimeError(
            "x3270 target.py not found. "
            "Clone https://github.com/wuzuf/x3270 or install x3270 package."
        )

    return subprocess.Popen(
        [
            "python3",
            str(target_path),
            "--type",
            scenario,
            "--port",
            str(port),
            "--address",
            host,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
