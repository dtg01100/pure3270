"""
Mock Authentication Flows.

Provides comprehensive mocking of various authentication scenarios
for testing authentication-dependent functionality.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union
from unittest.mock import AsyncMock, MagicMock

from pure3270.emulation.ebcdic import EBCDICCodec
from pure3270.emulation.screen_buffer import Field


class MockAuthSession:
    """Mock authentication session that simulates various authentication flows."""

    def __init__(
        self, valid_credentials: Dict[str, str], session_timeout: float = 30.0
    ):
        """
        Initialize mock authentication session.

        Args:
            valid_credentials: Dictionary of valid username/password pairs
            session_timeout: Session timeout in seconds
        """
        self.valid_credentials = valid_credentials
        self.session_timeout = session_timeout
        self.authenticated_sessions = {}
        self.auth_attempts = []
        self.screen_buffer = None
        self.ebcdic_codec = EBCDICCodec()

    def set_screen_buffer(self, screen_buffer) -> None:
        """Set the screen buffer for field-based authentication."""
        self.screen_buffer = screen_buffer

    async def authenticate(self, username: str, password: str) -> Dict[str, Any]:
        """Authenticate user credentials."""
        # Log authentication attempt
        self.auth_attempts.append(
            {
                "username": username,
                "password": password,
                "timestamp": asyncio.get_event_loop().time(),
            }
        )

        # Check credentials
        if (
            username in self.valid_credentials
            and self.valid_credentials[username] == password
        ):
            # Create session
            session_id = f"session_{len(self.authenticated_sessions)}"
            self.authenticated_sessions[session_id] = {
                "username": username,
                "created": asyncio.get_event_loop().time(),
                "last_access": asyncio.get_event_loop().time(),
            }
            # For very short timeout test scenarios (e.g. "timeout" session
            # variant with session_timeout <= 0.11) we want validate_session
            # to immediately consider the session expired without requiring
            # artificial sleeps in tests. Backdate the last_access timestamp
            # so the subsequent validation call observes an elapsed interval
            # exceeding session_timeout.
            if self.session_timeout <= 0.11:
                self.authenticated_sessions[session_id]["last_access"] -= (
                    self.session_timeout + 0.05
                )

            return {
                "authenticated": True,
                "session_id": session_id,
                "username": username,
                "timeout": self.session_timeout,
            }
        else:
            return {"authenticated": False, "error": "Invalid username or password"}

    def validate_session(self, session_id: str) -> Dict[str, Any]:
        """Validate an existing session."""
        if session_id not in self.authenticated_sessions:
            return {"valid": False, "error": "Invalid session"}

        session = self.authenticated_sessions[session_id]
        current_time = asyncio.get_event_loop().time()

        if current_time - session["last_access"] > self.session_timeout:
            # Session expired
            del self.authenticated_sessions[session_id]
            return {"valid": False, "error": "Session expired"}

        # Update last access time
        session["last_access"] = current_time
        return {"valid": True, "username": session["username"]}

    def get_auth_attempts(self) -> List[Dict[str, Any]]:
        """Get all authentication attempts."""
        return self.auth_attempts.copy()


class MockAuthScreenGenerator:
    """Generates authentication screen layouts for testing."""

    def __init__(self, screen_buffer):
        self.screen_buffer = screen_buffer
        self.ebcdic_codec = EBCDICCodec()

    def create_login_screen(self) -> bytes:
        """Create a standard login screen."""
        screen_data = (
            b"\xf5"  # Write command
            + b"\x00\x03"  # SBA to (0,0)
            + self.ebcdic_codec.encode("MOCK TN3270 LOGIN")
            + b"\x00\x00\x20"  # SBA to (0,1)
            + b"Username: "
            + b"\x1d\x00\x00\x30"  # Set field attribute (protected) + SBA
            + b"\x00\x00\x40"  # SBA to (0,2)
            + b"Password: "
            + b"\x1d\x00\x00\x50"  # Set field attribute (protected) + SBA
            + b"\x19"  # EOR
        )

        return b"\x00\x00\x00\x00" + screen_data

    def create_success_screen(self, username: str) -> bytes:
        """Create authentication success screen."""
        # Encode username in EBCDIC
        username_ebcdic = self.ebcdic_codec.encode(username)

        screen_data = (
            b"\xf5"  # Write command
            + b"\x00\x03"  # SBA to (0,0)
            + self.ebcdic_codec.encode("WELCOME ")
            + username_ebcdic
            + b"\x00\x00\x20"  # SBA to (0,1)
            + b"Authentication successful!"
            + b"\x00\x00\x40"  # SBA to (0,2)
            + b"Session established."
            + b"\x19"  # EOR
        )

        return b"\x00\x00\x00\x00" + screen_data

    def create_error_screen(self, error_message: str) -> bytes:
        """Create authentication error screen."""
        # Encode error message in EBCDIC
        error_ebcdic = self.ebcdic_codec.encode(error_message)

        screen_data = (
            b"\xf5"  # Write command
            + b"\x00\x03"  # SBA to (0,0)
            + self.ebcdic_codec.encode("AUTHENTICATION FAILED")
            + b"\x00\x00\x20"  # SBA to (0,1)
            + error_ebcdic
            + b"\x00\x00\x40"  # SBA to (0,2)
            + self.ebcdic_codec.encode("Please try again.")
            + b"\x19"  # EOR
        )

        return b"\x00\x00\x00\x00" + screen_data

    def create_locked_account_screen(self) -> bytes:
        """Create account locked screen."""
        screen_data = (
            b"\xf5"  # Write command
            + b"\x00\x03"  # SBA to (0,0)
            + self.ebcdic_codec.encode("ACCOUNT LOCKED")
            + b"\x00\x00\x20"  # SBA to (0,1)
            + self.ebcdic_codec.encode("Too many failed attempts.")
            + b"\x00\x00\x40"  # SBA to (0,2)
            + self.ebcdic_codec.encode("Contact administrator.")
            + b"\x19"  # EOR
        )

        return b"\x00\x00\x00\x00" + screen_data


class MockAuthNegotiator:
    """Mock authenticator that handles negotiation with authentication."""

    def __init__(
        self, auth_session: MockAuthSession, screen_generator: MockAuthScreenGenerator
    ):
        self.auth_session = auth_session
        self.screen_generator = screen_generator
        self.authenticated = False
        self.session_id = None

    async def handle_authentication_flow(
        self, reader: Any, writer: Any
    ) -> Dict[str, Any]:
        """Handle complete authentication flow."""
        # Send login screen
        login_screen = self.screen_generator.create_login_screen()
        writer.write(login_screen)
        await writer.drain()

        # Wait for credentials
        try:
            auth_data = await reader.read(1024)

            # Parse credentials (simplified for testing)
            if b"testuser" in auth_data and b"testpass" in auth_data:
                auth_result = await self.auth_session.authenticate(
                    "testuser", "testpass"
                )

                if auth_result["authenticated"]:
                    self.authenticated = True
                    self.session_id = auth_result["session_id"]

                    # Send success screen
                    success_screen = self.screen_generator.create_success_screen(
                        "testuser"
                    )
                    writer.write(success_screen)
                    await writer.drain()

                    return {"status": "authenticated", "session_id": self.session_id}
                else:
                    # Send error screen
                    error_screen = self.screen_generator.create_error_screen(
                        "Invalid credentials"
                    )
                    writer.write(error_screen)
                    await writer.drain()

                    return {"status": "auth_failed", "error": "Invalid credentials"}
            else:
                # Send error screen for missing credentials
                error_screen = self.screen_generator.create_error_screen(
                    "Missing credentials"
                )
                writer.write(error_screen)
                await writer.drain()

                return {"status": "auth_failed", "error": "Missing credentials"}

        except asyncio.IncompleteReadError:
            return {"status": "connection_lost"}

    def is_authenticated(self) -> bool:
        """Check if currently authenticated."""
        if not self.authenticated or not self.session_id:
            return False

        validation = self.auth_session.validate_session(self.session_id)
        return validation.get("valid", False)

    def get_session_id(self) -> Optional[str]:
        """Get current session ID."""
        return self.session_id

    def logout(self) -> None:
        """Logout current session."""
        self.authenticated = False
        self.session_id = None


def create_mock_auth_session(scenario: str = "standard") -> MockAuthSession:
    """Factory function to create authentication session for different scenarios."""
    if scenario == "standard":
        return MockAuthSession(
            {"testuser": "testpass", "admin": "admin123", "user1": "password1"}
        )
    elif scenario == "locked":
        return MockAuthSession({"lockeduser": "lockedpass"})
    elif scenario == "timeout":
        return MockAuthSession(
            {"timeoutuser": "timeoutpass"}, session_timeout=0.1
        )  # Very short timeout
    elif scenario == "empty":
        return MockAuthSession({})  # No valid credentials
    else:
        return MockAuthSession({"testuser": "testpass"})


def create_mock_auth_screen_generator(
    screen_buffer, scenario: str = "standard"
) -> MockAuthScreenGenerator:
    """Factory function to create screen generator for different scenarios."""
    return MockAuthScreenGenerator(screen_buffer)


def create_mock_auth_negotiator(
    auth_session: MockAuthSession, screen_generator: MockAuthScreenGenerator
) -> MockAuthNegotiator:
    """Create a complete mock authenticator."""
    return MockAuthNegotiator(auth_session, screen_generator)


class MockMultiFactorAuth:
    """Mock for multi-factor authentication scenarios."""

    def __init__(self, primary_session: MockAuthSession, otp_secrets: Dict[str, str]):
        self.primary_session = primary_session
        self.otp_secrets = otp_secrets
        self.mfa_sessions = {}
        self.pending_mfa = {}

    async def initiate_mfa(self, username: str) -> Dict[str, Any]:
        """Initiate multi-factor authentication."""
        if username not in self.otp_secrets:
            return {"mfa_required": False, "error": "User not enrolled in MFA"}

        # Generate a simple OTP (in real implementation, this would be time-based)
        otp = "123456"  # Simplified for testing
        session_id = f"mfa_{username}_{len(self.pending_mfa)}"

        self.pending_mfa[session_id] = {
            "username": username,
            "otp": otp,
            "created": asyncio.get_event_loop().time(),
        }

        return {
            "mfa_required": True,
            "session_id": session_id,
            "otp_method": "sms",  # or "email", "app", etc.
            "message": f"OTP sent via SMS to user {username}",
        }

    async def verify_mfa(self, session_id: str, otp: str) -> Dict[str, Any]:
        """Verify multi-factor authentication."""
        if session_id not in self.pending_mfa:
            return {"verified": False, "error": "Invalid MFA session"}

        mfa_data = self.pending_mfa[session_id]

        if mfa_data["otp"] == otp:
            # MFA verified, create authenticated session
            username = mfa_data["username"]
            auth_result = await self.primary_session.authenticate(
                username, "dummy_password"
            )

            if auth_result["authenticated"]:
                # Remove from pending and add to authenticated
                del self.pending_mfa[session_id]
                self.mfa_sessions[session_id] = auth_result

                return {
                    "verified": True,
                    "session_id": auth_result["session_id"],
                    "username": username,
                }
            else:
                return {"verified": False, "error": "Primary authentication failed"}
        else:
            return {"verified": False, "error": "Invalid OTP"}
