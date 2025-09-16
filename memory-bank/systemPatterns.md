# System Patterns

## System Architecture
Pure3270 follows a modular architecture with clear separation of concerns:

### Core Components
- **Session Layer**: AsyncSession/Session classes provide user-facing APIs
- **Handler Layer**: TN3270Handler manages connection and protocol flow
- **Protocol Layer**: Negotiator handles TN3270E negotiation, DataStreamParser processes data streams
- **Emulation Layer**: ScreenBuffer manages display state, EBCDICCodec handles character translation
- **Patching Layer**: MonkeyPatchManager enables p3270 compatibility

### Enhancement Architecture
The planned enhancements will add several new layers:

#### Quality Assurance Layer
- **Static Analysis Integration**: mypy, bandit, pylint for comprehensive code quality checks
- **Property-Based Testing**: Hypothesis framework for automatic edge case discovery
- **Pre-commit Hooks**: Quality checks that run before code commits
- **CI/CD Integration**: Automated workflows that enforce quality standards

#### Observability Layer
- **Enhanced Exception Handling**: Contextual exception classes with detailed error information
- **Structured Logging**: JSON-formatted logs for better searchability and analysis
- **API Documentation**: Sphinx-generated documentation for all public APIs

#### Automation Layer
- **Python Version Automation**: Automated testing and compatibility management across Python versions
- **AI-Assisted Development**: Copilot integration for rapid issue analysis and resolution
- **Regression Detection**: Automated systems for detecting and resolving compatibility issues

### Key Technical Decisions
- **Async-First Design**: AsyncSession is the primary interface with sync Session as a wrapper
- **Zero Dependencies**: Uses only Python standard library for maximum portability
- **RFC Compliance**: Prioritizes standards over compatibility with non-compliant implementations
- **Context Managers**: Sessions implement __aenter__/__aexit__ for resource management
- **Logging Integration**: Comprehensive logging for debugging and monitoring
- **Enhancement Integration**: Planned enhancements will integrate seamlessly with existing patterns

## Design Patterns

### Parser Pattern
DataStreamParser uses a dispatch table to handle different 3270 orders and data types:
```python
order_handlers = {
    WCC_ORDER: self._handle_wcc,
    SBA_ORDER: self._handle_sba,
    # ...
}
```

### Handler Pattern
TN3270Handler coordinates protocol operations:
- Negotiation through Negotiator
- Data parsing through DataStreamParser
- Screen updates through ScreenBuffer

### Session Pattern
Dual async/sync APIs with consistent interfaces:
- AsyncSession for asyncio applications
- Session as synchronous wrapper using asyncio.run()

### Factory Pattern
Session creation with automatic handler instantiation:
```python
async def create_session(self) -> AsyncSession:
    handler = TN3270Handler(...)
    return AsyncSession(handler)
```

### Enhancement Integration Patterns
The planned enhancements will follow established patterns:

#### Quality Gate Pattern
Pre-commit hooks and CI/CD workflows will enforce quality standards:
```python
# Pre-commit hook configuration
repos:
  - repo: https://github.com/pre-commit/mirrors-mypy
    hooks:
      - id: mypy
  - repo: https://github.com/PyCQA/bandit
    hooks:
      - id: bandit
```

#### Exception Enhancement Pattern
Enhanced exceptions will provide contextual information:
```python
class EnhancedSessionError(SessionError):
    def __init__(self, message, context=None, original_exception=None):
        super().__init__(message)
        self.context = context or {}
        self.original_exception = original_exception
```

#### Logging Enhancement Pattern
Structured logging will use JSON formatting:
```python
logger.info("Session connected", extra={
    'session_id': session_id,
    'host': host,
    'port': port,
    'mode': 'TN3270E' if tn3270e_mode else 'TN3270'
})
```

## Component Relationships
```
AsyncSession
    ↓
TN3270Handler ←→ Negotiator
    ↓           ↘
DataStreamParser → ScreenBuffer
    ↓
EBCDICCodec

[Planned Enhancements Layer]
    ↓
Quality Assurance ←→ Observability
    ↓
Automation ←→ AI Assistance
```

## Protocol Flows

### Connection Flow
1. Session.connect() → TN3270Handler.connect()
2. Telnet negotiation → Negotiator.negotiate()
3. TN3270E subnegotiation → device type and functions
4. Session ready for data exchange

### Data Processing Flow
1. Raw bytes received → TN3270Handler
2. Data type identification → TN3270EHeader
3. Stream parsing → DataStreamParser
4. Screen/field updates → ScreenBuffer
5. EBCDIC translation → display ready

### Enhancement Processing Flow
1. Code changes → Pre-commit hooks
2. Quality checks → Static analysis tools
3. Testing → Property-based and unit tests
4. Documentation → Sphinx generation
5. Logging → Structured JSON output
6. Compatibility → Python version automation

### Patching Flow
1. enable_replacement() → MonkeyPatchManager
2. sys.modules patch → Pure3270S3270Wrapper
3. p3270 imports → uses pure3270 internally
