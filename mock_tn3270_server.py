#!/usr/bin/env python3
"""
Simple TN3270 mock server for Docker container.
"""

import socket
import threading
import sys
import time


def handle_client(client_socket, address):
    """Handle a client connection."""
    print(f"Client connected from {address}")

    try:
        while True:
            data = client_socket.recv(1024)
            if not data:
                break

            # Echo back for basic testing
            client_socket.send(data)

    except Exception as e:
        print(f"Error handling client {address}: {e}")
    finally:
        client_socket.close()
        print(f"Client {address} disconnected")


def main():
    """Main server function."""
    host = "0.0.0.0"
    port = 23

    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((host, port))
        server_socket.listen(5)

        print(f"TN3270 Mock Server listening on {host}:{port}")

        while True:
            try:
                client_socket, address = server_socket.accept()
                client_thread = threading.Thread(
                    target=handle_client, args=(client_socket, address)
                )
                client_thread.daemon = True
                client_thread.start()
            except KeyboardInterrupt:
                print("\nShutting down server...")
                break
            except Exception as e:
                print(f"Error accepting connection: {e}")

    except Exception as e:
        print(f"Server error: {e}")
        return 1
    finally:
        if "server_socket" in locals():
            server_socket.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
