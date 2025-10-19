# Pure3270 Development Guide for AI Agents

## Build/Lint/Test Commands

### Essential Commands
- **Quick smoke test**: `python quick_test.py` (0.07s)
- **Run all tests**: `python run_all_tests.py` (0.6s)
- **Single test**: `python -m pytest tests/test_file.py::test_function -v`
- **Format code**: `python -m black pure3270/`
- **Lint code**: `python -m flake8 pure3270/`
- **Type check**: `python -m mypy pure3270/`
- **Pre-commit**: `pre-commit run --all-files`

### Installation
- **Install package**: `pip install -e .` (3s)
- **Dev dependencies**: `pip install -e .[test]` (may timeout due to network)

## Code Style Guidelines

### Formatting & Imports
- **Line length**: 88 characters (Black), 127 for flake8
- **Import style**: isort with black profile, group imports: stdlib, third-party, local
- **Formatting**: Black formatter required before commits
- **No trailing whitespace** or missing newlines

### Type System
- **Strict typing**: mypy strict mode enabled for pure3270/
- **Type hints required**: All function signatures and variables
- **Python 3.10+**: Use modern typing (Union types with |, etc.)

### Naming Conventions
- **Classes**: PascalCase (Session, AsyncSession, ScreenBuffer)
- **Functions/variables**: snake_case (connect, send_data, screen_buffer)
- **Constants**: UPPER_SNAKE_CASE (TN3270_DATA, DEFAULT_PORT)
- **Private**: underscore prefix (_internal_method)

### Error Handling
- **Specific exceptions**: Use custom exceptions from protocol.exceptions
- **Logging**: Use logging.getLogger(__name__) with appropriate levels
- **Resource cleanup**: Context managers for sessions, try/finally for manual cleanup

### Code Quality
- **No macros**: Macro DSL permanently removed (CI blocks macro references)
- **RFC compliance**: Follow TN3270/TN3270E RFCs over existing implementation
- **Async patterns**: Use async context managers, proper await handling
- **EBCDIC handling**: Always use EBCDICCodec, never manual translation

### Testing Requirements
- **Linting MUST pass**: flake8 with no errors before task completion
- **Quick validation**: Always run quick_test.py after changes
- **Test markers**: Use @pytest.mark.slow, @pytest.mark.integration appropriately
- **Coverage**: Focus on core functionality, exclude tests from coverage

### Critical Rules
- **ALWAYS defer to RFC specifications** for protocol implementation
- **NEVER cancel builds** - operations complete in seconds
- **LINTING MUST PASS** before considering any task finished
- **Use constants from utils.py** - never hardcode protocol values
