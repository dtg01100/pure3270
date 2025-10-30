# Task Plan Implementation Instructions

## Core

### 1. Plan Analysis and Preparation

**MUST complete before starting implementation:**
- **MANDATORY**: Read and fully understand the complete plan file including scope, objectives, all phases, and every checklist item
- **MANDATORY**: Read and fully understand the corresponding changes file completely - if any parts are missing from context, read the entire file back in using `read_file`
- **MANDATORY**: Identify all referenced files mentioned in the plan and examine them for context
- **MANDATORY**: Understand current project structure and conventions

### 2. Systematic Implementation Process

**Implement each task in the plan systematically:**

1. **Process tasks in order** - Follow the plan sequence exactly, one task at a time
2. **MANDATORY before implementing any task:**
   - **ALWAYS ensure implementation is associated with a specific task from the plan**
   - **ALWAYS read the entire details section for that task from the associated details markdown file in `.copilot-tracking/details/**`**

3. **Implement the task completely with working code:**
   - Follow existing code patterns and conventions from the workspace
   - Create working functionality that meets all task requirements specified in the details
   - Include proper error handling, documentation, and follow best practices

4. **Mark task complete and update changes tracking:**
   - Update plan file: change `[ ]` to `[x]` for completed task
   - **MANDATORY after completing EVERY task**: Update the changes file by appending to the appropriate Added, Modified, or Removed sections with relative file paths and one-sentence summary of what was implemented
   - **MANDATORY**: If any changes diverge from the task plan and details, specifically call out within the relevant section that the change was made outside of the plan and include the specific reason

### 3. Implementation Quality Standards

Every implementation MUST:
- Follow existing workspace patterns and conventions
- Implement complete, working functionality that meets all task requirements
- Include appropriate error handling and validation
- Use consistent naming conventions and code structure from the workspace
- Add necessary documentation and comments for complex logic
- Ensure compatibility with existing systems and dependencies

### 4. Continuous Progress and Validation

**After implementing each task:**
1. Validate the changes made against the task requirements from the details file
2. Fix any problems before moving to the next task
3. **MANDATORY**: Update the plan file to mark completed tasks `[x]`
4. **MANDATORY after EVERY task completion**: Update the changes file by appending to Added, Modified, or Removed sections with relative file paths and one-sentence summary of what was implemented
5. Continue to the next unchecked task

**Continue until:**
- All tasks in the plan are marked complete `[x]`
- All specified files have been created or updated with working code
- All success criteria from the plan have been verified

## Success Criteria

Implementation is complete when:
- ✅ All plan tasks are marked complete `[x]`
- ✅ All specified files contain working code
- ✅ Code follows workspace patterns and conventions
- ✅ All functionality works as expected within the project
- ✅ Changes file is updated after every task completion with Added, Modified, or Removed entries
- ✅ Changes file documents all phases with detailed release-ready documentation and final release summary

---
applyTo: '**/.copilot-tracking/changes/*.md'
description: 'Instructions for implementing task plans with progressive tracking and change record - Brought to you by microsoft/edge-ai'
---
