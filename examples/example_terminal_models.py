"""
Example: Iterate over supported terminal models and show screen dimensions
and capabilities reported by Pure3270.

Run:
    python examples/example_terminal_models.py

Note: This example does not connect to a real host; it demonstrates local
initialization, sizing, and capability reporting.
"""

import asyncio

import pure3270
from pure3270.protocol.utils import (
    DEFAULT_TERMINAL_MODEL,
    get_screen_size,
    get_supported_terminal_models,
)


async def main() -> None:
    models = get_supported_terminal_models()
    print(f"Found {len(models)} supported models (default: {DEFAULT_TERMINAL_MODEL})\n")

    # Limit output for brevity; show first 8 models
    for model in models[:8]:
        s = pure3270.AsyncSession(terminal_type=model)
        rows, cols = s.screen_buffer.rows, s.screen_buffer.cols
        expected_rows, expected_cols = get_screen_size(model)
        caps = s.capabilities()
        print(
            f"- {model:12} -> screen {rows}x{cols}"
            f" (expected {expected_rows}x{expected_cols})"
        )
        print(f"  caps: {caps}")

    # Show default behavior
    s_default = pure3270.AsyncSession()
    print(
        f"\nDefault session screen: {s_default.screen_buffer.rows}x{s_default.screen_buffer.cols} (model {DEFAULT_TERMINAL_MODEL})"
    )


if __name__ == "__main__":
    asyncio.run(main())
