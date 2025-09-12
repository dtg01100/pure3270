# System Patterns

## System Architecture
Pure3270 follows a modular architecture with clear separation of concerns:

### Core Components
- **Session Layer**: AsyncSession/Session classes provide user-facing APIs
- **Handler Layer**: TN3270Handler manages connection and protocol flow
- **Protocol Layer**: Negotiator handles TN3270E negotiation, DataStreamParser processes data streams
- **Emulation Layer**: ScreenBuffer manages display state, EBCDICCodec handles character translation
- **Patching Layer**: MonkeyPatchManager enables p3270 compatibility

### Key Technical Decisions
- **Async-First Design**: AsyncSession is the primary interface with sync Session as a wrapper
- **Zero Dependencies**: Uses only Python standard library for maximum portability
- **RFC Compliance**: Prioritizes standards over compatibility with non-compliant implementations
- **Context Managers**: Sessions implement __aenter__/__aexit__ for resource management
- **Logging Integration**: Comprehensive logging for debugging and monitoring

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

## Component Relationships
```
AsyncSession
    ↓
TN3270Handler ←→ Negotiator
    ↓           ↘
DataStreamParser → ScreenBuffer
    ↓
EBCDICCodec
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

### Patching Flow
1. enable_replacement() → MonkeyPatchManager
2. sys.modules patch → Pure3270S3270Wrapper
3. p3270 imports → uses pure3270 internally
