# Local shim for test harness: provide a `p3270` module that wraps
# our internal `pure3270.p3270_client.P3270Client` implementation for
# faster local testing without relying on the external p3270 package.
from importlib import import_module

_p3270_client = import_module("pure3270.p3270_client")

# Provide both top-level exports and a module-like object `p3270` that
# mirrors the API shape of the real p3270 library, which some tests import
# as `from p3270 import p3270` and then use `p3270.P3270Client`, `p3270.Config`.
P3270Client = _p3270_client.P3270Client
Config = getattr(_p3270_client, "Config", None)


class _P3270Namespace:
    """Simple namespace to hold p3270 compatibility exports.

    Tests expect an import `from p3270 import p3270` and then access
    `p3270.P3270Client` and `p3270.Config` (module-like API). Expose the
    same interface pointing to our native implementation.
    """

    P3270Client = P3270Client
    Config = Config


# The module-level variable "p3270" matches consumer expectations
p3270 = _P3270Namespace()

__all__ = ["P3270Client", "Config", "p3270"]
