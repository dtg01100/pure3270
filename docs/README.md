# Documentation Organization Guide

This document outlines the organization of documentation and notes for the pure3270 project.

## Directory Structure

### `/docs/` - Official Documentation
- **Purpose**: Sphinx-generated documentation for users and developers
- **Contents**:
  - `source/` - Sphinx source files (RST format)
  - `build/` - Generated HTML documentation
  - `architecture/` - System architecture documentation
  - `development/` - Development guides and processes
  - `guides/` - User guides and tutorials
  - `migration/` - Migration guides
  - `reports/` - Generated reports and analysis
  - `testing/` - Testing documentation
  - `validation/` - Validation reports and procedures

### `/memory-bank/` - Project Context and Planning
- **Purpose**: Internal project knowledge, context, and planning documents
- **Contents**:
  - `activeContext.md` - Current project context
  - `productContext.md` - Product vision and requirements
  - `projectbrief.md` - Project overview and goals
  - `progress.md` - Current progress and status
  - `systemPatterns.md` - System design patterns
  - `techContext.md` - Technical architecture context
  - `tasks/` - Individual task documentation

### `/.github/` - Development Workflow Documentation
- **Purpose**: GitHub Actions, AI assistant configurations, and development processes
- **Contents**:
  - `workflows/` - CI/CD pipeline definitions
  - `instructions/` - Task implementation guidelines
  - `prompts/` - AI assistant prompt templates
  - `chatmodes/` - AI assistant behavior modes

### Root Level Documentation
- **README.md** - Project overview and getting started
- **TODO.md** - Current task list and priorities
- **CONTRIBUTING.md** - Contribution guidelines
- **THIRD_PARTY_NOTICES.md** - License and attribution information

## Summary Reports and Analysis

### Development Reports
- **COMPLETE_TEST_FIXES_SUMMARY.md** - Summary of all test fixes
- **COMPREHENSIVE_VALIDATION_REPORT.md** - Complete validation results
- **FINAL_VALIDATION_SUMMARY.md** - Final validation status
- **IMPLEMENTATION_SUMMARY.md** - Implementation progress summary
- **TEST_FIXES_SUMMARY.md** - Test fix documentation

### Protocol and Feature Reports
- **CONNECTION_FIX_SUMMARY.md** - Connection handling fixes
- **RA_FIX_SUMMARY.md** - Repeat to Address fixes
- **TRACE_TESTING_SUMMARY.md** - Trace testing results
- **REAL_SYSTEM_VALIDATION_SUMMARY.md** - Real system testing results

### MCP Server Documentation
- **MCP_SERVERS_SUMMARY.md** - MCP server overview
- **MCP_SERVERS_COMPLETION_REPORT.md** - MCP server implementation status
- **MCP_SERVERS_VALIDATION_REPORT.md** - MCP server testing results
- **MCP_CORE_FUNCTIONALITY_REPORT.md** - Core MCP functionality
- **MCP_FUNCTIONALITY_DEMO_REPORT.md** - MCP demonstration results

### CI/CD and Quality Assurance
- **PYTEST_TRIAGE_SUMMARY.md** - Test triage results
- **FAILING_TESTS_FIXED.md** - Fixed failing tests documentation
- **TEST_HANG_INVESTIGATION.md** - Test hanging issue investigation
- **INFINITE_LOOP_PREVENTION.md** - Infinite loop prevention measures

## Finding Documentation

### For Users
1. Start with `README.md` for project overview
2. Check `docs/` for detailed user guides
3. Look in `docs/guides/` for specific tutorials

### For Developers
1. Read `CONTRIBUTING.md` for contribution guidelines
2. Check `docs/development/` for development processes
3. Review `memory-bank/` for project context
4. Look at `.github/instructions/` for task implementation guidance

### For Specific Topics
- **Testing**: `docs/testing/`, test summary files
- **Architecture**: `docs/architecture/`, `memory-bank/systemPatterns.md`
- **Validation**: Validation summary files, `docs/validation/`
- **MCP Servers**: MCP summary and report files
- **CI/CD**: `.github/workflows/`, CI/CD summary files

## Maintenance Guidelines

### Adding New Documentation
1. **User-facing docs** → `docs/source/`
2. **Internal notes** → `memory-bank/`
3. **Development processes** → `.github/instructions/`
4. **AI prompts** → `.github/prompts/`
5. **Summary reports** → Root level with descriptive names

### Naming Conventions
- Use `UPPER_CASE` for summary and report files
- Use `kebab-case` for directory names
- Use `Title Case` for document titles
- Include dates in filenames when relevant (e.g., `TEST_FIXES_SUMMARY_2025-11-01.md`)

### Review Process
- Technical documentation should be reviewed by team members
- User documentation should be tested for clarity
- Summary reports should be validated against source data

## Quick Reference

| Document Type | Location | Purpose |
|---------------|----------|---------|
| User Guides | `docs/guides/` | How-to guides for users |
| API Docs | `docs/source/api.rst` | API reference |
| Architecture | `docs/architecture/` | System design |
| Development | `docs/development/` | Development processes |
| Validation | `docs/validation/` | Testing and validation |
| Project Context | `memory-bank/` | Internal project knowledge |
| CI/CD | `.github/workflows/` | Build and deployment |
| AI Assistance | `.github/prompts/` | AI assistant configurations |
| Task Instructions | `.github/instructions/` | Implementation guidelines |
| Summary Reports | Root level | Status and analysis reports |
