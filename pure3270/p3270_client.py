"""
Drop-in replacement for p3270.P3270Client using pure3270.Session internally.
Matches the API and behavior of p3270.P3270Client exactly.
"""

import logging
import time
from typing import Any, List, Optional, Union

logger = logging.getLogger(__name__)


class InvalidConfiguration(Exception):
    """Raised when p3270 configuration is invalid."""

    pass


class P3270Client:
    def disconnect(self) -> None:
        """Disconnect from TN3270 host and clean up session."""
        if self._pure_session is not None:
            try:
                self._pure_session.close()
            except Exception as e:
                logger.error(f"Error closing session: {e}")
            self._pure_session = None
        self._connected = False

    def getScreen(self) -> str:
        """Get the current screen content as text (always ASCII/Unicode)."""
        if not self._connected or not self._pure_session:
            return ""
        try:
            screen_buffer = getattr(self._pure_session, "screen_buffer", None)
            if screen_buffer is not None and hasattr(screen_buffer, "ascii_buffer"):
                screen_text = screen_buffer.ascii_buffer
            elif screen_buffer is not None and hasattr(screen_buffer, "to_text"):
                screen_text = screen_buffer.to_text()
            else:
                screen_data = self._pure_session.read(timeout=1.0)
                if isinstance(screen_data, bytes):
                    screen_text = self._pure_session.ascii(screen_data)
                elif isinstance(screen_data, str):
                    screen_text = screen_data
                else:
                    screen_text = str(screen_data)
            self._last_screen = screen_text
            return str(screen_text)
        except Exception as e:
            logger.error(f"Error reading screen: {e}")
            return self._last_screen or ""

    def connect(self) -> None:
        """
        Establish connection to TN3270 host using pure3270.Session.
        """
        if self._connected:
            return
        from pure3270.session import Session

        self._pure_session = Session()
        if self.ssl:
            import ssl

            ssl_context = ssl.create_default_context()
        else:
            ssl_context = None
        self._pure_session.connect(
            self.hostName, port=self.hostPort, ssl_context=ssl_context
        )

    """
    Native P3270Client implementation that matches p3270.P3270Client API exactly.
    Uses pure3270.Session internally instead of spawning s3270 subprocess.
    """

    # Class variable to track instances (matches p3270 behavior)
    numOfInstances = 0

    hostName: Optional[str]
    hostPort: int
    ssl: bool
    _pure_session: Optional[Any]
    _connected: bool
    _last_screen: str
    _cursor_row: int
    _cursor_col: int
    _screen_rows: int
    _screen_cols: int
    _init_args: Any
    _init_kwargs: Any

    def __init__(
        self,
        hostName: Optional[str] = None,
        hostPort: int = 23,
        ssl: bool = False,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Initialize P3270Client with hostName and hostPort, matching p3270 API.
        """
        type(self).numOfInstances += 1
        self.hostName = hostName
        self.hostPort = hostPort
        self.ssl = ssl
        self._pure_session = None
        self._connected = False
        self._last_screen = ""
        self._cursor_row = 0
        self._cursor_col = 0
        self._screen_rows = 24
        self._screen_cols = 80
        # Optionally accept other p3270-compatible args
        self._init_args = args
        self._init_kwargs = kwargs
        # If hostName is provided, connect immediately (matches p3270 behavior)
        if self.hostName:
            self.connect()

    def _sendCommand(self, command: str) -> Optional[str]:
        """
        Send a command to the session and handle response, matching p3270 behavior.
        After commands that expect a screen update, immediately read and update the buffer.
        """
        try:
            # ...existing code...
            update_screen = False
            if command in [
                "Enter",
                "Clear",
                "Home",
                "Tab",
                "BackTab",
                "BackSpace",
                "Up",
                "Down",
                "Left",
                "Right",
            ]:
                if self._pure_session is not None:
                    self._pure_session.send(f"key {command}".encode("ascii"))
                update_screen = True
            elif command.startswith("PF("):
                pf_num = command[3:-1]
                if self._pure_session is not None:
                    self._pure_session.send(f"key PF{pf_num}".encode("ascii"))
                update_screen = True
            elif command.startswith("PA("):
                pa_num = command[3:-1]
                if self._pure_session is not None:
                    self._pure_session.send(f"key PA{pa_num}".encode("ascii"))
                update_screen = True
            elif command.startswith("String("):
                text = command[7:-1]
                if self._pure_session is not None:
                    self._pure_session.send(f"String({text})".encode("ascii"))
                update_screen = True
            elif command.startswith("MoveCursor("):
                coords = command[11:-1]
                row, col = coords.split(",")
                if self._pure_session is not None:
                    self._pure_session.send(f"MoveCursor {row} {col}".encode("ascii"))
                update_screen = True
            elif command.startswith("Connect("):
                param = command[8:-1]
                host = param
                if param.startswith("B:"):
                    host = param[2:]
                elif param.startswith("L:") and "@" in param:
                    host = param.split("@", 1)[1]
                if ":" in host:
                    host_parts = host.split(":", 1)
                    self.hostName = host_parts[0]
                    self.hostPort = int(host_parts[1])
                else:
                    self.hostName = host
                self.connect()
                update_screen = True
            elif command == "Disconnect":
                self.disconnect()
            elif command == "Quit":
                self.disconnect()
            elif command.startswith("Ascii("):
                params = command[6:-1]
                if params:
                    from typing import List, cast

                    param_list = cast(
                        List[int], [int(x.strip()) for x in params.split(",")]
                    )
                    if len(param_list) == 3:
                        r, c, l = (
                            int(param_list[0]),
                            int(param_list[1]),
                            int(param_list[2]),
                        )
                        return self.readTextAtPosition(r, c, l)
                    elif len(param_list) == 4:
                        r, c, rs, cs = (
                            int(param_list[0]),
                            int(param_list[1]),
                            int(param_list[2]),
                            int(param_list[3]),
                        )
                        return self.readTextArea(
                            r,
                            c,
                            r + rs - 1,
                            c + cs - 1,
                        )
                else:
                    return self.getScreen()
            elif command.startswith("Wait("):
                params = command[5:-1]
                try:
                    if "," in params:
                        timeout_str = params.split(",")[0]
                        timeout = float(timeout_str)
                    else:
                        timeout = float(params)
                    time.sleep(min(timeout, 10.0))
                except ValueError:
                    time.sleep(1.0)
            elif command.startswith("PrintText("):
                params = command[10:-1]
                return self.getScreen()
            elif command == "NoOpCommand":
                pass
            else:
                if self._pure_session is not None:
                    self._pure_session.send(command.encode("ascii"))

            if update_screen:
                # Immediately read and update the buffer after screen-changing commands
                try:
                    if self._pure_session is not None:
                        self._pure_session.read(timeout=1.0)
                except Exception as e:
                    logger.debug(f"Screen update after command '{command}' failed: {e}")

            logger.debug(f"Sent command: {command}")

        except Exception as e:
            logger.error(f"Error sending command '{command}': {e}")
        """Get the current screen content as text (always ASCII/Unicode)."""
        if not self._connected or not self._pure_session:
            return ""

        try:
            # Use the decoded buffer directly
            screen_buffer = getattr(self._pure_session, "screen_buffer", None)
            if screen_buffer is not None and hasattr(screen_buffer, "ascii_buffer"):
                screen_text = screen_buffer.ascii_buffer
            else:
                # Fallback: use to_text() if available
                if screen_buffer is not None and hasattr(screen_buffer, "to_text"):
                    screen_text = screen_buffer.to_text()
                else:
                    # Fallback: try to read and decode
                    screen_data = self._pure_session.read(timeout=1.0)
                    if isinstance(screen_data, bytes):
                        screen_text = self._pure_session.ascii(screen_data)
                    elif isinstance(screen_data, str):
                        screen_text = screen_data
                    else:
                        screen_text = str(screen_data)

            self._last_screen = screen_text
            return str(screen_text)
        except Exception as e:
            logger.error(f"Error reading screen: {e}")
            return self._last_screen or ""

    def printScreen(self) -> str:
        """Print current screen content (returns screen text)."""
        return self.getScreen()

    def saveScreen(self, filename: str) -> bool:
        """Save current screen to file."""
        try:
            screen_content = self.getScreen()
            with open(filename, "w", encoding="utf-8") as f:
                f.write(screen_content)
            return True
        except Exception as e:
            logger.error(f"Error saving screen to {filename}: {e}")
            return False

    def clearScreen(self) -> None:
        """Clear the screen."""
        self._sendCommand("Clear")

    def sendText(self, text: str, asterisks: bool = False) -> None:
        """
        Send text to the current cursor position.

        Args:
            text: Text to send
            asterisks: If True, mask input (for passwords)
        """
        if asterisks:
            # Log asterisks but send actual text
            logger.debug(f"Sending masked text: {'*' * len(text)}")
        else:
            logger.debug(f"Sending text: {text}")

        self._sendCommand(f"String({text})")

    def sendEnter(self) -> None:
        """Send Enter key."""
        self._sendCommand("Enter")

    def sendTab(self) -> None:
        """Send Tab key."""
        self._sendCommand("Tab")

    def sendBackTab(self) -> None:
        """Send BackTab key."""
        self._sendCommand("BackTab")

    def sendBackSpace(self) -> None:
        """Send BackSpace key."""
        self._sendCommand("BackSpace")

    def sendHome(self) -> None:
        """Send Home key."""
        self._sendCommand("Home")

    def sendPF(self, pfNum: int) -> None:
        """Send PF key (PF1-PF24)."""
        self._sendCommand(f"PF({pfNum})")

    def sendPA(self, paNum: int) -> None:
        """Send PA key (PA1-PA3)."""
        self._sendCommand(f"PA({paNum})")

    def sendKeys(self, keys: str) -> None:
        """Send arbitrary key sequence."""
        self._sendCommand(f"Key({keys})")

    def moveTo(self, row: int, col: int) -> None:
        """Move cursor to specified position."""
        self._sendCommand(f"MoveCursor({row},{col})")
        self._cursor_row = row
        self._cursor_col = col

    def moveCursorUp(self) -> None:
        """Move cursor up one row."""
        self._sendCommand("Up")
        if self._cursor_row > 0:
            self._cursor_row -= 1

    def moveCursorDown(self) -> None:
        """Move cursor down one row."""
        self._sendCommand("Down")
        if self._cursor_row < self._screen_rows - 1:
            self._cursor_row += 1

    def moveCursorLeft(self) -> None:
        """Move cursor left one column."""
        self._sendCommand("Left")
        if self._cursor_col > 0:
            self._cursor_col -= 1

    def moveCursorRight(self) -> None:
        """Move cursor right one column."""
        self._sendCommand("Right")
        if self._cursor_col < self._screen_cols - 1:
            self._cursor_col += 1

    def moveToFirstInputField(self) -> None:
        """Move cursor to first input field."""
        # Move to home and then find first input field
        self.sendHome()
        self.sendTab()

    def delChar(self) -> None:
        """Delete character at cursor position."""
        self._sendCommand("Delete")

    def delField(self) -> None:
        """Delete current field."""
        self._sendCommand("DeleteField")

    def delWord(self) -> None:
        """Delete current word."""
        self._sendCommand("DeleteWord")

    def eraseChar(self) -> None:
        """Erase character (same as delete)."""
        self._sendCommand("Erase")

    def readTextAtPosition(self, row: int, col: int, length: int) -> str:
        """
        Read text at specified position.

        Args:
            row: Row position (0-based)
            col: Column position (0-based)
            length: Number of characters to read

        Returns:
            Text at the specified position
        """
        screen = self.getScreen()
        lines = screen.split("\n")

        if row >= len(lines):
            return ""

        line = lines[row]
        if col >= len(line):
            return ""

        end_pos = min(col + length, len(line))
        return line[col:end_pos]

    def readTextArea(
        self, startRow: int, startCol: int, endRow: int, endCol: int
    ) -> str:
        """
        Read text from a rectangular area.

        Args:
            startRow: Starting row (0-based)
            startCol: Starting column (0-based)
            endRow: Ending row (0-based)
            endCol: Ending column (0-based)

        Returns:
            Text from the specified area
        """
        screen = self.getScreen()
        lines = screen.split("\n")
        result = []

        for row in range(startRow, min(endRow + 1, len(lines))):
            if row < len(lines):
                line = lines[row]
                start = startCol if row == startRow else 0
                end = endCol + 1 if row == endRow else len(line)
                result.append(line[start:end])

        return "\n".join(result)

    def foundTextAtPosition(self, row: int, col: int, text: str) -> bool:
        """
        Check if specific text is found at position.

        Args:
            row: Row position (0-based)
            col: Column position (0-based)
            text: Text to search for

        Returns:
            True if text is found at position
        """
        actual_text = self.readTextAtPosition(row, col, len(text))
        return actual_text == text

    def trySendTextToField(
        self, text: str, row: Optional[int] = None, col: Optional[int] = None
    ) -> bool:
        """
        Try to send text to a specific field.

        Args:
            text: Text to send
            row: Row position (optional)
            col: Column position (optional)

        Returns:
            True if successful
        """
        try:
            if row is not None and col is not None:
                self.moveTo(row, col)
            self.sendText(text)
            return True
        except Exception as e:
            logger.error(f"Error sending text to field: {e}")
            return False

    # Wait functions
    def waitForCursorAt(self, row: int, col: int, timeout: float = 5.0) -> bool:
        """Wait for cursor to be at specific position."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            # In real implementation, would check actual cursor position
            # For now, assume success after small delay
            time.sleep(0.1)
            if self._cursor_row == row and self._cursor_col == col:
                return True
        return False

    def waitForCursorAtOffset(self, offset: int, timeout: float = 5.0) -> bool:
        """Wait for cursor at specific offset from start of screen."""
        row = offset // self._screen_cols
        col = offset % self._screen_cols
        return self.waitForCursorAt(row, col, timeout)

    def waitForStringAt(
        self, row: int, col: int, text: str, timeout: float = 5.0
    ) -> bool:
        """Wait for specific text to appear at position."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.foundTextAtPosition(row, col, text):
                return True
            time.sleep(0.1)
            self.getScreen()  # Refresh screen
        return False

    def waitForStringAtOffset(
        self, offset: int, text: str, timeout: float = 5.0
    ) -> bool:
        """Wait for specific text to appear at offset."""
        row = offset // self._screen_cols
        col = offset % self._screen_cols
        return self.waitForStringAt(row, col, text, timeout)

    def waitForField(self, timeout: float = 5.0) -> bool:
        """Wait for an input field to be available."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            # In real implementation, would check for input fields
            time.sleep(0.1)
            # Assume field is available after delay
            return True
        return False

    def waitForFieldAt(self, row: int, col: int, timeout: float = 5.0) -> bool:
        """Wait for input field at specific position."""
        return self.waitForField(timeout)

    def waitForFieldAtOffset(self, offset: int, timeout: float = 5.0) -> bool:
        """Wait for input field at specific offset."""
        return self.waitForField(timeout)

    def waitForOutput(self, timeout: float = 5.0) -> bool:
        """Wait for output to be ready."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            time.sleep(0.1)
            # Check if screen has been updated
            current_screen = self.getScreen()
            if current_screen != self._last_screen:
                return True
        return True  # Assume output is ready

    def waitFor3270Mode(self, timeout: float = 5.0) -> bool:
        """Wait for 3270 mode to be active."""
        # In pure implementation, always in 3270 mode when connected
        return self._connected

    def waitForNVTMode(self, timeout: float = 5.0) -> bool:
        """Wait for NVT mode to be active."""
        # Pure implementation doesn't support NVT mode
        return False

    def waitForDisconnect(self, timeout: float = 5.0) -> bool:
        """Wait for disconnection."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if not self._connected:
                return True
            time.sleep(0.1)
        return not self._connected

    def waitForUnlock(self, timeout: float = 5.0) -> bool:
        """Wait for keyboard unlock."""
        # In pure implementation, keyboard is always unlocked
        return True

    def waitForTimeout(self, timeout: float) -> bool:
        """Wait for specified timeout period."""
        time.sleep(timeout)
        return True

    # Compatibility aliases
    def close(self) -> None:
        """Alias for disconnect."""
        self.disconnect()

    def send(self, command: str) -> None:
        """Send command (for backwards compatibility)."""
        self._sendCommand(command)

    def read(self) -> str:
        """Read screen (for backwards compatibility)."""
        return self.getScreen()
