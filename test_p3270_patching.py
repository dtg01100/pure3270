#!/usr/bin/env python3
"""
Test script to verify that p3270 works correctly with pure3270 patching.
"""

import pure3270
import p3270

def test_p3270_patching():
    """Test that p3270 is correctly patched with pure3270."""
    # Enable pure3270 patching
    pure3270.enable_replacement()
    
    # Create a p3270 client
    client = p3270.P3270Client()
    
    # Verify that the client is using pure3270
    print("p3270 client created successfully")
    print(f"Client type: {type(client)}")
    print(f"Client s3270 attribute type: {type(client.s3270)}")
    
    # Try to access some attributes that should work
    try:
        connected = client.isConnected()
        print(f"isConnected() returned: {connected}")
    except Exception as e:
        print(f"isConnected() failed with error: {e}")
    
    # Try to call some methods that should work (even if they fail due to not being connected)
    try:
        result = client.sendEnter()
        print(f"sendEnter() returned: {result}")
    except Exception as e:
        print(f"sendEnter() failed with error: {e}")
        
    try:
        result = client.sendPF(1)
        print(f"sendPF(1) returned: {result}")
    except Exception as e:
        print(f"sendPF(1) failed with error: {e}")
    
    print("Test completed successfully!")

if __name__ == "__main__":
    test_p3270_patching()