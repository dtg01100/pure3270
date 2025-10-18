pure3270.protocol Module
========================

.. automodule:: pure3270.protocol
    :members:
    :undoc-members:
    :show-inheritance:

IND$FILE Protocol
=================

The IND$FILE protocol provides file transfer capabilities for 3270 terminals. It allows uploading files from the client to the host and downloading files from the host to the client.

Overview
--------

IND$FILE uses structured fields (SF) with type 0xD0 to transfer files. The protocol supports:

- **Upload**: Send files from client to host
- **Download**: Receive files from host to client
- **Error handling**: Proper error reporting and recovery
- **State management**: Track transfer progress and handle concurrent transfers

Message Types
-------------

The IND$FILE protocol defines several message types:

- **IND_FILE_UPLOAD (0x00)**: Request to upload a file to the host
- **IND_FILE_DOWNLOAD (0x01)**: Request to download a file from the host
- **IND_FILE_DATA (0x02)**: File data payload
- **IND_FILE_EOF (0x03)**: End of file marker
- **IND_FILE_ERROR (0x04)**: Error message

Usage Example
-------------

.. code-block:: python

    import asyncio
    from pure3270 import AsyncSession

    async def file_transfer_example():
        # Connect to host
        session = AsyncSession("host.example.com", 23)
        await session.connect()

        # Upload a file
        await session.send_file("/local/path/file.txt", "remote_file.txt")

        # Download a file
        await session.receive_file("remote_file.txt", "/local/path/downloaded.txt")

        await session.close()

    # Run the example
    asyncio.run(file_transfer_example())

Implementation Details
----------------------

The IND$FILE implementation consists of several key components:

**IndFileMessage Class**
    Handles creation, serialization, and parsing of IND$FILE messages.

**IndFileTransfer Class**
    Manages the state of an ongoing file transfer, including file I/O and progress tracking.

**IndFile Class**
    Provides the main interface for file transfers, integrating with the session layer.

**Session Integration**
    The AsyncSession class provides ``send_file()`` and ``receive_file()`` methods that use IND$FILE under the hood.

Error Handling
--------------

IND$FILE includes comprehensive error handling:

- File not found errors
- Permission errors
- Network timeouts
- Protocol violations
- Transfer aborts

All errors are properly logged and can be caught as ``IndFileError`` exceptions.

Limitations
-----------

- Only supports binary file transfers
- Maximum file size depends on available memory
- No resume capability for interrupted transfers
- Host-initiated transfers are partially implemented
