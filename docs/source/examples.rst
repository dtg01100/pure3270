Examples
========

This section provides practical examples of using Pure3270 in various scenarios.

Standalone Synchronous Session
------------------------------

.. code-block:: python

   from pure3270 import Session

   with Session() as session:
       session.connect('your-host.example.com', port=23, ssl_context=None)
       session.key('Enter')
       print(session.ascii(session.read()))

Standalone Asynchronous Session
-------------------------------

.. code-block:: python

   import asyncio
   from pure3270 import AsyncSession

   async def main():
       async with AsyncSession() as session:
           await session.connect('your-host.example.com', port=23, ssl_context=None)
           await session.key('Enter')
           print(session.ascii(await session.read()))

   asyncio.run(main())


Integration with p3270
----------------------

To replace ``p3270``'s ``s3270`` dependency with Pure3270:

1. Install ``p3270`` in your venv: ``pip install p3270``.
2. Enable patching before importing ``p3270``.

.. code-block:: python

   import pure3270
   pure3270.enable_replacement()  # Applies global patches to p3270

   import p3270
   session = p3270.P3270Client()  # Now uses pure3270 under the hood
   session.connect('your-host.example.com', port=23, ssl_context=None)
   session.key('Enter')
   screen_text = session.ascii(session.read())
   print(screen_text)
   session.close()

This redirects ``p3270.P3270Client`` methods (``__init__``, ``connect``, ``send``,
``read``) to pure3270 equivalents. Logs will indicate patching success.


Selecting a Terminal Model in Examples
--------------------------------------

You can pass ``terminal_type`` when creating sessions to emulate different IBM models.

.. code-block:: python

    from pure3270 import Session

    # Emulate a color 32x80 terminal (3279 Model 3)
    with Session(terminal_type="IBM-3279-3") as session:
       session.connect('your-host.example.com', port=23)
       print("Screen size:", session.screen_buffer.rows, "x", session.screen_buffer.cols)

File Transfer with IND$FILE
---------------------------

Pure3270 supports file transfer using the IND$FILE protocol, allowing you to upload files to and download files from the host.

.. code-block:: python

    import asyncio
    from pure3270 import AsyncSession

    async def file_transfer_example():
        async with AsyncSession() as session:
            await session.connect('your-host.example.com', port=23)

            # Upload a local file to the host
            await session.send_file('/local/path/source.txt', 'destination.txt')

            # Download a file from the host
            await session.receive_file('remote_file.txt', '/local/path/downloaded.txt')

            print("File transfer completed successfully")

    # Run the example
    asyncio.run(file_transfer_example())

Error Handling in File Transfers
--------------------------------

.. code-block:: python

    import asyncio
    from pure3270 import AsyncSession
    from pure3270.ind_file import IndFileError

    async def robust_file_transfer():
        async with AsyncSession() as session:
            await session.connect('your-host.example.com', port=23)

            try:
                # Attempt to upload a file
                await session.send_file('/local/path/missing.txt', 'remote.txt')
            except IndFileError as e:
                print(f"Upload failed: {e}")

            try:
                # Attempt to download a file
                await session.receive_file('nonexistent.txt', '/local/path/fail.txt')
            except IndFileError as e:
                print(f"Download failed: {e}")

    asyncio.run(robust_file_transfer())
