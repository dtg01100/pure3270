"""Validate Pure3270 `P3270Client` abstraction against pub400.com.

Mirrors the usage semantics of the legacy p3270 client to illustrate
API compatibility of the drop-in replacement path.
"""

from pure3270.p3270_client import P3270Client

HOST = "pub400.com"
PORT = 23


def main() -> int:
    print(f"Connecting to {HOST}:{PORT} using P3270Client...")
    client = P3270Client(hostName=HOST, hostPort=PORT)
    try:
        client.connect()
        print("✓ Connected successfully.")
        client.sendEnter()
        screen = client.getScreen()
        print("Received screen:")
        print(screen)
        return 0
    except Exception as e:
        print(f"Connection or negotiation failed: {e}")
        return 1
    finally:
        client.disconnect()
        print("Session closed.")


if __name__ == "__main__":  # pragma: no cover - manual example
    raise SystemExit(main())
