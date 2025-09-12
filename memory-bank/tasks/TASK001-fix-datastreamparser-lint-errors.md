# [TASK001] Fix DataStreamParser lint errors

**Status:** In Progress  
**Added:** 2025-09-12  
**Updated:** 2025-09-12

## Original Request
Fix remaining lint errors in DataStreamParser (e.g., correct indentation in _handle_write, add missing args to handlers like _handle_sfe).

## Thought Process
The DataStreamParser has several handler methods that were recently added or modified. These methods need to have correct syntax, indentation, and parameter signatures to pass linting. Common issues include:
- Incorrect indentation causing "unindent does not match" errors
- Missing required parameters in method definitions
- Obscured method declarations due to syntax issues

Need to systematically review each handler method and ensure they conform to Python syntax and flake8 rules.

## Implementation Plan
1. Run flake8 on pure3270/protocol/data_stream.py to identify specific errors
2. Fix indentation issues in _handle_write and other methods
3. Add missing parameters to handler methods like _handle_sfe
4. Ensure all method signatures match expected patterns
5. Re-run linting to verify fixes

## Progress Tracking

**Overall Status:** In Progress - 25% Complete

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 1.1 | Run flake8 to identify specific lint errors | Not Started | 2025-09-12 | Need to get exact error locations |
| 1.2 | Fix indentation in _handle_write method | Not Started | 2025-09-12 | Check for unindent errors |
| 1.3 | Add missing args to _handle_sfe and other handlers | Not Started | 2025-09-12 | Review method signatures |
| 1.4 | Verify all handlers have correct syntax | Not Started | 2025-09-12 | Run linting again |

## Progress Log
### 2025-09-12
- Created task to track DataStreamParser lint fixes
- Identified need for systematic review of handler methods
- Planned implementation steps based on known issues
