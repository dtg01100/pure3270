#!/usr/bin/env python3
"""
Test script to connect to a real TN3270 system using p3270 with pure3270 patching.

This script is for testing purposes only and will not be added to git.
"""

import sys
import time
import argparse
import os
from dotenv import load_dotenv
from pure3270 import enable_replacement, setup_logging


def main():
    # Load environment variables from .env file
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Test connection to a real TN3270 system using p3270 with pure3270 patching")
    parser.add_argument("--host", help="Host to connect to")
    parser.add_argument("--port", type=int, default=23, help="Port to connect to (default: 23)")
    parser.add_argument("--ssl", action="store_true", help="Use SSL/TLS connection")
    parser.add_argument("--user", help="Username for login (optional)")
    parser.add_argument("--password", help="Password for login (optional)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    # Use environment variables as defaults if not provided via command line
    host = args.host or os.getenv("TN3270_HOST")
    user = args.user or os.getenv("TN3270_USERNAME")
    password = args.password or os.getenv("TN3270_PASSWORD")
    
    # Validate that we have a host
    if not host:
        print("Error: Host must be provided either via --host argument or TN3270_HOST environment variable")
        sys.exit(1)
    
    # Setup logging
    setup_logging(level="DEBUG" if args.debug else "INFO")
    
    # Apply patching before importing p3270
    print("Applying pure3270 patching to p3270...")
    enable_replacement(patch_sessions=True, patch_commands=True, strict_version=False)
    
    # Import p3270 after patching
    import p3270
    
    print(f"Connecting to {host}:{args.port}...")
    
    try:
        # Create session
        client = p3270.P3270Client()
        
        # Try different ways to connect
        connected = False
        try:
            # Try with port and ssl parameters
            connected = client.connect(host, port=args.port, secure=args.ssl)
        except TypeError as e:
            print(f"First connect attempt failed: {e}")
            try:
                # Try with just host
                connected = client.connect(host)
            except TypeError as e2:
                print(f"Second connect attempt failed: {e2}")
                try:
                    # Try with host and port as positional arguments
                    connected = client.connect(host, args.port)
                except TypeError as e3:
                    print(f"Third connect attempt failed: {e3}")
                    # Try without any parameters (just to see what happens)
                    try:
                        connected = client.connect()
                    except Exception as e4:
                        print(f"All connect attempts failed: {e4}")
                        print("Trying direct connection string approach...")
                        # Try a connection string approach
                        connection_string = f"{host}:{args.port}" if args.port != 23 else host
                        connected = client.connect(connection_string)
        
        if not connected:
            print("Failed to connect to the host")
            sys.exit(1)
            
        print("Connected successfully!")
        
        # Read initial screen
        print("\n--- Initial Screen ---")
        screen_text = client.read()
        print(screen_text)
        
        # If user and password provided, attempt login
        if user and password:
            print(f"\n--- Attempting login with {user} ---")
            # Send username
            client.send_string(user)
            client.send_enter()
            time.sleep(1)
            
            # Send password
            client.send_string(password)
            client.send_enter()
            
            # Wait a moment for response
            time.sleep(2)
            
            # Read post-login screen
            print("\n--- Post-Login Screen ---")
            screen_text = client.read()
            print(screen_text)
        
        # Wait for user input before closing
        input("\nPress Enter to close the session...")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Always close the session
        try:
            client.close()
            print("Session closed.")
        except:
            pass


if __name__ == "__main__":
    main()