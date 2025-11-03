# Pure3270 Documentation Index

This is a comprehensive index of all documentation and notes in the pure3270 project, organized by category and purpose.

## Table of Contents
- [Project Overview](#project-overview)
- [User Documentation](#user-documentation)
- [Developer Documentation](#developer-documentation)
- [Architecture & Design](#architecture--design)
- [Testing & Validation](#testing--validation)
- [CI/CD & Quality Assurance](#cicd--quality-assurance)
- [MCP Server Documentation](#mcp-server-documentation)
- [Development Reports](#development-reports)
- [Project Management](#project-management)
- [Legacy & Archive](#legacy--archive)

---

## Project Overview

| File | Location | Purpose | Audience |
|------|----------|---------|----------|
| `README.md` | `/` | Project overview, installation, getting started | All users |
| `CONTRIBUTING.md` | `/` | Contribution guidelines and processes | Contributors |
| `THIRD_PARTY_NOTICES.md` | `/` | License and attribution information | Legal/Compliance |
| `RELEASE_NOTES.md` | `/` | Release history and changes | Users |
| `PORTING_GUIDELINES.md` | `/` | Guidelines for porting from s3270 | Developers |
| `MIGRATION_GUIDE.md` | `/` | Migration guides for users | Users |

---

## User Documentation

### Official Documentation (`/docs/`)
| File/Directory | Purpose | Status |
|----------------|---------|--------|
| `docs/README.md` | Documentation organization guide | ✅ Complete |
| `docs/source/index.rst` | Main documentation index | Sphinx |
| `docs/source/usage.rst` | Usage guide | Sphinx |
| `docs/source/api.rst` | API reference | Sphinx |
| `docs/source/examples.rst` | Code examples | Sphinx |
| `docs/source/advanced.rst` | Advanced usage | Sphinx |
| `docs/source/modules.rst` | Module documentation | Sphinx |
| `docs/source/terminal_models.rst` | Terminal model configuration | Sphinx |

### Guides (`/docs/guides/`)
*Directory for user guides and tutorials*

### Examples (`/examples/`)
| File | Purpose | Category |
|------|---------|----------|
| `example_end_to_end.py` | Complete usage example | Getting Started |
| `example_protocol_operations.py` | Protocol operations demo | Protocol |
| `example_advanced_screen_operations.py` | Screen operations | Screen Handling |
| `example_error_handling.py` | Error handling patterns | Error Handling |
| `example_terminal_models.py` | Terminal model usage | Configuration |
| `example_printer_session.py` | Printer session usage | Printing |
| `example_pub400.py` | Real system connection | Real Systems |
| `example_pub400_s3270.py` | s3270 comparison | Comparison |
| `example_pub400_p3270.py` | p3270 comparison | Comparison |
| `example_pub400_ultra_fast.py` | High-performance usage | Performance |

---

## Developer Documentation

### Development Guides (`/docs/development/`)
*Directory for development processes and guidelines*

### GitHub Instructions (`.github/instructions/`)
| File | Purpose | Audience |
|------|---------|----------|
| `task-implementation.instructions.md` | Task implementation guidelines | AI Assistants |
| `markdown.instructions.md` | Markdown formatting standards | All Contributors |
| `security-and-owasp.instructions.md` | Security best practices | Developers |
| `ai-prompt-engineering-safety-best-practices.instructions.md` | AI safety guidelines | AI Assistants |

### AI Prompts (`.github/prompts/`)
| File | Purpose | Audience |
|------|---------|----------|
| `create-oo-component-documentation.prompt.md` | OO component docs | AI Assistants |
| `create-agentsmd.prompt.md` | Agent documentation | AI Assistants |
| `create-readme.prompt.md` | README generation | AI Assistants |
| `create-llms.prompt.md` | LLM documentation | AI Assistants |
| `documentation-writer.prompt.md` | Documentation writing | AI Assistants |
| `review-and-refactor.prompt.md` | Code review guidelines | AI Assistants |
| `python-mcp-server-generator.prompt.md` | MCP server generation | AI Assistants |
| `prompt-builder.prompt.md` | Prompt engineering | AI Assistants |

### Chat Modes (`.github/chatmodes/`)
| File | Purpose | Audience |
|------|---------|----------|
| `principal-software-engineer.chatmode.md` | Senior engineer mode | AI Assistants |
| `software-engineer-agent-v1.chatmode.md` | Standard engineer mode | AI Assistants |
| `mentor.chatmode.md` | Mentoring mode | AI Assistants |
| `python-mcp-expert.chatmode.md` | MCP expert mode | AI Assistants |
| `implementation-plan.chatmode.md` | Planning mode | AI Assistants |
| `tdd-red.chatmode.md` | TDD red phase | AI Assistants |
| `tdd-green.chatmode.md` | TDD green phase | AI Assistants |
| `tdd-refactor.chatmode.md` | TDD refactor phase | AI Assistants |
| `debug.chatmode.md` | Debugging mode | AI Assistants |
| `research-technical-spike.chatmode.md` | Research mode | AI Assistants |
| `tech-debt-remediation-plan.chatmode.md` | Tech debt planning | AI Assistants |
| `janitor.chatmode.md` | Cleanup mode | AI Assistants |
| `blueprint-mode.chatmode.md` | Architecture planning | AI Assistants |
| `plan.chatmode.md` | General planning | AI Assistants |

---

## Architecture & Design

### Architecture Documentation (`/docs/architecture/`)
*Directory for system architecture documentation*

### Memory Bank (`/memory-bank/`)
| File | Purpose | Audience |
|------|---------|----------|
| `activeContext.md` | Current project context | Team |
| `productContext.md` | Product vision and requirements | Team |
| `projectbrief.md` | Project overview and goals | Team |
| `progress.md` | Current progress and status | Team |
| `systemPatterns.md` | System design patterns | Developers |
| `techContext.md` | Technical architecture context | Developers |
| `trace_negotiation_test_coverage.md` | Test coverage analysis | QA |

### Task Documentation (`/memory-bank/tasks/`)
| File | Purpose | Status |
|------|---------|--------|
| `_index.md` | Task index | Active |
| `TASK002-add-screen-parity-regression-scaffold.md` | Screen parity testing | Complete |
| `TASK004-integrate-s3270-license-attribution.md` | License attribution | Complete |
| `TASK005-create-porting-guidelines-document.md` | Porting guidelines | Complete |
| `TASK006-attribution-comment-scaffolding.md` | Attribution comments | Complete |
| `TASK008-implement-new-environ-proper-parsing.md` | Environment parsing | Active |
| `TASK009-configurable-terminal-models.md` | Terminal models | Active |

### Design Documents
| File | Location | Purpose |
|------|----------|---------|
| `architecture.md` | `/` | System architecture overview | Developers |
| `CI_CD.md` | `/` | CI/CD architecture | DevOps |
| `CI_README.md` | `/` | CI/CD documentation | DevOps |

---

## Testing & Validation

### Testing Documentation (`/docs/testing/`)
*Directory for testing documentation*

### Validation Documentation (`/docs/validation/`)
*Directory for validation procedures and reports*

### Test Reports & Analysis
| File | Purpose | Category |
|------|---------|----------|
| `COMPREHENSIVE_VALIDATION_REPORT.md` | Complete validation results | Validation |
| `FINAL_VALIDATION_SUMMARY.md` | Final validation status | Validation |
| `REAL_SYSTEM_VALIDATION_SUMMARY.md` | Real system testing | Validation |
| `TRACE_TESTING_SUMMARY.md` | Trace testing results | Testing |
| `PYTEST_TRIAGE_SUMMARY.md` | Test triage results | Testing |
| `COMPLETE_TEST_FIXES_SUMMARY.md` | All test fixes summary | Testing |
| `TEST_FIXES_SUMMARY.md` | Test fix documentation | Testing |
| `TEST_FIXES_SUMMARY_2025-11-01.md` | Dated test fixes | Testing |
| `FAILING_TESTS_FIXED.md` | Fixed failing tests | Testing |
| `TEST_HANG_INVESTIGATION.md` | Test hanging issues | Debugging |
| `TEST_HANG_RESOLUTION.md` | Test hang resolution | Debugging |
| `TEST_IMPROVEMENTS_SUMMARY.md` | Test improvements | Testing |
| `TEST_RESOLUTION_SUMMARY.md` | Test resolution summary | Testing |

### Test Data (`/tests/data/`)
| Directory/File | Purpose |
|----------------|---------|
| `expected/` | Expected test outputs |
| `traces/` | Test trace files |

---

## CI/CD & Quality Assurance

### GitHub Workflows (`.github/workflows/`)
| File | Purpose | Triggers |
|------|---------|----------|
| `ci.yml` | Main CI pipeline | Push/PR |
| `python-regression.yml` | Python version testing | Push/PR |
| `trace_replay_tests.yml` | Trace replay testing | Push/PR |
| `static-analysis.yml` | Code quality checks | Push/PR |
| `reports.yml` | Report generation | Push/PR |
| `documentation.yml` | Docs building | Push/PR |
| `copilot-regression-analysis.yml` | Copilot testing | Push/PR |

### Quality Assurance Tools (`/tools/`)
| File | Purpose | Category |
|------|---------|----------|
| `screen_buffer_regression_test.py` | Screen buffer testing | Regression |
| `test_trace_replay.py` | Trace replay testing | Integration |
| `enhanced_trace_replay.py` | Enhanced trace testing | Integration |
| `trace_coverage_report.py` | Coverage reporting | Analysis |
| `compare_replay_with_s3270.py` | s3270 comparison | Validation |
| `batch_compare_traces.py` | Batch trace comparison | Validation |
| `generate_expected_outputs.py` | Test data generation | Testing |
| `validate_screen_snapshot.py` | Screen validation | Testing |
| `api_compatibility_report.py` | API compatibility | Analysis |
| `validate_attributions.py` | Attribution validation | Compliance |
| `generate_attribution.py` | Attribution generation | Compliance |

### Quality Gates
| File | Purpose |
|------|---------|
| `.pylintrc` | Python linting configuration |
| `.bandit` | Security scanning configuration |
| `.mypy.ini` | Type checking configuration |
| `.flake8` | Style checking configuration |
| `.pre-commit-config.yaml` | Pre-commit hooks |
| `.coveragerc` | Coverage configuration |
| `pyproject.toml` | Project configuration |

---

## MCP Server Documentation

### MCP Server Reports
| File | Purpose | Status |
|------|---------|--------|
| `MCP_SERVERS_SUMMARY.md` | MCP server overview | Complete |
| `MCP_SERVERS_COMPLETION_REPORT.md` | Implementation status | Complete |
| `MCP_SERVERS_VALIDATION_REPORT.md` | Testing results | Complete |
| `MCP_CORE_FUNCTIONALITY_REPORT.md` | Core functionality | Complete |
| `MCP_FUNCTIONALITY_DEMO_REPORT.md` | Demonstration results | Complete |
| `PURE3270_MCP_TESTING_REPORT.md` | Testing report | Complete |

### MCP Server Code (`/mcp-servers/`)
| Server | Purpose | Status |
|--------|---------|--------|
| `terminal-debugger/` | Terminal debugging | Complete |
| `connection-tester/` | Connection testing | Complete |
| `tn3270-protocol-analyzer/` | Protocol analysis | Complete |
| `ebcdic-ascii-converter/` | Character conversion | Complete |

### MCP Configuration
| File | Purpose |
|------|---------|
| `mcp-config.json` | MCP server configuration |
| `launch_mcp_servers.py` | MCP server launcher |

---

## Development Reports

### Implementation Reports
| File | Purpose | Scope |
|------|---------|--------|
| `IMPLEMENTATION_SUMMARY.md` | Implementation progress | All |
| `SESSION_SUMMARY.md` | Session handling | Protocol |
| `SESSION_ACTIONS_IMPLEMENTATION_STATUS.md` | Session actions | Protocol |
| `INFINITE_LOOP_PREVENTION.md` | Loop prevention | Stability |
| `AGENTS.md` | AI agent documentation | Development |

### Protocol-Specific Reports
| File | Purpose | Protocol Area |
|------|---------|--------|
| `CONNECTION_FIX_SUMMARY.md` | Connection fixes | Networking |
| `RA_FIX_SUMMARY.md` | RA command fixes | Screen Control |
| `S3270_PROTOCOL_ALIGNMENT_FIXES.md` | Protocol alignment | Compatibility |
| `API_COMPATIBILITY_AUDIT.md` | API compatibility | Interface |
| `api_compatibility_report.md` | Compatibility report | Interface |

### Performance & Optimization
| File | Purpose |
|------|---------|
| `TRACE_TIMEOUT_FIX_SUMMARY.md` | Timeout fixes |
| `TRACE_REPLAY_COVERAGE_ANALYSIS.md` | Coverage analysis |
| `TRACE_REPLAY_IMPROVEMENTS_SUMMARY.md` | Replay improvements |
| `TRACE_RESEARCH_SUMMARY.md` | Trace research |

---

## Project Management

### Current Tasks
| File | Purpose |
|------|---------|
| `TODO.md` | Current task list and priorities |
| `DOCUMENTATION_UPDATE_NOV_2025.md` | Documentation updates |

### Project Context
| File | Purpose | Audience |
|------|---------|----------|
| `memory-bank/productContext.md` | Product vision | Team |
| `memory-bank/projectbrief.md` | Project goals | Team |
| `memory-bank/activeContext.md` | Current context | Team |
| `memory-bank/progress.md` | Progress tracking | Team |

---

## Legacy & Archive

### Archive Directory (`/archive/`)
| Subdirectory | Contents |
|--------------|----------|
| `old-ci-scripts/` | Legacy CI scripts |
| `stale-tests/` | Deprecated tests |
| `ai-artifacts/` | AI-generated content |

### Deprecated Files
*Files that may be moved to archive or removed*

### Temporary Files
| File | Purpose | Status |
|------|---------|--------|
| `kilo_code_task_oct-26-2025_2-32-41-pm.md` | Temporary task notes | Temporary |
| `test_eua_fix.py` | EUA fix testing | Temporary |
| `debug_trace_categories.py` | Debug script | Temporary |

---

## Quick Reference by Category

### Finding Documentation by Task

**New Users:**
1. `README.md` → `docs/source/usage.rst`
2. `examples/example_end_to_end.py`

**Contributors:**
1. `CONTRIBUTING.md` → `.github/instructions/`
2. `memory-bank/activeContext.md`

**Protocol Developers:**
1. `memory-bank/techContext.md` → `docs/architecture/`
2. Protocol-specific summary files

**QA Engineers:**
1. `docs/testing/` → `docs/validation/`
2. Test summary files

**DevOps:**
1. `.github/workflows/` → `CI_CD.md`
2. `CI_README.md`

### File Naming Conventions

- **Summary Reports**: `UPPER_CASE_SUMMARY.md`
- **Reports**: `UPPER_CASE_REPORT.md`
- **Guides**: `Title Case.md`
- **Configuration**: `kebab-case.ext`
- **Directories**: `kebab-case/`

### Maintenance Notes

- Summary files should be updated when related work is completed
- Documentation should be reviewed quarterly for accuracy
- Archive old documentation rather than deleting
- Use dates in filenames for time-sensitive reports

---

*Last updated: November 2025*
*Maintained by: Development Team*
