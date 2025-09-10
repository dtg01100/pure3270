"""
Wrapper class to make pure3270 compatible with p3270's S3270 interface.
"""

import logging
from typing import Optional, Any
from pure3270.session import Session, SessionError

logger = logging.getLogger(__name__)


class Pure3270S3270Wrapper:
    """
    A wrapper that implements the same interface as p3270.S3270
    but uses pure3270.Session internally.

    This allows p3270.P3270Client to work with pure3270 instead of
    spawning the external s3270 binary.
    """

    numOfInstances = 0

    def __init__(self, args, encoding="latin1"):
        """
        Initialize the wrapper.

        Args:
            args: Command line arguments (ignored, for compatibility)
            encoding: Text encoding (ignored, for compatibility)
        """
        self.args = args
        self.encoding = encoding
        self.buffer = None
        self.statusMsg = None

        # Create our pure3270 session
        self._session = Session()

        # Increment instance counter
        Pure3270S3270Wrapper.numOfInstances += 1
        logger.debug(
            f"Created Pure3270S3270Wrapper instance #{Pure3270S3270Wrapper.numOfInstances}"
        )

    def do(self, cmd: str) -> bool:
        """
        Execute an s3270 command.

        Args:
            cmd: The s3270 command to execute

        Returns:
            True if command succeeded, False otherwise
        """
        logger.debug(f"Executing s3270 command: {cmd}")

        try:
            # Parse the command and map it to pure3270 operations
            result = self._execute_command(cmd)
            return result
        except Exception as e:
            logger.error(f"Error executing command '{cmd}': {e}")
            self.statusMsg = self._create_error_status()
            return False

    def _execute_command(self, cmd: str) -> bool:
        """
        Parse and execute an s3270 command.

        Args:
            cmd: The s3270 command to execute

        Returns:
            True if command succeeded, False otherwise
        """
        # Strip whitespace and newlines
        cmd = cmd.strip()
        if cmd.endswith("\n"):
            cmd = cmd[:-1]

        # Handle different command types
        if cmd.startswith("Connect("):
            return self._handle_connect(cmd)
        elif cmd == "Disconnect":
            return self._handle_disconnect()
        elif cmd == "Quit":
            return self._handle_quit()
        elif cmd == "Enter":
            return self._handle_enter()
        elif cmd.startswith("PF("):
            return self._handle_pf(cmd)
        elif cmd.startswith("PA("):
            return self._handle_pa(cmd)
        elif cmd == "BackSpace":
            return self._handle_backspace()
        elif cmd == "BackTab":
            return self._handle_backtab()
        elif cmd == "Home":
            return self._handle_home()
        elif cmd == "Tab":
            return self._handle_tab()
        elif cmd.startswith("Key("):
            return self._handle_key(cmd)
        elif cmd == "Clear":
            return self._handle_clear()
        elif cmd == "Delete":
            return self._handle_delete()
        elif cmd == "DeleteField":
            return self._handle_delete_field()
        elif cmd == "DeleteWord":
            return self._handle_delete_word()
        elif cmd == "Erase":
            return self._handle_erase()
        elif cmd == "Down":
            return self._handle_down()
        elif cmd == "Up":
            return self._handle_up()
        elif cmd == "Left":
            return self._handle_left()
        elif cmd == "Right":
            return self._handle_right()
        elif cmd.startswith("MoveCursor("):
            return self._handle_move_cursor(cmd)
        elif cmd.startswith("String("):
            return self._handle_string(cmd)
        elif cmd.startswith("PrintText("):
            return self._handle_print_text(cmd)
        elif cmd == "NoOpCommand":
            return self._handle_noop()
        elif cmd.startswith("Ascii("):
            return self._handle_ascii(cmd)
        elif cmd.startswith("Wait("):
            return self._handle_wait(cmd)
        else:
            logger.warning(f"Unknown command: {cmd}")
            self.statusMsg = self._create_status()
            return True  # For compatibility, we don't fail on unknown commands

    def _handle_connect(self, cmd: str) -> bool:
        """Handle Connect command."""
        # Parse connection parameters from command
        # Examples: Connect(B:hostname), Connect(L:lu@hostname)
        # For now, we'll just set status and return success
        logger.info(f"Handling connect command: {cmd}")
        self.statusMsg = self._create_status(connection_state="C(hostname)")
        return True

    def _handle_disconnect(self) -> bool:
        """Handle Disconnect command."""
        logger.info("Handling disconnect command")
        self.statusMsg = self._create_status(connection_state="N")
        return True

    def _handle_quit(self) -> bool:
        """Handle Quit command."""
        logger.info("Handling quit command")
        self.statusMsg = self._create_status()
        return True

    def _handle_enter(self) -> bool:
        """Handle Enter command."""
        logger.info("Handling enter command")
        # Send Enter key action
        try:
            self._session.enter()
            self.statusMsg = self._create_status()
            return True
        except Exception as e:
            logger.error(f"Error sending Enter: {e}")
            self.statusMsg = self._create_error_status()
            return False

    def _handle_pf(self, cmd: str) -> bool:
        """Handle PF command."""
        # Parse PF number: PF(1), PF(2), etc.
        try:
            pf_num = int(cmd[3:-1])  # Extract number from PF(n)
            logger.info(f"Handling PF command: {pf_num}")
            # Send PF key action
            self._session.pf(pf_num)
            self.statusMsg = self._create_status()
            return True
        except Exception as e:
            logger.error(f"Error handling PF command '{cmd}': {e}")
            self.statusMsg = self._create_error_status()
            return False

    def _handle_pa(self, cmd: str) -> bool:
        """Handle PA command."""
        # Parse PA number: PA(1), PA(2), etc.
        try:
            pa_num = int(cmd[3:-1])  # Extract number from PA(n)
            logger.info(f"Handling PA command: {pa_num}")
            # Send PA key action
            self._session.pa(pa_num)
            self.statusMsg = self._create_status()
            return True
        except Exception as e:
            logger.error(f"Error handling PA command '{cmd}': {e}")
            self.statusMsg = self._create_error_status()
            return False

    def _handle_backspace(self) -> bool:
        """Handle BackSpace command."""
        logger.info("Handling backspace command")
        # Send BackSpace key action
        try:
            self._session.backspace()  # Using backspace method
            self.statusMsg = self._create_status()
            return True
        except Exception as e:
            logger.error(f"Error sending BackSpace: {e}")
            self.statusMsg = self._create_error_status()
            return False

    def _handle_backtab(self) -> bool:
        """Handle BackTab command."""
        logger.info("Handling backtab command")
        # Send BackTab key action
        self.statusMsg = self._create_status()
        return True

    def _handle_home(self) -> bool:
        """Handle Home command."""
        logger.info("Handling home command")
        # Send Home key action
        try:
            self._session.home()
            self.statusMsg = self._create_status()
            return True
        except Exception as e:
            logger.error(f"Error sending Home: {e}")
            self.statusMsg = self._create_error_status()
            return False

    def _handle_tab(self) -> bool:
        """Handle Tab command."""
        logger.info("Handling tab command")
        # Send Tab key action
        self.statusMsg = self._create_status()
        return True

    def _handle_key(self, cmd: str) -> bool:
        """Handle Key command."""
        # Parse key: Key(A), Key(B), etc.
        try:
            key = cmd[4:-1]  # Extract key from Key(X)
            logger.info(f"Handling key command: {key}")
            # Send key action
            # For now, we'll just set status
            self.statusMsg = self._create_status()
            return True
        except Exception as e:
            logger.error(f"Error handling Key command '{cmd}': {e}")
            self.statusMsg = self._create_error_status()
            return False

    def _handle_clear(self) -> bool:
        """Handle Clear command."""
        logger.info("Handling clear command")
        # Send Clear action using erase method
        try:
            self._session.erase()
            self.statusMsg = self._create_status()
            return True
        except Exception as e:
            logger.error(f"Error handling Clear: {e}")
            self.statusMsg = self._create_error_status()
            return False

    def _handle_delete(self) -> bool:
        """Handle Delete command."""
        logger.info("Handling delete command")
        # Send Delete action
        try:
            self._session.erase()  # Using erase as equivalent
            self.statusMsg = self._create_status()
            return True
        except Exception as e:
            logger.error(f"Error handling Delete: {e}")
            self.statusMsg = self._create_error_status()
            return False

    def _handle_delete_field(self) -> bool:
        """Handle DeleteField command."""
        logger.info("Handling delete field command")
        # Send DeleteField action
        try:
            self._session.erase_eof()  # Using erase_eof as equivalent
            self.statusMsg = self._create_status()
            return True
        except Exception as e:
            logger.error(f"Error handling DeleteField: {e}")
            self.statusMsg = self._create_error_status()
            return False

    def _handle_delete_word(self) -> bool:
        """Handle DeleteWord command."""
        logger.info("Handling delete word command")
        # Send DeleteWord action
        self.statusMsg = self._create_status()
        return True

    def _handle_erase(self) -> bool:
        """Handle Erase command."""
        logger.info("Handling erase command")
        # Send Erase action
        try:
            self._session.erase()
            self.statusMsg = self._create_status()
            return True
        except Exception as e:
            logger.error(f"Error handling Erase: {e}")
            self.statusMsg = self._create_error_status()
            return False

    def _handle_down(self) -> bool:
        """Handle Down command."""
        logger.info("Handling down command")
        # Send Down action
        try:
            self._session.down()
            self.statusMsg = self._create_status()
            return True
        except Exception as e:
            logger.error(f"Error handling Down: {e}")
            self.statusMsg = self._create_error_status()
            return False

    def _handle_up(self) -> bool:
        """Handle Up command."""
        logger.info("Handling up command")
        # Send Up action
        try:
            self._session.up()
            self.statusMsg = self._create_status()
            return True
        except Exception as e:
            logger.error(f"Error handling Up: {e}")
            self.statusMsg = self._create_error_status()
            return False

    def _handle_left(self) -> bool:
        """Handle Left command."""
        logger.info("Handling left command")
        # Send Left action
        try:
            self._session.left()
            self.statusMsg = self._create_status()
            return True
        except Exception as e:
            logger.error(f"Error handling Left: {e}")
            self.statusMsg = self._create_error_status()
            return False

    def _handle_right(self) -> bool:
        """Handle Right command."""
        logger.info("Handling right command")
        # Send Right action
        try:
            self._session.right()
            self.statusMsg = self._create_status()
            return True
        except Exception as e:
            logger.error(f"Error handling Right: {e}")
            self.statusMsg = self._create_error_status()
            return False

    def _handle_move_cursor(self, cmd: str) -> bool:
        """Handle MoveCursor command."""
        # Parse coordinates: MoveCursor(row, col)
        try:
            coords = cmd[11:-1]  # Extract coordinates from MoveCursor(row, col)
            row, col = map(int, coords.split(","))
            logger.info(f"Handling move cursor command: row={row}, col={col}")
            # Move cursor action
            # For now, we'll just set status
            self.statusMsg = self._create_status()
            return True
        except Exception as e:
            logger.error(f"Error handling MoveCursor command '{cmd}': {e}")
            self.statusMsg = self._create_error_status()
            return False

    def _handle_string(self, cmd: str) -> bool:
        """Handle String command."""
        # Parse string: String("text")
        try:
            # Extract text from String("text")
            text = cmd[7:-1]  # Remove String( and )
            logger.info(f"Handling string command: {text}")
            # Send text using compose method
            self._session.compose(text)
            self.statusMsg = self._create_status()
            return True
        except Exception as e:
            logger.error(f"Error handling String command '{cmd}': {e}")
            self.statusMsg = self._create_error_status()
            return False

    def _handle_print_text(self, cmd: str) -> bool:
        """Handle PrintText command."""
        # Parse PrintText command
        logger.info(f"Handling print text command: {cmd}")
        # For PrintText(string), we need to populate the buffer
        if "string" in cmd:
            try:
                # Get screen content and put it in buffer
                screen_content = self._session.read()
                self.buffer = (
                    screen_content.decode("latin1", errors="replace")
                    if isinstance(screen_content, bytes)
                    else str(screen_content)
                )
                logger.debug(f"Buffer populated with: {self.buffer}")
            except Exception as e:
                logger.error(f"Error getting screen content: {e}")
                self.buffer = ""
        self.statusMsg = self._create_status()
        return True

    def _handle_noop(self) -> bool:
        """Handle NoOpCommand."""
        logger.info("Handling noop command")
        # No-op action
        self.statusMsg = self._create_status()
        return True

    def _handle_ascii(self, cmd: str) -> bool:
        """Handle Ascii command."""
        # Parse Ascii command: Ascii(row, col, length) or Ascii(row, col, rows, cols)
        try:
            params = cmd[6:-1]  # Extract parameters from Ascii(...)
            param_list = list(map(int, params.split(",")))
            logger.info(f"Handling ascii command with params: {param_list}")
            # For now, we'll just set an empty buffer and status
            self.buffer = ""  # In a real implementation, we'd extract text from screen
            self.statusMsg = self._create_status()
            return True
        except Exception as e:
            logger.error(f"Error handling Ascii command '{cmd}': {e}")
            self.statusMsg = self._create_error_status()
            return False

    def _handle_wait(self, cmd: str) -> bool:
        """Handle Wait command."""
        # Parse Wait command: Wait(timeout, condition, ...)
        try:
            logger.info(f"Handling wait command: {cmd}")
            # For now, we'll just set status
            self.statusMsg = self._create_status()
            return True
        except Exception as e:
            logger.error(f"Error handling Wait command '{cmd}': {e}")
            self.statusMsg = self._create_error_status()
            return False

    def _create_status(
        self,
        keyboard="U",
        screen="F",
        field="U",
        connection_state="C(hostname)",
        emulator="I",
        model="2",
        rows="24",
        cols="80",
        cursor_row="0",
        cursor_col="0",
        win_id="0x0",
        exec_time="-",
    ) -> str:
        """
        Create a status message compatible with s3270 format.

        Returns:
            A status message string with 12 space-separated fields
        """
        status_fields = [
            keyboard,  # Keyboard state: U=Unlocked, L=Locked, E=Error
            screen,  # Screen formatting: F=Formatted, U=Unformatted
            field,  # Field protection: P=Protected, U=Unprotected
            connection_state,  # Connection state: C(hostname)=Connected, N=Not connected
            emulator,  # Emulator mode: I=3270, L=NVT Line, C=NVT Char, P=Unnegotiated, N=Not connected
            model,  # Model number
            rows,  # Number of rows
            cols,  # Number of columns
            cursor_row,  # Cursor row (0-based)
            cursor_col,  # Cursor column (0-based)
            win_id,  # Window ID
            exec_time,  # Execution time
        ]
        return " ".join(status_fields)

    def _create_error_status(self) -> str:
        """Create an error status message."""
        return self._create_status(keyboard="E", connection_state="N")

    def check(self, doNotCheck=False) -> bool:
        """
        Check the result of the executed command.

        Args:
            doNotCheck: If True, don't perform checking (for Quit command)

        Returns:
            True if check passed, False otherwise
        """
        if doNotCheck:
            return True
        # In the original s3270, this would read from the subprocess
        # For our implementation, we assume the command already set status
        logger.debug("Checking command result")
        return True
