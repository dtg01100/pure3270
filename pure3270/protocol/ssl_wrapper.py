"""SSL/TLS wrapper for secure TN3270 connections using stdlib ssl module."""

import logging
import ssl
from typing import Any, Optional

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

        :return: Configured SSLContext.
        :raises SSLError: If context creation fails.
        """
        try:
            # Create default SSL context for TLS client
            self.context = ssl.create_default_context()

            # Override verification if disabled
            if not self.verify:
                self.context.check_hostname = False
                self.context.verify_mode = ssl.CERT_NONE
                logger.warning(
                    "🚨 SECURITY WARNING: SSL certificate verification is DISABLED! "
                    "This makes the connection vulnerable to man-in-the-middle attacks. "
                    "Only use verify=False for testing/development environments. "
                    "Production deployments should ALWAYS verify certificates."
                )
                logger.warning(
                    "🔔 DEPRECATION NOTICE: The verify=False option will be deprecated "
                    "in a future version. Consider using proper certificate validation "
                    "or configuring custom CA certificates."
                )
            else:
                if self.cafile:
                    self.context.load_verify_locations(cafile=self.cafile)
                if self.capath:
                    self.context.load_verify_locations(capath=self.capath)

            # Set minimum TLS version to 1.2
            self.context.minimum_version = ssl.TLSVersion.TLSv1_2

            # Enable cipher suites for compatibility
            self.context.set_ciphers("HIGH:!aNULL:!MD5")

            logger.debug("SSLContext created successfully")
            return self.context

        except ssl.SSLError as e:
            logger.error(f"SSL context creation failed: {e}")
            raise SSLError(f"SSL context creation failed: {e}")

    def wrap_connection(self, telnet_connection: Any) -> Any:
        """
        Wrap an existing telnet connection with SSL (if asyncio doesn't handle natively).

        :param telnet_connection: The telnet connection object (e.g., from asyncio.open_connection).
        :return: Wrapped connection.

        Note: This is a stub; asyncio.open_connection handles SSL natively via ssl parameter.
        """
        # Since asyncio supports SSL natively, this method is for compatibility or custom wrapping.
        # For basics, log and return original.
        self.get_context()  # Ensure context is created
        logger.info("Using native asyncio SSL support; no additional wrapping needed")
        return telnet_connection

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
