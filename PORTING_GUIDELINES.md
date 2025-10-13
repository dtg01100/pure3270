# Porting Guidelines for Pure3270

## Overview

This document provides comprehensive guidelines for porting third-party code into the Pure3270 project. These guidelines ensure that all ported code maintains legal compliance, quality standards, and compatibility with the project's architecture and goals.

## 1. Porting Philosophy

### 1.1 Core Principles

Pure3270 follows a **selective porting strategy** that prioritizes:

- **RFC-First Development**: ALWAYS defer to RFC specifications rather than assuming existing implementations are correct
- **Protocol Fidelity**: Maintaining accurate 3270/TN3270 protocol implementation per RFC standards
- **Clean Architecture**: Preserving the layered architecture (Protocol → Emulation → Session → Client)
- **Zero Dependencies**: Minimizing external dependencies for runtime usage
- **Quality over Quantity**: Careful evaluation before porting any code
- **Attribution Integrity**: Proper legal attribution for all ported work

### 1.1.1 RFC-First Development Philosophy

**CRITICAL**: When implementing or modifying TN3270/TN3270E protocol behavior, **ALWAYS defer to RFC specifications** rather than assuming the current implementation or source code has correct behavior. The implementation may contain bugs, incomplete features, or non-standard workarounds that should be corrected to match RFC requirements.

#### Key RFC References
- **RFC 854**: Telnet Protocol Specification
- **RFC 855**: Telnet Option Specifications
- **RFC 856**: Telnet Binary Transmission
- **RFC 857**: Telnet Echo Option
- **RFC 858**: Telnet Suppress Go Ahead Option
- **RFC 859**: Telnet Status Option
- **RFC 860**: Telnet Timing Mark Option
- **RFC 1091**: Telnet Terminal-Type Option
- **RFC 1576**: TN3270 Current Practices
- **RFC 1646**: TN3270 Enhancements (TN3270E)
- **RFC 2355**: TN3270 Enhancements (updated)

#### RFC Compliance Guidelines
1. **RFC First**: When implementing or modifying protocol behavior, consult the relevant RFC first
2. **Test Against RFC**: Validate implementation against RFC requirements, not just existing tests
3. **Document Deviations**: If current code deviates from RFC, document why and plan correction
4. **Standards Compliance**: Prefer standards-compliant behavior over backward compatibility with non-standard implementations
5. **Protocol Constants**: Use RFC-defined constants and values, not implementation-specific ones

### 1.2 When to Consider Porting

Porting should only be considered when:

1. **No Native Alternative**: The functionality cannot be reasonably implemented using existing Python standard library or project code
2. **Significant Quality Gap**: The third-party implementation offers substantial improvements over potential native implementations
3. **Maintenance Burden**: The ported code will not create excessive maintenance overhead
4. **License Compatibility**: The source license is compatible with Pure3270's MIT license
5. **Architecture Fit**: The code fits naturally into Pure3270's layered architecture

## 2. Evaluation Framework

### 2.1 Porting Decision Matrix

Use this matrix to evaluate whether code should be ported or reimplemented:

| Criteria | Port (Score 3) | Reimplement (Score 1) | Notes |
|----------|----------------|-----------------------|-------|
| **Complexity** | Simple, well-understood algorithms | Complex proprietary logic | Consider porting simple utilities |
| **Dependencies** | No new dependencies | Introduces new required dependencies | Pure3270 prefers zero runtime dependencies |
| **License** | MIT/BSD compatible | GPL/Restrictive licenses | Must be compatible with MIT |
| **Maintenance** | Well-maintained upstream | Abandoned or poorly maintained | Active maintenance is crucial |
| **Architecture Fit** | Fits existing layers | Requires architectural changes | Must fit protocol/emulation/session layers |
| **Test Coverage** | Well-tested | Poor or no tests | Must include comprehensive tests |
| **Documentation** | Well-documented | Poor documentation | Must be understandable |

**Scoring**: 15+ points = Consider Porting; <15 points = Reimplement or Avoid

### 2.2 Mandatory Evaluation Steps

Before proposing any port:

1. **Document the Need**: Clearly explain why porting is necessary
2. **License Analysis**: Verify license compatibility and requirements
3. **Architecture Impact**: Assess how the code fits into existing layers
4. **Maintenance Assessment**: Evaluate upstream maintenance status
5. **Alternative Analysis**: Document why reimplementation isn't feasible
6. **Testing Strategy**: Plan comprehensive testing approach
7. **Attribution Planning**: Identify all attribution requirements

## 3. Legal and Attribution Requirements

### 3.1 License Compatibility

All ported code must be compatible with Pure3270's MIT license:

**Compatible Licenses**:
- MIT License
- BSD 2-Clause/BSD 3-Clause
- Apache License 2.0
- ISC License
- Python Software Foundation License

**Incompatible Licenses**:
- GPL v2/v3 (unless specifically allowed)
- LGPL (creates linking requirements)
- Proprietary licenses
- Licenses requiring attribution in specific formats

### 3.2 Attribution Documentation

All ported code must include comprehensive attribution using the **Attribution Scaffolding System**:

#### Attribution Scaffolding System

Pure3270 provides standardized tools for creating attribution comments:

```bash
# Interactive mode (recommended)
python tools/generate_attribution.py --interactive

# Generate module-level attribution
python tools/generate_attribution.py --type module \
    --source "Original Project" \
    --url "https://example.com/project" \
    --license "MIT License" \
    --description "Description of what was ported"
```

#### Required Attribution Elements:
1. **Source Identification**: Original project name, author, and URL
2. **License Text**: Complete license text for the ported code
3. **Modification Notes**: Clear indication of what was modified
4. **Integration Points**: How the code integrates with Pure3270
5. **Compatibility Statements**: Any compatibility guarantees or limitations

#### Attribution Format:
```markdown
## [Original Project Name]

**Original Project**: [Project Name]
**Original Author**: [Author Name]
**Original URL**: [Project URL]
**License**: [License Name]

### Porting Details

- **Ported Components**: [List of ported files/functions]
- **Integration Layer**: [Protocol/Emulation/Session]
- **Modifications Made**: [Summary of changes]
- **Compatibility**: [Compatibility statement]

### License Text

[Complete license text here]
```

#### Attribution Types Available:
- **Module-level**: For entire files with ported code
- **Function/method**: For specific functions from third-party sources
- **Class**: For classes inspired by other implementations
- **Protocol**: For RFC-based protocol implementations
- **s3270 compatibility**: For code maintaining s3270 compatibility
- **EBCDIC codec**: For encoding/decoding implementations

See `tools/ATTRIBUTION_GUIDE.md` for comprehensive documentation.

### 3.3 THIRD_PARTY_NOTICES.md Updates

All ported code must be documented in `THIRD_PARTY_NOTICES.md`:

1. **Add new section** for the ported code
2. **Include complete license text** (not just a reference)
3. **Document integration points** and modifications
4. **Update contributor guidelines** if needed
5. **Maintain chronological order** of additions

## 4. Code Quality Standards

### 4.1 Architecture Compliance

Ported code must comply with Pure3270's architecture:

#### Protocol Layer (`pure3270/protocol/`):
- TN3270/TN3270E protocol implementations
- Telnet option negotiation
- Data stream processing
- Must follow RFC 1576/2355 specifications

#### Emulation Layer (`pure3270/emulation/`):
- Screen buffer management
- EBCDIC encoding/decoding
- Field attribute handling
- Must maintain 3270 emulation fidelity

#### Session Layer (`pure3270/`):
- Session management
- Client interfaces
- Must maintain API compatibility

#### Patching Layer (`pure3270/patching/`):
- Compatibility shims
- Must not break existing functionality

### 4.2 Code Style Requirements

All ported code must follow Pure3270's coding standards:

- **Python 3.10+** syntax and features
- **Type hints** for all public functions
- **Docstrings** following Google style
- **Error handling** using Pure3270's exception hierarchy
- **Logging** using Pure3270's logging utilities
- **Async compatibility** where applicable

### 4.3 Testing Requirements

Ported code must include comprehensive tests:

#### Required Test Types:
1. **Unit Tests**: Test individual functions and classes
2. **Integration Tests**: Test interaction with other components
3. **Regression Tests**: Ensure compatibility with existing functionality
4. **Protocol Tests**: Validate against RFC specifications
5. **Edge Case Tests**: Cover error conditions and boundary cases

#### Test Coverage Requirements:
- **Minimum 90%** code coverage for ported code
- **100%** coverage for critical protocol functions
- **Mutation testing** for complex algorithms
- **Property-based testing** where applicable

## 5. Integration Process

### 5.1 Pre-Integration Checklist

Before integrating ported code:

- [ ] **License compatibility** verified
- [ ] **Attribution documentation** complete
- [ ] **Architecture fit** confirmed
- [ ] **Code style** compliance verified
- [ ] **Tests written** and passing
- [ ] **Documentation updated**
- [ ] **Review completed** by maintainers

### 5.2 Integration Workflow

#### Phase 1: Preparation
1. Create feature branch for porting work
2. Set up isolated development environment
3. Implement ported code in isolation
4. Write comprehensive tests
5. Verify code style compliance

#### Phase 2: Attribution
1. Add attribution to ported files
2. Update THIRD_PARTY_NOTICES.md
3. Document integration points
4. Update API documentation

#### Phase 3: Integration
1. Integrate with existing codebase
2. Update import statements
3. Modify interfaces as needed
4. Ensure backward compatibility

#### Phase 4: Validation
1. Run full test suite
2. Verify integration tests pass
3. Check for regressions
4. Validate against real systems

#### Phase 5: Documentation
1. Update API documentation
2. Add usage examples
3. Document any limitations
4. Update migration guides

## 6. Contributor Guidelines for Porting

### 6.1 Porting Proposal Process

#### Step 1: Proposal Submission
Submit a porting proposal including:
- **Rationale**: Why porting is necessary
- **Source Analysis**: Evaluation against decision matrix
- **License Review**: Compatibility assessment
- **Implementation Plan**: High-level integration approach
- **Testing Strategy**: How functionality will be validated

#### Step 2: Community Review
- Present proposal in GitHub issue
- Gather community feedback
- Address concerns and questions
- Revise proposal based on input

#### Step 3: Implementation
- Implement according to approved plan
- Maintain regular communication
- Address review feedback promptly
- Ensure CI/CD compliance

### 6.2 Code Review Requirements

Porting PRs must include:

#### Documentation:
- [ ] **Porting rationale** in PR description
- [ ] **License compatibility** statement
- [ ] **Attribution documentation** complete
- [ ] **Integration impact** assessment
- [ ] **Testing strategy** documented

#### Code Quality:
- [ ] **Type hints** for all public APIs
- [ ] **Docstrings** for all classes/functions
- [ ] **Error handling** using project exceptions
- [ ] **Logging** integration
- [ ] **Async compatibility** where applicable

#### Testing:
- [ ] **Unit tests** for all new functionality
- [ ] **Integration tests** with existing code
- [ ] **Regression tests** for compatibility
- [ ] **Documentation** of test coverage

### 6.3 Maintenance Responsibilities

Contributors porting code are responsible for:

1. **Initial Quality**: Ensuring ported code meets all standards
2. **Documentation**: Complete and accurate documentation
3. **Testing**: Comprehensive test coverage
4. **Maintenance**: Addressing issues in ported code
5. **Updates**: Keeping ported code current with upstream

## 7. Common Porting Scenarios

### 7.1 Protocol Extensions

**When**: Adding support for new 3270 features or TN3270E options

**Guidelines**:
- Must follow RFC specifications
- Include comprehensive protocol tests
- Document any deviations from standards
- Maintain backward compatibility

**Example**:
```python
# Porting TN3270E printer session support
# - Follow RFC 2355 specifications
# - Integrate with existing protocol layer
# - Add comprehensive printer emulation tests
```

### 7.2 Encoding/Decoding Libraries

**When**: Adding support for additional EBCDIC code pages

**Guidelines**:
- Must be optional dependencies
- Include fallback to standard library
- Comprehensive encoding/decoding tests
- Document performance implications

**Example**:
```python
# Porting extended EBCDIC codec
# - Optional dependency with fallback
# - Integrate with emulation/ebcdic.py
# - Add codec validation tests
```

### 7.3 Utility Functions

**When**: Adding specialized 3270 data processing utilities

**Guidelines**:
- Must fit existing architecture layers
- Include performance benchmarks
- Comprehensive unit tests
- Document algorithmic complexity

**Example**:
```python
# Porting 3270 data stream parser
# - Integrate with protocol/data_stream.py
# - Add parsing validation tests
# - Document parsing performance
```

## 8. Quality Assurance

### 8.1 Validation Requirements

All ported code must pass:

#### Functional Validation:
- [ ] **RFC Compliance**: Adherence to relevant RFCs
- [ ] **Compatibility**: Works with existing 3270 systems
- [ ] **Performance**: Meets or exceeds existing implementations
- [ ] **Error Handling**: Proper exception handling

#### Code Quality:
- [ ] **Static Analysis**: Passes all linting checks
- [ ] **Type Checking**: Passes mypy validation
- [ ] **Security**: No security vulnerabilities
- [ ] **Documentation**: Complete API documentation

### 8.2 Performance Requirements

Ported code must meet performance standards:

- **No Performance Regression**: Must not slow down existing functionality
- **Memory Efficiency**: Reasonable memory usage patterns
- **Async Compatibility**: Must work in async contexts
- **Scalability**: Must handle expected load patterns

### 8.3 Security Considerations

Ported code must address security concerns:

- **Input Validation**: All inputs must be validated
- **Buffer Overflows**: Protection against buffer issues
- **Injection Attacks**: Protection against injection vulnerabilities
- **Resource Limits**: Appropriate resource usage limits

## 9. Maintenance and Updates

### 9.1 Ongoing Maintenance

Ported code requires ongoing maintenance:

#### Regular Reviews:
- **Quarterly Reviews**: Assess continued need for ported code
- **Dependency Updates**: Keep dependencies current
- **Security Updates**: Address security vulnerabilities promptly
- **Performance Monitoring**: Track performance impact

#### Update Process:
1. **Monitor Upstream**: Track upstream changes
2. **Evaluate Updates**: Assess need for updates
3. **Test Integration**: Ensure updates don't break functionality
4. **Document Changes**: Update attribution and documentation

### 9.2 Deprecation Process

If ported code becomes obsolete:

1. **Evaluation**: Assess whether code is still needed
2. **Migration Plan**: Plan migration to native implementation
3. **Deprecation Notice**: Announce deprecation timeline
4. **Migration Period**: Allow time for migration
5. **Removal**: Remove code and update documentation

## 10. Decision Trees

### 10.1 Should I Port This Code?

```
Is the functionality essential?
├── YES → Continue evaluation
└── NO → Do not port

↓

Can it be implemented natively?
├── YES → Implement natively
└── NO → Continue evaluation

↓

Is the license compatible?
├── YES → Continue evaluation
└── NO → Cannot port

↓

Does it fit the architecture?
├── YES → Continue evaluation
└── NO → Cannot port

↓

Is maintenance burden acceptable?
├── YES → Proceed with porting
└── NO → Do not port
```

### 10.2 Integration Complexity Assessment

```
How complex is the integration?
├── Simple (single file, clear interface)
│   └── Low risk - proceed
├── Moderate (multiple files, some dependencies)
│   └── Medium risk - careful evaluation needed
└── Complex (major architectural changes)
    └── High risk - consider alternatives
```

## 11. Examples

### 11.1 Successful Porting Example

**Porting EBCDIC Codec Enhancement**:

```markdown
## ebcdic-ext Package Port

**Original Project**: ebcdic-ext
**License**: MIT License
**Integration**: pure3270/emulation/ebcdic.py

### Rationale
Enhanced EBCDIC codec provides better international character support
beyond standard library CP037 codec.

### Changes Made
- Added dynamic import with fallback
- Integrated with existing EBCDIC handling
- Added codec validation tests

### Testing
- 100% test coverage for new codecs
- Integration tests with existing emulation
- Performance benchmarks vs standard library
```

### 11.2 Rejected Porting Example

**Proposed GUI Framework Port**:

```markdown
## tkinter-gui-framework Port - REJECTED

**Original Project**: tkinter-gui-framework
**License**: GPL v3
**Proposed Integration**: New GUI layer

### Rationale for Rejection
- License incompatible with MIT
- Would add significant dependency burden
- Doesn't fit Pure3270's zero-dependency philosophy
- GUI functionality not core to 3270 emulation

### Alternative
Implement simple TUI interface using standard library
curses module if needed.
```

## 12. Contact and Support

### 12.1 Getting Help

For questions about porting guidelines:

- **GitHub Issues**: https://github.com/dtg01100/pure3270/issues
- **Discussions**: https://github.com/dtg01100/pure3270/discussions
- **Maintainer**: David LaFreniere

### 12.2 Reporting Issues

When reporting porting-related issues:

1. **Include context**: What were you trying to port?
2. **License information**: What license does the source code use?
3. **Integration approach**: How were you planning to integrate it?
4. **Error details**: Specific errors or issues encountered
5. **Alternatives considered**: What alternatives did you evaluate?

## 13. Revision History

- **v1.0** (2025-09-23): Initial porting guidelines document
- **Future versions**: Will be updated as porting practices evolve

---

*These guidelines ensure that Pure3270 maintains its commitment to quality, legal compliance, and architectural integrity while allowing for strategic adoption of third-party code when beneficial.*
