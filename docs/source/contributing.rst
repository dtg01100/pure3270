Contributing to pure3270
========================

Development Setup
-----------------

1. Clone the repository:
   .. code-block:: bash

       git clone https://github.com/yourorg/pure3270.git
       cd pure3270

2. Create virtual environment:
   .. code-block:: bash

       python -m venv venv
       source venv/bin/activate  # On Windows: venv\\Scripts\\activate

3. Install development dependencies:
   .. code-block:: bash

       pip install -e .[dev]

4. Install pre-commit hooks:
   .. code-block:: bash

       pre-commit install

Coding Standards
----------------

- Follow PEP 8 style guidelines
- Use type hints for all public APIs
- Write comprehensive unit tests
- Document all public functions and classes

Testing
-------

Run tests with:
.. code-block:: bash

    pytest tests/

For property-based tests:
.. code-block:: bash

    pytest tests/ -m property

Static Analysis
---------------

- mypy: `mypy pure3270/ --strict`
- pylint: `pylint pure3270/`
- bandit: `bandit -r pure3270/`

Building Documentation
---------------------

.. code-block:: bash

    cd docs
    make html

The generated docs will be in `_build/html/`.

Reporting Issues
----------------

Please report bugs and feature requests on GitHub Issues with:
- Detailed description
- Steps to reproduce
- Environment details (Python version, OS)
- Relevant logs or error messages
