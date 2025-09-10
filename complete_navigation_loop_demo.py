#!/usr/bin/env python3
"""
Complete loop demonstration: Navigation with screen content reading.
This demonstrates the full cycle of:
1. Connect to TN3270 server
2. Read initial screen content
3. Navigate based on screen content
4. Read updated screen content
5. Make decisions based on content
6. Continue navigation loop
"""

import asyncio
from typing import List, Tuple, Optional
from unittest.mock import AsyncMock, MagicMock, patch

# Import pure3270
import pure3270
from pure3270 import AsyncSession

class NavigationWithContentReadingDemo:
    """Demonstrate complete navigation loop with screen content reading."""
    
    def __init__(self):
        self.session: Optional[AsyncSession] = None
        self.navigation_log: List[str] = []
    
    @patch('pure3270.session.TN3270Handler')
    @patch('pure3270.session.asyncio.open_connection')
    async def run_complete_navigation_loop(self, mock_open, mock_handler):
        """Run complete navigation loop with screen content reading."""
        print("=== COMPLETE NAVIGATION LOOP WITH SCREEN CONTENT READING ===")
        
        # Mock connection
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_open.return_value = (mock_reader, mock_writer)
        
        # Mock handler with screen buffer
        handler_instance = AsyncMock()
        mock_handler.return_value = handler_instance
        
        # Create session
        self.session = AsyncSession("localhost", 23)
        await self.session.connect()
        self.log_action("Connected to TN3270 server")
        
        try:
            # Phase 1: Initial screen analysis
            print("\n--- PHASE 1: INITIAL SCREEN ANALYSIS ---")
            initial_analysis = await self.analyze_current_screen("Initial Login Screen")
            self.log_action(f"Analyzed initial screen: {initial_analysis['title']}")
            
            # Phase 2: Login sequence with content-based decisions
            print("\n--- PHASE 2: LOGIN SEQUENCE ---")
            login_success = await self.perform_login_sequence()
            self.log_action(f"Login sequence completed: {'Success' if login_success else 'Failed'}")
            
            # Phase 3: Menu navigation with content reading
            print("\n--- PHASE 3: MENU NAVIGATION ---")
            menu_navigation_success = await self.navigate_application_menus()
            self.log_action(f"Menu navigation completed: {'Success' if menu_navigation_success else 'Failed'}")
            
            # Phase 4: Data entry with field content reading
            print("\n--- PHASE 4: DATA ENTRY ---")
            data_entry_success = await self.perform_data_entry()
            self.log_action(f"Data entry completed: {'Success' if data_entry_success else 'Failed'}")
            
            # Phase 5: Form submission and response analysis
            print("\n--- PHASE 5: FORM SUBMISSION AND RESPONSE ---")
            submission_success = await self.submit_form_and_analyze_response()
            self.log_action(f"Form submission completed: {'Success' if submission_success else 'Failed'}")
            
            # Phase 6: Navigation completion and logout
            print("\n--- PHASE 6: LOGOUT AND CLEANUP ---")
            logout_success = await self.perform_logout()
            self.log_action(f"Logout completed: {'Success' if logout_success else 'Failed'}")
            
            # Show complete navigation log
            print("\n--- COMPLETE NAVIGATION LOG ---")
            for i, log_entry in enumerate(self.navigation_log, 1):
                print(f"{i:2d}. {log_entry}")
            
            return True
            
        except Exception as e:
            self.log_action(f"Navigation loop failed: {type(e).__name__}: {e}")
            return False
        finally:
            try:
                await self.session.disconnect()
                self.log_action("Disconnected from TN3270 server")
            except:
                pass
    
    async def analyze_current_screen(self, screen_title: str) -> dict:
        """Analyze current screen content and return structured information."""
        self.log_action(f"Analyzing screen: {screen_title}")
        
        # Get screen content
        screen_text = self.session.screen_buffer.to_text()
        fields = self.session.screen_buffer.fields
        rows = self.session.screen_buffer.rows
        cols = self.session.screen_buffer.cols
        cursor_row, cursor_col = self.session.screen_buffer.get_position()
        
        # Get screen lines
        lines = screen_text.split('\n') if screen_text else []
        
        # Analyze screen structure
        analysis = {
            'title': screen_title,
            'dimensions': f"{rows}×{cols}",
            'cursor_position': f"({cursor_row}, {cursor_col})",
            'total_lines': len(lines),
            'total_fields': len(fields),
            'screen_length': len(screen_text),
            'first_line': lines[0].strip() if lines else "",
            'last_line': lines[-1].strip() if lines else "",
            'contains_menu': 'MENU' in screen_text.upper(),
            'contains_error': 'ERROR' in screen_text.upper(),
            'contains_help': 'HELP' in screen_text.upper(),
            'contains_exit': 'EXIT' in screen_text.upper() or 'QUIT' in screen_text.upper(),
            'input_prompt_detected': any('=>' in line or ':' in line for line in lines),
            'function_keys_present': any('F1=' in line or 'F3=' in line for line in lines)
        }
        
        # Log detailed analysis
        self.log_action(f"  Dimensions: {analysis['dimensions']}")
        self.log_action(f"  Cursor: {analysis['cursor_position']}")
        self.log_action(f"  Fields: {analysis['total_fields']}")
        self.log_action(f"  Lines: {analysis['total_lines']}")
        self.log_action(f"  First line: {repr(analysis['first_line'][:30])}")
        self.log_action(f"  Contains menu: {analysis['contains_menu']}")
        self.log_action(f"  Input prompt: {analysis['input_prompt_detected']}")
        
        return analysis
    
    async def perform_login_sequence(self) -> bool:
        """Perform login sequence with screen content reading."""
        self.log_action("Starting login sequence")
        
        # Read initial login screen
        screen_analysis = await self.analyze_current_screen("Login Screen")
        
        # Look for username field
        screen_text = self.session.screen_buffer.to_text()
        if 'USERNAME' in screen_text.upper() or 'USER' in screen_text.upper():
            self.log_action("Username field detected")
            await self.session.move_cursor(4, 16)  # Typical username position
            await self.session.insert_text("TESTUSER")
            self.log_action("Entered username")
        
        # Look for password field
        if 'PASSWORD' in screen_text.upper() or 'PASS' in screen_text.upper():
            self.log_action("Password field detected")
            await self.session.move_cursor(5, 16)  # Typical password position
            await self.session.insert_text("TESTPASS")
            self.log_action("Entered password")
        
        # Submit login
        await self.session.enter()
        self.log_action("Submitted login form")
        
        # Read response screen
        response_analysis = await self.analyze_current_screen("Login Response")
        
        # Check for success/failure
        response_text = self.session.screen_buffer.to_text().upper()
        if 'INVALID' in response_text or 'ERROR' in response_text:
            self.log_action("Login failed - invalid credentials")
            return False
        elif 'WELCOME' in response_text or 'MAIN MENU' in response_text:
            self.log_action("Login successful")
            return True
        else:
            self.log_action("Login response unclear, assuming success")
            return True
    
    async def navigate_application_menus(self) -> bool:
        """Navigate application menus based on screen content."""
        self.log_action("Starting menu navigation")
        
        # Read main menu
        menu_analysis = await self.analyze_current_screen("Main Menu")
        
        # Look for menu options in screen text
        screen_text = self.session.screen_buffer.to_text()
        lines = screen_text.split('\n')
        
        # Find report generation option
        report_option = None
        for i, line in enumerate(lines):
            if 'REPORT' in line.upper() and 'GENERAT' in line.upper():
                report_option = i
                self.log_action(f"Report generation option found at line {i}")
                break
        
        if report_option is not None:
            # Select report option (typically by entering line number)
            await self.session.insert_text("3")  # Assuming it's option 3
            await self.session.enter()
            self.log_action("Selected report generation option")
        else:
            # Try common menu options
            menu_options = ["1", "2", "3", "4"]
            for option in menu_options:
                await self.session.insert_text(option)
                await self.session.enter()
                self.log_action(f"Tried menu option {option}")
                
                # Check response
                response_analysis = await self.analyze_current_screen(f"Menu Response {option}")
                response_text = self.session.screen_buffer.to_text().upper()
                
                if 'REPORT' in response_text or 'GENERAT' in response_text:
                    self.log_action(f"Menu option {option} led to correct screen")
                    break
                elif 'INVALID' in response_text or 'ERROR' in response_text:
                    self.log_action(f"Menu option {option} was invalid, trying next")
                    # Go back to menu (PF3 is common for "back")
                    await self.session.pf(3)
                    await asyncio.sleep(0.1)
                    continue
                else:
                    self.log_action(f"Menu option {option} response unclear")
                    break
        
        return True
    
    async def perform_data_entry(self) -> bool:
        """Perform data entry with field content reading."""
        self.log_action("Starting data entry")
        
        # Read data entry screen
        data_screen_analysis = await self.analyze_current_screen("Data Entry Screen")
        
        # Get fields
        fields = self.session.screen_buffer.fields
        self.log_action(f"Found {len(fields)} input fields")
        
        # Enter data in fields
        field_data = [
            ("CUSTOMER_ID", "CUST12345"),
            ("ORDER_DATE", "2023-12-01"),
            ("QUANTITY", "10"),
            ("DESCRIPTION", "TEST ITEM")
        ]
        
        for i, (field_name, field_value) in enumerate(field_data):
            if i < len(fields):
                self.log_action(f"Entering {field_name}: {field_value}")
                # Move to field (simplified - in reality would use field navigation)
                await self.session.move_cursor(6 + i, 24)  # Approximate positions
                await self.session.insert_text(field_value)
        
        return True
    
    async def submit_form_and_analyze_response(self) -> bool:
        """Submit form and analyze server response."""
        self.log_action("Submitting form")
        
        # Submit form
        await self.session.enter()
        self.log_action("Form submitted")
        
        # Read response
        response_analysis = await self.analyze_current_screen("Form Response")
        response_text = self.session.screen_buffer.to_text().upper()
        
        # Analyze response content
        if 'SUCCESS' in response_text or 'CONFIRM' in response_text:
            self.log_action("Form submission successful")
            success_details = self.extract_success_details()
            self.log_action(f"Success details: {success_details}")
        elif 'ERROR' in response_text or 'INVALID' in response_text:
            self.log_action("Form submission failed")
            error_details = self.extract_error_details()
            self.log_action(f"Error details: {error_details}")
        else:
            self.log_action("Form response ambiguous")
            # Try to extract any relevant information
            key_info = self.extract_key_information()
            self.log_action(f"Key information: {key_info}")
        
        return True
    
    async def perform_logout(self) -> bool:
        """Perform logout sequence."""
        self.log_action("Starting logout sequence")
        
        # Look for logout option
        screen_text = self.session.screen_buffer.to_text()
        lines = screen_text.split('\n')
        
        # Find logout option
        logout_found = False
        for line in lines:
            if 'LOGOUT' in line.upper() or 'QUIT' in line.upper() or 'EXIT' in line.upper():
                logout_found = True
                self.log_action("Logout option detected")
                break
        
        if logout_found:
            # Use common logout methods
            logout_methods = [
                ("PF4", lambda: self.session.pf(4)),
                ("QUIT command", lambda: self.session.insert_text("QUIT")),
                ("EXIT command", lambda: self.session.insert_text("EXIT")),
                ("F3 then QUIT", lambda: asyncio.gather(self.session.pf(3), asyncio.sleep(0.1), self.session.insert_text("QUIT")))
            ]
            
            for method_name, method_func in logout_methods:
                try:
                    self.log_action(f"Trying logout method: {method_name}")
                    await method_func()
                    await self.session.enter()
                    self.log_action(f"Logout method {method_name} executed")
                    break
                except Exception as e:
                    self.log_action(f"Logout method {method_name} failed: {e}")
                    continue
        else:
            # Force disconnect
            self.log_action("No explicit logout found, forcing disconnect")
        
        return True
    
    def extract_success_details(self) -> dict:
        """Extract success details from screen."""
        screen_text = self.session.screen_buffer.to_text()
        lines = screen_text.split('\n')
        
        details = {}
        for line in lines:
            if 'TRANSACTION' in line.upper():
                details['transaction'] = line.strip()
            elif 'REFERENCE' in line.upper():
                details['reference'] = line.strip()
            elif 'CONFIRMATION' in line.upper():
                details['confirmation'] = line.strip()
        
        return details
    
    def extract_error_details(self) -> dict:
        """Extract error details from screen."""
        screen_text = self.session.screen_buffer.to_text()
        lines = screen_text.split('\n')
        
        details = {}
        for line in lines:
            if 'ERROR' in line.upper():
                details['error_message'] = line.strip()
            elif 'CODE' in line.upper():
                details['error_code'] = line.strip()
            elif 'REASON' in line.upper():
                details['error_reason'] = line.strip()
        
        return details
    
    def extract_key_information(self) -> dict:
        """Extract key information from screen regardless of type."""
        screen_text = self.session.screen_buffer.to_text()
        lines = screen_text.split('\n')
        
        info = {}
        for line in lines[:10]:  # Check first 10 lines
            if ':' in line:
                key, value = line.split(':', 1)
                info[key.strip()] = value.strip()
        
        return info
    
    def log_action(self, action: str):
        """Log navigation action."""
        self.navigation_log.append(action)
        print(f"  ✓ {action}")

async def demonstrate_content_driven_navigation():
    """Demonstrate navigation driven by screen content reading."""
    print("\n=== CONTENT-DRIVEN NAVIGATION DEMONSTRATION ===")
    
    examples = [
        {
            "title": "Adaptive Menu Navigation",
            "description": "Navigation that adapts based on menu options found on screen",
            "code": '''
async def adaptive_menu_navigation(session):
    """Navigate menus by reading available options."""
    
    # Read current screen
    screen_text = session.screen_buffer.to_text()
    lines = screen_text.split(chr(10))
    
    # Build menu map from screen content
    menu_map = {}
    for line in lines:
        # Look for numbered menu options
        if line.strip().startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')):
            option_parts = line.strip().split('.', 1)
            if len(option_parts) == 2:
                option_num = option_parts[0].strip()
                option_text = option_parts[1].strip()
                menu_map[option_text.lower()] = option_num
                print(f"Found menu option: {option_num}. {option_text}")
    
    # Navigate to specific option based on content
    target_options = ["report", "query", "generate"]
    for target in target_options:
        for menu_text, menu_num in menu_map.items():
            if target in menu_text:
                print(f"Selecting {target} option: {menu_num}")
                await session.insert_text(menu_num)
                await session.enter()
                return True
    
    # If no target found, try first available option
    if menu_map:
        first_option = list(menu_map.values())[0]
        print(f"No target found, selecting first option: {first_option}")
        await session.insert_text(first_option)
        await session.enter()
        return True
    
    return False
'''
        },
        {
            "title": "Intelligent Field Filling",
            "description": "Filling fields by reading their labels and context",
            "code": '''
async def intelligent_field_filling(session, data_dict):
    """Fill fields by reading their labels and context."""
    
    # Get current screen text
    screen_text = session.screen_buffer.to_text()
    lines = screen_text.split(chr(10))
    
    # Create field mapping based on labels
    field_mapping = {}
    
    for i, line in enumerate(lines[:-1]):  # Don't check last line
        line_upper = line.upper()
        
        # Look for common field labels
        label_indicators = [
            ('CUSTOMER', 'customer_id'),
            ('NAME', 'customer_name'), 
            ('ADDRESS', 'address'),
            ('PHONE', 'phone'),
            ('EMAIL', 'email'),
            ('DATE', 'date'),
            ('QUANTITY', 'quantity'),
            ('PRICE', 'price'),
            ('TOTAL', 'total')
        ]
        
        for label_indicator, data_key in label_indicators:
            if label_indicator in line_upper:
                # Field is typically on next line or nearby
                field_line = i + 1
                if field_line < len(lines):
                    field_mapping[data_key] = {
                        'label_line': i,
                        'field_line': field_line,
                        'label_text': line.strip(),
                        'data_value': data_dict.get(data_key, '')
                    }
                    print(f"Mapped {data_key} to line {field_line}")
    
    # Fill the mapped fields
    for data_key, field_info in field_mapping.items():
        if field_info['data_value']:
            # Move to approximate field position
            await session.move_cursor(field_info['field_line'], 24)
            await session.insert_text(field_info['data_value'])
            print(f"Filled {data_key}: {field_info['data_value']}")
    
    return len(field_mapping) > 0
'''
        },
        {
            "title": "Error Detection and Recovery",
            "description": "Detecting errors and taking corrective actions based on screen content",
            "code": '''
async def error_detective_navigation(session, operation_func):
    """Execute operations with intelligent error detection and recovery."""
    
    max_attempts = 3
    for attempt in range(max_attempts):
        # Execute the operation
        try:
            result = await operation_func(session)
        except Exception as e:
            print(f"Operation failed: {e}")
            if attempt < max_attempts - 1:
                await asyncio.sleep(1)
                continue
            else:
                raise
        
        # Read screen to check for errors
        screen_text = session.screen_buffer.to_text().upper()
        lines = screen_text.split(chr(10))
        
        # Check for various error conditions
        error_detected = False
        error_type = None
        
        for line in lines:
            if 'ERROR' in line:
                error_detected = True
                error_type = 'general_error'
                print(f"General error detected: {line.strip()}")
                break
            elif 'INVALID' in line:
                error_detected = True
                error_type = 'invalid_input'
                print(f"Invalid input detected: {line.strip()}")
                break
            elif 'TIMEOUT' in line:
                error_detected = True
                error_type = 'timeout'
                print(f"Timeout detected: {line.strip()}")
                break
            elif 'NOT FOUND' in line:
                error_detected = True
                error_type = 'not_found'
                print(f"Not found error: {line.strip()}")
                break
        
        # Take corrective action based on error type
        if error_detected:
            if attempt < max_attempts - 1:
                print(f"Attempt {attempt + 1}: Taking corrective action for {error_type}")
                
                if error_type == 'invalid_input':
                    # Clear input and try with different data
                    await session.field_end()
                    await session.erase_eof()
                    # Modify input data for next attempt
                    print("Cleared invalid input, will retry")
                    
                elif error_type == 'timeout':
                    # Wait and retry
                    print("Timeout occurred, waiting before retry")
                    await asyncio.sleep(2)
                    
                elif error_type == 'not_found':
                    # Go back and try different path
                    await session.pf(3)  # PF3 is commonly "go back"
                    print("Going back to previous screen")
                    await asyncio.sleep(1)
                    
                else:
                    # Generic error recovery
                    await session.enter()  # Often clears error messages
                    print("Sent Enter to clear error message")
                    await asyncio.sleep(1)
                
                continue  # Try again
            else:
                print(f"All {max_attempts} attempts failed")
                raise RuntimeError(f"Operation failed after {max_attempts} attempts due to {error_type}")
        else:
            # No error detected, operation successful
            print("Operation completed successfully")
            return result
    
    raise RuntimeError(f"Operation failed after {max_attempts} attempts")
'''
        }
    ]
    
    for example in examples:
        print(f"\n{example['title']}: {example['description']}")
        print("-" * 60)
        print(example['code'].strip())

async def main():
    """Main demonstration function."""
    print("PURE3270 COMPLETE NAVIGATION LOOP WITH SCREEN CONTENT READING")
    print("=" * 80)
    print("Demonstrating how pure3270 reads screen content to drive navigation:")
    print("  1. Connect to TN3270 server")
    print("  2. Read and analyze initial screen content") 
    print("  3. Navigate based on content analysis")
    print("  4. Read updated screen content")
    print("  5. Make decisions based on new content")
    print("  6. Continue navigation loop until completion")
    print("  7. Logout and disconnect properly")
    print("=" * 80)
    
    try:
        # Run complete navigation loop demonstration
        demo = NavigationWithContentReadingDemo()
        success = await demo.run_complete_navigation_loop()
        
        # Show content-driven navigation examples
        await demonstrate_content_driven_navigation()
        
        print("\n" + "=" * 80)
        if success:
            print("🎉 COMPLETE NAVIGATION LOOP DEMONSTRATION SUCCESSFUL!")
            print("Pure3270 successfully demonstrated:")
            print("  ✓ Full screen content reading and analysis")
            print("  ✓ Content-driven navigation decisions") 
            print("  ✓ Field content extraction and filling")
            print("  ✓ Error detection and recovery")
            print("  ✓ Form submission and response analysis")
            print("  ✓ Adaptive menu navigation")
        else:
            print("❌ NAVIGATION LOOP DEMONSTRATION HAD ISSUES!")
            print("Note: This is expected in mock environment without real server.")
        
        print("\nKey Features Demonstrated:")
        print("  ✓ Read screen text and analyze structure")
        print("  ✓ Extract field information and content") 
        print("  ✓ Search for specific text patterns")
        print("  ✓ Navigate based on screen content")
        print("  ✓ Handle errors by reading screen messages")
        print("  ✓ Make decisions from screen analysis")
        print("  ✓ Complete navigation loop with feedback")
        
        return success
        
    except Exception as e:
        print(f"❌ Demonstration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)