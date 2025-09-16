# Qwen Code Assistant Usage Guide

This document outlines the practices and conventions used when working with Qwen Code Assistant on this project.

## Project Overview

Qwen Code Assistant helps with software engineering tasks by following core mandates and using specific workflows to ensure code quality and consistency.

## Memory Bank and Copilot Instructions

Qwen Code Assistant should reference the following instruction files for project-specific guidance:

1. **Memory Bank Instructions**: Located at `.github/instructions/memory-bank.instructions.md`
   - Contains detailed workflow requirements for task management
   - Must be read at the start of every task
   - Includes guidelines for maintaining project context across sessions
   - Defines the Memory Bank structure with required core files:
     - `projectbrief.md` - Foundation document defining core requirements and goals
     - `productContext.md` - Why this project exists and problems it solves
     - `activeContext.md` - Current work focus and recent changes
     - `systemPatterns.md` - System architecture and design patterns
     - `techContext.md` - Technologies used and technical constraints
     - `progress.md` - What works, what's left to build, and current status
     - `tasks/` folder - Contains individual task files and index

2. **Copilot Instructions**: Located at `.github/copilot-instructions.md`
   - Contains project-specific technical guidelines
   - Includes RFC compliance requirements for TN3270/TN3270E protocol implementation
   - Provides development workflows, validation commands, and code patterns
   - Details the package structure and important files to check when making changes
   - Contains usage patterns for basic Session, Async Session, and p3270 integration
   - Lists essential validation commands for quick testing after changes

## Core Mandates

### Conventions
- Strictly adhere to existing project conventions when reading or modifying code
- Analyze surrounding code, tests, and configuration first before making changes
- Follow the style, structure, framework choices, typing, and architectural patterns of existing code

### Libraries/Frameworks
- NEVER assume a library/framework is available or appropriate
- Verify established usage within the project before employing it
- Check imports, configuration files, and neighboring files to understand what's already in use

### Style & Structure
- Mimic the style (formatting, naming), structure, framework choices, typing, and architectural patterns of existing code
- Understand the local context (imports, functions/classes) to ensure changes integrate naturally and idiomatically

### Comments
- Add code comments sparingly, focusing on *why* something is done rather than *what* is done
- Only add high-value comments if necessary for clarity or if requested by the user
- Do not edit comments that are separate from the code being changed

### Proactiveness
- Fulfill user requests thoroughly, including directly implied follow-up actions

### Confirm Ambiguity/Expansion
- Do not take significant actions beyond the clear scope of the request without confirming with the user
- If asked *how* to do something, explain first rather than just doing it

## Primary Workflows

### Software Engineering Tasks
When requested to perform tasks like fixing bugs, adding features, refactoring, or explaining code:

1. **Plan**: Create an initial plan based on existing knowledge and immediately obvious context
2. **Implement**: Begin implementing while gathering additional context as needed
3. **Adapt**: Update plans as new information is discovered
4. **Verify**: Run project-specific build, linting and type-checking commands

### New Applications
For implementing new applications:

1. **Understand Requirements**: Identify core features, desired UX, visual aesthetic, and constraints
2. **Propose Plan**: Formulate a development plan and present it to the user
3. **User Approval**: Obtain user approval for the proposed plan
4. **Implementation**: Convert the approved plan into a structured todo list and implement
5. **Verify**: Review work against original request and fix bugs/deviations
6. **Solicit Feedback**: Provide instructions on how to start the application and request user feedback

## Task Management

Qwen Code uses the `todo_write` tool to manage tasks:

- Plan complex or multi-step work using TODO items
- Mark todos as `in_progress` when starting and `completed` when finishing
- Add new todos if the scope expands
- Refine approach based on what is learned during implementation

## Tool Usage

### File Paths
- Always use absolute paths when referring to files
- Combine the absolute path of the project's root directory with the file's path relative to the root

### Parallelism
- Execute multiple independent tool calls in parallel when feasible

### Command Execution
- Explain modifying commands before executing them
- Prioritize user understanding and safety

### Background Processes
- Use background processes (via `&`) for commands unlikely to stop on their own

## Code Quality Standards

### Testing
- Run project tests after making changes
- Identify correct test commands by examining README files and build configuration
- Always run `python quick_test.py` after any change to validate basics
- Focus on Quick Smoke Test, Navigation Method Test, and Release Validation Test
- Use built-in validation instead of external test tools when dependencies are unavailable

### Standards Verification
- Execute project-specific build, linting and type-checking commands
- Ensure code quality and adherence to standards
- Always check `session.py` after modifying core functionality (main 70KB file)
- Always check `examples/` when changing public APIs
- Always run black formatting before committing changes

### Important Files to Check When Making Changes
- **Always check session.py** after modifying core functionality (main 70KB file)
- **Always run quick_test.py** after any change to validate basics
- **Always check examples/** when changing public APIs
- **Always run black formatting** before committing changes
- **Check protocol/ directory** when modifying TN3270/TN3270E protocol handling
- **Check emulation/ directory** when modifying screen buffer or EBCDIC translation
- **Check patching/ directory** when modifying p3270 compatibility features

## Security

- Apply security best practices
- Never introduce code that exposes, logs, or commits secrets or sensitive information

## Communication Style

- Adopt a professional, direct, and concise tone
- Focus strictly on the user's query
- Use GitHub-flavored Markdown for formatting
- Provide brief explanations (1-2 sentences) when unable to fulfill a request

## Usage Patterns

### Basic Session Usage
```python
from pure3270 import Session

# Synchronous usage
with Session() as session:
    session.connect('hostname', port=23, ssl=False)
    session.send(b'String(username)')
    session.send(b'key Enter')
    response = session.read()
```

### Async Session Usage
```python
from pure3270 import AsyncSession
import asyncio

async def main():
    async with AsyncSession() as session:
        await session.connect('hostname', port=23)
        await session.send(b'key Enter')
        response = await session.read()

asyncio.run(main())
```

### p3270 Integration via Patching
```python
import pure3270
pure3270.enable_replacement()  # Apply patches

import p3270  # Now uses pure3270 under the hood
session = p3270.P3270Client()
session.connect('hostname')
```

## Project-Specific Practices

### Python Development
- Use Python 3.8+ with standard library only (no external dependencies)
- Use asyncio for async operations
- Follow existing patterns in session.py for sync/async wrappers
- Use context managers for resource management
- Prefer bytearray for binary data manipulation
- Use structured logging with appropriate levels
- Handle errors with custom exceptions
- Prefer composition over inheritance
- Use properties for computed values
- Use 4-space indentation, no tabs
- Prefer double quotes for strings
- Type hints are encouraged but not enforced
- Private methods start with underscore
- Follow the Session/AsyncSession API patterns for public interfaces
- Use EBCDICCodec for all EBCDIC translations
- Follow RFC specifications for protocol implementation
- Use constants from protocol/utils.py rather than hardcoding values

### Testing
- Use pytest for testing
- Use pytest-asyncio for async tests
- Use parametrized tests for testing multiple scenarios
- Use fixtures for test setup/teardown
- Write comprehensive tests for new features
- Maintain 80%+ test coverage

### Documentation
- Document public APIs with docstrings
- Keep documentation up-to-date with implementation changes

### CI/CD
- Use GitHub Actions for CI/CD
- Follow semantic versioning for releases

### Package Structure
- Main API exports (Session, AsyncSession, enable_replacement) in `pure3270/__init__.py`
- Core Session classes in `pure3270/session.py` (70KB main file)
- 3270 terminal emulation logic in `pure3270/emulation/`:
  - Screen buffer management with EBCDIC support in `screen_buffer.py`
  - EBCDIC ↔ ASCII translation (IBM CP037) in `ebcdic.py`
  - Printer session buffer management in `printer_buffer.py`
- TN3270/TN3270E protocol handling in `pure3270/protocol/`:
  - Main protocol handler with negotiation in `tn3270_handler.py`
  - Telnet/TN3270E negotiation logic in `negotiator.py`
  - Data stream parsing and SNA responses in `data_stream.py`
  - TN3270E header parsing in `tn3270e_header.py`
  - Protocol constants and utilities in `utils.py`
  - Protocol-specific exceptions in `exceptions.py`
- p3270 monkey-patching functionality in `pure3270/patching/`:
  - MonkeyPatchManager for dynamic patching in `patching.py`
  - S3270 interface compatibility layer in `s3270_wrapper.py`
- Runnable example scripts in `pure3270/examples/` and root level `examples/`

### Compatibility
- Maintain compatibility with p3270 library
- Follow RFC specifications for protocol implementation

### Code Formatting
- Use black for code formatting
- Use flake8 for linting

## Memory Bank Workflow

When working on tasks, Qwen Code Assistant must follow the Memory Bank workflow:

1. **Read All Memory Bank Files**: At the start of every task, read all files in the `memory-bank/` directory:
   - Core files: `projectbrief.md`, `productContext.md`, `activeContext.md`, `systemPatterns.md`, `techContext.md`, `progress.md`
   - Task index: `memory-bank/tasks/_index.md`
   - Individual task files in `memory-bank/tasks/` as relevant to current work
2. **Update Documentation**: As work progresses, update relevant memory bank files with current status
3. **Track Progress**: Maintain detailed progress logs in task-specific files
4. **Update Task Index**: Keep the `memory-bank/tasks/_index.md` file updated with current task statuses

## RFC Compliance

When working on TN3270/TN3270E protocol implementation, always defer to RFC specifications rather than assuming the current implementation or tests have correct behavior. Key RFC references include:

- RFC 1576: TN3270 Current Practices
- RFC 1646: TN3270 Enhancements (TN3270E)
- RFC 2355: TN3270 Enhancements (updated)
- RFC 854: Telnet Protocol Specification
- RFC 855: Telnet Option Specifications
- RFC 856: Telnet Binary Transmission
- RFC 857: Telnet Echo Option
- RFC 858: Telnet Suppress Go Ahead Option
- RFC 859: Telnet Status Option
- RFC 860: Telnet Timing Mark Option
- RFC 1091: Telnet Terminal-Type Option

Always validate implementation against RFC requirements, not just existing tests. Refer to `.github/copilot-instructions.md` for detailed guidance on RFC compliance and common conflicts between RFC specifications and current implementation.

## Development Workflows

Follow these essential validation commands after making changes:

1. **Quick validation** (0.15 seconds total):
   ```bash
   python quick_test.py && python examples/example_standalone.py
   ```

2. **Import test** (0.08 seconds):
   ```bash
   python -c "import pure3270; s=pure3270.Session(); print('✓ Works'); s.close()"
   ```

3. **Full test suite** (0.6 seconds):
   ```bash
   python run_all_tests.py
   ```

4. **Code compilation check** (0.05 seconds):
   ```bash
   python -m py_compile pure3270/*.py
   ```

5. **Standalone example test** (0.08 seconds):
   ```bash
   python examples/example_standalone.py
   ```

6. **Patching functionality test** (0.08 seconds):
   ```bash
   python examples/example_patching.py
   ```

When linting tools are available, ensure all pass before considering any task finished:
```bash
python -m black pure3270/ && python -m flake8 pure3270/ && python quick_test.py && python run_all_tests.py
```

**CRITICAL: Task Completion Requirements**
- Linters MUST pass before considering any task finished
- ALWAYS run code formatting and linting checks:
  ```bash
  # Format code first
  python -m black pure3270/

  # Then run linter - this MUST pass with no errors
  python -m flake8 pure3270/
  ```
- Never mark a task as complete if linting fails
- Fix all linting errors before proceeding
- Code quality gates: Formatting + Linting + Tests = Task Complete

## Example Workflow

When asked to implement a new feature or fix a bug:

1. **Plan**: Identify requirements and affected components using Memory Bank files
2. **Implement**: Make changes to relevant modules following RFC specifications
3. **Test**: Run `python quick_test.py` and relevant examples
4. **Validate**: Run full test suite with `python run_all_tests.py`
5. **Format**: Apply black formatting with `python -m black pure3270/`
6. **Lint**: Run flake8 linting with `python -m flake8 pure3270/` (MUST pass with no errors)
7. **Commit**: Ensure all tests pass and linting is clean

When asked to audit documentation and update any that need changes:

1. Identify all documentation files in the project
2. Examine each documentation file to understand current content
3. Compare documentation with actual implementation
4. Create TODO items for needed updates
5. Update documentation files with accurate information
6. Verify changes maintain consistency with codebase
7. Run validation commands to ensure documentation examples still work
