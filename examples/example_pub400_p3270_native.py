"""Compare native p3270.P3270Client behavior against pub400.com host.

Use this to contrast screens / negotiation with the pure Python
implementation when both are available locally.
"""

from p3270 import P3270Client

HOST = "pub400.com"
PORT = 23


def main() -> int:
    print(f"Connecting to {HOST}:{PORT} using native p3270...")
    client = P3270Client(
        hostName=HOST,
        hostPort=str(PORT),
        modelName="3279-4",
        enableTLS="no",
        timeoutInSec=20,
    )
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
