"""Invoke external s3270 against pub400.com for behavioral reference.

This requires the `s3270` binary to be installed and available on PATH.
It is intentionally simple; capturing output size is limited.
"""

import subprocess
import sys

HOST = "pub400.com"
PORT = 23


def main() -> int:
    print(f"Connecting to {HOST}:{PORT} using s3270...")
    try:
        proc = subprocess.Popen(
            ["s3270", f"{HOST}:{PORT}"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if proc.stdin is None or proc.stdout is None:  # Defensive guard
            print("s3270 process did not provide expected pipes; aborting.")
            return 1
        # Send Enter key and request screen text
        for cmd in ("Enter", "PrintText"):
            proc.stdin.write(cmd + "\n")
            proc.stdin.flush()
        output = proc.stdout.read(4096)
        print("Received screen:")
        print(output)
        proc.stdin.write("Quit\n")
        proc.stdin.flush()
        proc.terminate()
        return 0
    except FileNotFoundError:
        print("s3270 binary not found on PATH; skipping.")
        return 0
    except Exception as e:
        print(f"Connection or negotiation failed: {e}")
        return 1
    finally:
        print("Session closed.")


if __name__ == "__main__":  # pragma: no cover - manual example
    raise SystemExit(main())
