Configurable Terminal Models
============================

Pure3270 supports multiple IBM 3270 terminal models and lets you choose which
terminal type to present to the host during Telnet/TN3270(E) negotiation.
This affects screen dimensions, color capabilities, and negotiation responses
(TTYPE and NEW-ENVIRON TERM).

Overview
--------

- Default model: ``IBM-3278-2`` (24x80, monochrome) for broad compatibility
- Configurable via the ``terminal_type`` parameter on ``Session`` and
  ``AsyncSession``
- Screen buffer is initialized to the correct rows/columns for the chosen model
- NAWS/USABLE-AREA negotiation and capability reporting reflect the chosen size

Supported Models
----------------

The following terminal models are supported by the built-in registry:

- IBM-3278-2 (24x80)
- IBM-3278-3 (32x80)
- IBM-3278-4 (43x80)
- IBM-3278-5 (27x132)
- IBM-3279-2 (24x80, color)
- IBM-3279-3 (32x80, color)
- IBM-3279-4 (43x80, color)
- IBM-3279-5 (27x132, color)
- IBM-3179-2 (24x80, color)
- IBM-3270PC-G (24x80, color)
- IBM-3270PC-GA (24x80, color)
- IBM-3270PC-GX (24x80, color)
- IBM-DYNAMIC (negotiated)

To programmatically discover available models or their attributes, see
``pure3270.protocol.utils`` helpers like ``get_supported_terminal_models()``
and ``get_screen_size(model)``.

Usage Examples
--------------

Synchronous usage:

.. code-block:: python

   from pure3270 import Session

   # Use a wide 132-column model
   with Session(terminal_type="IBM-3278-5") as s:
       s.connect('host.example.com', port=23)
       # Screen buffer is 27x132 for this model
       rows = s.screen_buffer.rows
       cols = s.screen_buffer.cols
       print(f"Screen size: {rows}x{cols}")

Asynchronous usage:

.. code-block:: python

   import asyncio
   from pure3270 import AsyncSession

   async def main():
       async with AsyncSession(terminal_type="IBM-3279-3") as s:
           await s.connect('host.example.com', port=23)
           caps = await s.capabilities()
           print("Capabilities:", caps)

   asyncio.run(main())

Notes
-----

- If an invalid ``terminal_type`` is provided, a ``ValueError`` is raised with
  the list of valid options.
- If omitted, the default is used (``IBM-3278-2``).
- TTYPE (Terminal-Type) and NEW-ENVIRON TERM responses reflect the configured
  terminal type during negotiation.
