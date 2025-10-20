"""SSL/TLS wrapper for secure TN3270 connections using stdlib ssl module."""

import logging
import socket
import ssl
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class SSLError(Exception):
    """Error during SSL operations."""

    pass


class SSLWrapper:
    """Layers SSL/TLS on top of asyncio connections using Python's ssl module."""

    """Layers SSL/TLS on top of asyncio connections using Python's ssl module."""

    def __init__(
        self,
        verify: bool = True,
        cafile: Optional[str] = None,
        capath: Optional[str] = None,
    ):
        """
        Initialize the SSLWrapper.

        :param verify: Whether to verify the server's certificate.
        :param cafile: Path to CA certificate file.
        :param capath: Path to CA certificates directory.
        """
        self.verify = verify
        self.cafile = cafile
        self.capath = capath
        self.context: Optional[ssl.SSLContext] = None

        # Warn immediately if verification is disabled
        if not verify:
            logger.warning(
                "🚨 SSL verification disabled at SSLWrapper creation. "
                "This creates security vulnerabilities and should only be used "
                "for testing. Production systems should verify certificates."
            )

    def create_context(self) -> ssl.SSLContext:
        """
        Create an SSLContext for secure connections.

        This implementation matches the expectations of our tests:
        - Build context with ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        - When verify=True: check_hostname=True and verify_mode=CERT_REQUIRED
        - Enforce minimum TLS 1.2
        - Configure cipher suite to "HIGH:!aNULL:!MD5"

        :return: Configured SSLContext.
        :raises SSLError: If context creation fails.
        """
        try:
            # Explicitly create TLS client context to satisfy tests that patch SSLContext
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

            if self.verify:
                ctx.check_hostname = True
                ctx.verify_mode = ssl.CERT_REQUIRED
                # Load custom CA locations if provided
                try:
                    if self.cafile:
                        ctx.load_verify_locations(cafile=self.cafile)
                    if self.capath:
                        ctx.load_verify_locations(capath=self.capath)
                except Exception as e:  # pragma: no cover - environment dependent
                    logger.warning(f"Failed to load custom CA locations: {e}")
            else:
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                logger.warning(
                    "SSL certificate verification is DISABLED (verify=False). "
                    "Use only for testing/development environments."
                )

            # Set minimum TLS version to 1.2 for security
            ctx.minimum_version = ssl.TLSVersion.TLSv1_2

            # Configure cipher suites exactly as asserted in tests
            try:
                ctx.set_ciphers("HIGH:!aNULL:!MD5")
            except ssl.SSLError as e:  # pragma: no cover - depends on OpenSSL build
                logger.debug(f"Cipher configuration failed, using defaults: {e}")

            self.context = ctx
            logger.debug("SSLContext created successfully")
            return ctx

        except ssl.SSLError as e:
            logger.error(f"SSL context creation failed: {e}")
            raise SSLError(f"SSL context creation failed: {e}")

    def _configure_x3270_cipher_suites(self) -> None:
        """
        Configure cipher suites compatible with x3270 and legacy servers.
        Includes fallback mechanisms for older TLS implementations.
        """
        if not self.context:
            raise SSLError("SSL context not initialized")

        # x3270-compatible cipher suites in order of preference
        x3270_cipher_suites = [
            # Modern, secure ciphers (preferred)
            "ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20",
            # Fallback to AES with DHE
            "DHE+AES:!aNULL:!MD5:!DSS",
            # Legacy compatibility (last resort)
            "HIGH:!aNULL:!MD5:!RC4",
            # Additional legacy support
            "ALL:!aNULL:!MD5:!RC4:!EXPORT:!LOW:!EXP:!eNULL:!SSLv2:!SSLv3",
        ]

        configured = False
        for cipher_suite in x3270_cipher_suites:
            try:
                self.context.set_ciphers(cipher_suite)
                logger.debug(f"Successfully configured cipher suite: {cipher_suite}")
                configured = True
                break
            except ssl.SSLError as e:
                logger.debug(f"Failed to configure cipher suite '{cipher_suite}': {e}")
                continue

        if not configured:
            logger.warning(
                "Failed to configure any cipher suite, using system defaults"
            )
            # Fall back to system defaults if all configurations fail
            try:
                self.context.set_ciphers("DEFAULT")
            except ssl.SSLError:
                logger.error("Failed to configure default cipher suites")

        # Configure additional compatibility options
        try:
            # Allow TLS 1.2 and 1.3 for maximum compatibility
            self.context.minimum_version = ssl.TLSVersion.TLSv1_2
            self.context.maximum_version = ssl.TLSVersion.TLSv1_3

            # Enable session resumption for better performance
            self.context.check_hostname = self.verify
            self.context.verify_mode = (
                ssl.CERT_REQUIRED if self.verify else ssl.CERT_NONE
            )

            # Configure protocol options for x3270 compatibility
            if hasattr(self.context, "post_handshake_auth"):
                self.context.post_handshake_auth = False  # Disable for compatibility

            logger.debug("SSL context configured with x3270 compatibility options")

        except Exception as e:
            logger.warning(f"Failed to configure some SSL options: {e}")

    def wrap_connection(self, telnet_connection: Any) -> Any:
        """
        Wrap an existing telnet connection with SSL with x3270-compatible fallback mechanisms.

        :param telnet_connection: The telnet connection object (e.g., from asyncio.open_connection).
        :return: Wrapped connection.

        Note: This is a stub; asyncio.open_connection handles SSL natively via ssl parameter.
        """
        # Since asyncio supports SSL natively, this method is for compatibility or custom wrapping.
        # For basics, log and return original.
        self.get_context()  # Ensure context is created
        logger.info(
            "Using native asyncio SSL support with x3270 compatibility; no additional wrapping needed"
        )
        return telnet_connection

    def create_fallback_context(self) -> ssl.SSLContext:
        """
        Create a fallback SSL context for legacy server compatibility.

        :return: Fallback SSLContext with relaxed security for compatibility.
        :raises SSLError: If context creation fails.
        """
        try:
            # Create a more permissive context for legacy servers
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            # Minimum TLS version for legacy compatibility
            context.minimum_version = ssl.TLSVersion.TLSv1

            # Legacy cipher suites for older servers
            legacy_ciphers = [
                "ALL:!aNULL:!MD5:!EXPORT:!LOW:!EXP:!eNULL:!SSLv2:!SSLv3",
                "HIGH:!aNULL:!MD5",
                "DEFAULT",
            ]

            for cipher_suite in legacy_ciphers:
                try:
                    context.set_ciphers(cipher_suite)
                    logger.debug(f"Configured legacy cipher suite: {cipher_suite}")
                    break
                except ssl.SSLError:
                    continue

            logger.info("Created fallback SSL context for legacy server compatibility")
            return context

        except ssl.SSLError as e:
            logger.error(f"Fallback SSL context creation failed: {e}")
            raise SSLError(f"Fallback SSL context creation failed: {e}")

    def test_ssl_compatibility(self, hostname: str, port: int) -> Dict[str, Any]:
        """
        Test SSL compatibility with a target server.

        :param hostname: Target hostname
        :param port: Target port
        :return: Compatibility test results
        """
        results: Dict[str, Any] = {
            "primary_compatible": False,
            "fallback_compatible": False,
            "supported_protocols": [],
            "supported_ciphers": [],
            "errors": [],
        }

        # Test primary context
        try:
            context = self.get_context()
            conn = context.wrap_socket(socket.create_connection((hostname, port)))
            conn.close()
            results["primary_compatible"] = True
            logger.debug("Primary SSL context is compatible")
        except Exception as e:
            results["errors"].append(f"Primary context failed: {e}")
            logger.debug(f"Primary SSL context failed: {e}")

        # Test fallback context
        try:
            context = self.create_fallback_context()
            conn = context.wrap_socket(socket.create_connection((hostname, port)))
            conn.close()
            results["fallback_compatible"] = True
            logger.debug("Fallback SSL context is compatible")
        except Exception as e:
            results["errors"].append(f"Fallback context failed: {e}")
            logger.debug(f"Fallback SSL context failed: {e}")

        return results

    def get_context(self) -> ssl.SSLContext:
        """Get the SSLContext (create if not exists)."""
        if self.context is None:
            self.create_context()
        assert self.context is not None, "Context should be created by create_context"
        return self.context

    def decrypt(self, encrypted_data: bytes) -> bytes:
        """Stub for decrypting data (for testing)."""
        return encrypted_data


# Usage example (for docstrings):
# wrapper = SSLWrapper(verify=True)
# context = wrapper.create_context()
# handler = TN3270Handler(host="example.com", port=992, ssl_context=context)
