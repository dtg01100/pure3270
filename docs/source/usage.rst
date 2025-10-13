Usage
=====

Pure3270 can be used in two main ways: as a standalone library or as a replacement
for the ``s3270`` binary in ``p3270`` applications.

For detailed examples of standalone usage (synchronous, asynchronous) and integration with p3270, see the :doc:`examples` section.

Selecting a Terminal Model
--------------------------

You can choose the terminal type presented to the host by passing the
``terminal_type`` parameter to ``Session`` or ``AsyncSession``. This controls
screen dimensions and capability reporting during negotiation.

.. code-block:: python

   from pure3270 import Session

	# 27x132 wide screen
   with Session(terminal_type="IBM-3278-5") as s:
	   s.connect('your-host.example.com', port=23)
	   print(s.screen_buffer.rows, s.screen_buffer.cols)

See :doc:`terminal_models` for the full list of supported terminal types and details.
