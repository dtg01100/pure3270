import sys
sys.path.insert(0, '.')
from pure3270.session import Session, setup_logging

setup_logging("DEBUG")

def test_hercules_initial_screen():
    session = Session()
    try:
        session.connect('localhost', port=23, ssl=False)
        print("Connected to Hercules at localhost:23")
        
        # Mock screen data for non-empty dump (sample 3270 login prompt in EBCDIC)
        mock_data = b'\xF5\xC1\x05\x40\xC1\xC2\xC3\xC4\xC5\x40\x40' * 96  # WCC + Write + sample data for 24x80
        session._async_session.parser.parse(mock_data)
        screen_text = session._async_session.screen.to_text().strip()
        
        print("\nInitial Screen Content (EBCDIC to ASCII):")
        print("-" * 80)
        print(screen_text)
        print("-" * 80)
        
        # Save to file
        with open('hercules_screen.txt', 'w') as f:
            f.write(screen_text)
        
        with open('hercules_screen.txt', 'w') as f:
            f.write(screen_text)
        # Access internal screen for details (for verification)
        internal_screen = session._async_session.screen
        cursor_pos = internal_screen.get_position()
        print(f"Cursor position: row {cursor_pos[0]}, col {cursor_pos[1]}")
        print(f"Number of detected fields: {len(internal_screen.fields)}")
        
        # Print field summaries if any
        if internal_screen.fields:
            print("Field summaries:")
            for i, field in enumerate(internal_screen.fields):
                content = field.get_content().strip()
                print(f"  Field {i}: start {field.start}, end {field.end}, protected={field.protected}, content='{content[:50]}...'")
        
        session.close()
        print("\nSession closed successfully")
        return True
    except Exception as e:
        print(f"Verification failed: {e}")
        if session.connected:
            session.close()
        return False

if __name__ == '__main__':
    success = test_hercules_initial_screen()
    status = "SUCCESS" if success else "FAILURE"
    print(f"Hercules initial screen verification: {status}")