# Qwen Code Assistant Usage Guide

This document outlines the practices and conventions used when working with Qwen Code Assistant on this project.

## Project Overview

Qwen Code Assistant helps with software engineering tasks by following core mandates and using specific workflows to ensure code quality and consistency.

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

### Standards Verification
- Execute project-specific build, linting and type-checking commands
- Ensure code quality and adherence to standards

## Security

- Apply security best practices
- Never introduce code that exposes, logs, or commits secrets or sensitive information

## Communication Style

- Adopt a professional, direct, and concise tone
- Focus strictly on the user's query
- Use GitHub-flavored Markdown for formatting
- Provide brief explanations (1-2 sentences) when unable to fulfill a request

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

### Compatibility
- Maintain compatibility with p3270 library
- Follow RFC specifications for protocol implementation

### Code Formatting
- Use black for code formatting
- Use flake8 for linting

## Example Workflow

When asked to audit documentation and update any that need changes:

1. Identify all documentation files in the project
2. Examine each documentation file to understand current content
3. Compare documentation with actual implementation
4. Create TODO items for needed updates
5. Update documentation files with accurate information
6. Verify changes maintain consistency with codebase