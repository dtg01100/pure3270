"""Pure3270 pub400.com connectivity example.

Demonstrates using the high-level synchronous `Session` API to:
1. Connect to a public TN3270 host (pub400.com)
2. Send an Enter key
3. Read back the immediate screen buffer representation

NOTE: Public hosts may rate-limit or disconnect frequently; this
example is best-effort and intended for manual experimentation.
"""

from pure3270 import Session

HOST = "pub400.com"
PORT = 23


def main() -> int:
    print(f"Connecting to {HOST}:{PORT} ...")
    with Session() as session:
        try:
            session.connect(HOST, port=PORT)
            print("✓ Connected successfully.")
            session.send(b"key Enter")
            response = session.read()
            print("Received response:")
            print(response)
            return 0
        except Exception as e:
            print(f"Connection or negotiation failed: {e}")
            return 1
        finally:
            print("Session closed.")


if __name__ == "__main__":  # pragma: no cover - manual example
    raise SystemExit(main())
