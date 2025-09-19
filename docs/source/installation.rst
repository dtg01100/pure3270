Installation
============

Pure3270 requires Python 3.10 or later. It is recommended to use a virtual
environment for isolation.

Requirements
------------

* Python 3.10 or later
* No external runtime dependencies (uses only Python standard library)

Installation Methods
--------------------

Stable Release
~~~~~~~~~~~~~~

To install Pure3270, run this command in your terminal:

.. code-block:: console

   pip install pure3270

This is the preferred method to install Pure3270, as it will always install the
most recent stable release.

Development Version
~~~~~~~~~~~~~~~~~~~

If you'd like to install the latest development version, you can clone the
repository and install it in editable mode:

.. code-block:: console

   git clone https://github.com/dtg01100/pure3270.git
   cd pure3270
   python -m pip install -e .

Virtual Environment Installation
--------------------------------

It's recommended to use a virtual environment to avoid conflicts with other
Python packages:

.. code-block:: console

   python -m venv pure3270-env
   source pure3270-env/bin/activate  # On Windows: pure3270-env\Scripts\activate
   pip install pure3270

To deactivate the virtual environment when you're done:

.. code-block:: console

   deactivate

Quick Start
-----------

After installation, you can quickly test a basic connection:

.. code-block:: python

   from pure3270 import Session

   with Session() as session:
       session.connect('your-host.example.com', port=23, ssl_context=None)
       screen = session.read()
       print(session.ascii(screen))

For more examples, see the :doc:`examples` section.
