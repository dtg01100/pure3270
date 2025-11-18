Advanced Patterns
==================

This section covers advanced usage patterns, optimization techniques, and complex scenarios for Pure3270 implementation.

For practical examples of the patterns described here, see:

* :doc:`examples` - Basic usage examples and API demonstrations
* :doc:`protocol_examples` - Detailed protocol-level examples
* :doc:`integration_scenarios` - Real-world enterprise integration patterns

Complex Session Management Patterns
------------------------------------

Advanced session lifecycle management with resource pooling and state tracking. For connection pooling implementations, see :doc:`examples` section on connection management.

.. code-block:: python

    import asyncio
    import time
    from dataclasses import dataclass
    from typing import Dict, List, Optional, Set
    from contextlib import asynccontextmanager
    from pure3270 import AsyncSession, setup_logging
    from pure3270.exceptions import ConnectionError, TN3270Error

    @dataclass
    class SessionMetrics:
        """Track session performance and usage metrics."""
        created_at: float
        last_activity: float
        request_count: int
        error_count: int
        total_bytes_sent: int
        total_bytes_received: int
        average_response_time: float
        peak_memory_usage: int

    class AdvancedSessionManager:
        """
        Advanced session management with comprehensive monitoring,
        resource pooling, and automatic recovery.
        """

        def __init__(self, hosts: Dict[str, dict], max_sessions_per_host: int = 5):
            self.hosts = hosts  # {host: {"port": 23, "ssl": True, "terminal": "IBM-3278-2"}}
            self.max_sessions_per_host = max_sessions_per_host
            self.sessions: Dict[str, List[AsyncSession]] = {}
            self.metrics: Dict[str, SessionMetrics] = {}
            self.active_sessions: Set[AsyncSession] = set()
            self._monitoring_task = None
            self._lock = asyncio.Lock()

        async def start_monitoring(self):
            """Start background monitoring and maintenance tasks."""

            async def monitor_sessions():
                while True:
                    try:
                        await self._health_check_all_sessions()
                        await self._cleanup_idle_sessions()
                        await self._rebalance_session_pool()
                        await asyncio.sleep(30)  # Check every 30 seconds
                    except Exception as e:
                        print(f"Monitoring error: {e}")
                        await asyncio.sleep(5)

            self._monitoring_task = asyncio.create_task(monitor_sessions())

        async def stop_monitoring(self):
            """Stop monitoring tasks and cleanup."""
            if self._monitoring_task:
                self._monitoring_task.cancel()
                try:
                    await self._monitoring_task
                except asyncio.CancelledError:
                    pass

        async def get_session(self, host: str = None) -> AsyncSession:
            """
            Get an active session with automatic session management.

            Args:
                host: Specific host to get session from, or None for auto-select
            """
            if host is None:
                # Auto-select host with best metrics
                host = await self._select_best_host()

            if host not in self.hosts:
                raise ValueError(f"Unknown host: {host}")

            async with self._lock:
                # Check existing sessions
                if host in self.sessions and self.sessions[host]:
                    session = self.sessions[host].pop(0)

                    # Validate session health
                    if await self._is_session_healthy(session):
                        self.active_sessions.add(session)
                        await self._update_metrics(session, "checkout")
                        return session
                    else:
                        # Session is unhealthy, close it
                        await self._close_session(session)

            # Create new session
            return await self._create_session(host)

        async def return_session(self, session: AsyncSession):
            """Return session to pool with health validation."""
            host = None
            for h, sessions in self.sessions.items():
                if session in sessions:
                    host = h
                    break

            if host is None:
                # Session not from pool, close it
                await self._close_session(session)
                return

            async with self._lock:
                self.active_sessions.discard(session)

                # Validate before returning to pool
                if await self._is_session_healthy(session):
                    if len(self.sessions.get(host, [])) < self.max_sessions_per_host:
                        self.sessions.setdefault(host, []).append(session)
                        await self._update_metrics(session, "return")
                    else:
                        # Pool full, close session
                        await self._close_session(session)
                else:
                    await self._close_session(session)

        async def _create_session(self, host: str) -> AsyncSession:
            """Create a new session with proper initialization."""
            config = self.hosts[host]

            session = AsyncSession(terminal_type=config.get("terminal", "IBM-3278-2"))

            try:
                await session.connect(
                    host,
                    port=config.get("port", 23),
                    ssl_context=config.get("ssl_context", None)
                )

                # Initialize session metrics
                self.metrics[id(session)] = SessionMetrics(
                    created_at=time.time(),
                    last_activity=time.time(),
                    request_count=0,
                    error_count=0,
                    total_bytes_sent=0,
                    total_bytes_received=0,
                    average_response_time=0.0,
                    peak_memory_usage=0
                )

                self.active_sessions.add(session)
                return session

            except Exception as e:
                await self._close_session(session)
                raise ConnectionError(f"Failed to create session for {host}: {e}")

        async def _close_session(self, session: AsyncSession):
            """Safely close a session and cleanup."""
            try:
                await session.close()
            except Exception as e:
                print(f"Error closing session: {e}")
            finally:
                self.active_sessions.discard(session)
                self.metrics.pop(id(session), None)

        async def _is_session_healthy(self, session: AsyncSession) -> bool:
            """Perform comprehensive health check on session."""
            try:
                # Quick response test
                start_time = time.time()
                await asyncio.wait_for(session.read(), timeout=2.0)
                response_time = time.time() - start_time

                # Check response time is reasonable
                if response_time > 5.0:
                    return False

                return True

            except Exception:
                return False

        async def _health_check_all_sessions(self):
            """Perform health checks on all sessions in pool."""
            async with self._lock:
                for host, sessions in self.sessions.items():
                    healthy_sessions = []
                    for session in sessions:
                        if await self._is_session_healthy(session):
                            healthy_sessions.append(session)
                        else:
                            await self._close_session(session)
                    self.sessions[host] = healthy_sessions

        async def _cleanup_idle_sessions(self):
            """Remove idle sessions to free resources."""
            current_time = time.time()
            idle_threshold = 300  # 5 minutes

            async with self._lock:
                for host, sessions in list(self.sessions.items()):
                    active_sessions = []
                    for session in sessions:
                        metrics = self.metrics.get(id(session))
                        if metrics:
                            if current_time - metrics.last_activity > idle_threshold:
                                # Remove from pool but keep if still in use
                                if session not in self.active_sessions:
                                    await self._close_session(session)
                                else:
                                    active_sessions.append(session)
                            else:
                                active_sessions.append(session)
                    self.sessions[host] = active_sessions

        async def _rebalance_session_pool(self):
            """Rebalance session distribution across hosts."""
            # Implementation for load balancing across multiple hosts
            pass

        async def _select_best_host(self) -> str:
            """Select the host with the best performance metrics."""
            best_host = None
            best_score = float('inf')

            for host, sessions in self.sessions.items():
                # Simple scoring based on active session count
                active_count = len([s for s in sessions if s in self.active_sessions])
                if active_count < best_score:
                    best_score = active_count
                    best_host = host

            return best_host or list(self.hosts.keys())[0]

        async def _update_metrics(self, session: AsyncSession, operation: str):
            """Update session metrics based on operation."""
            metrics = self.metrics.get(id(session))
            if metrics:
                if operation == "checkout":
                    metrics.request_count += 1
                    metrics.last_activity = time.time()

        async def get_statistics(self) -> Dict:
            """Get comprehensive session pool statistics."""
            async with self._lock:
                stats = {
                    "total_sessions": sum(len(sessions) for sessions in self.sessions.values()),
                    "active_sessions": len(self.active_sessions),
                    "hosts": {}
                }

                for host, sessions in self.sessions.items():
                    host_stats = {
                        "available_sessions": len(sessions),
                        "active_sessions": len([s for s in sessions if s in self.active_sessions])
                    }

                    # Add metrics for this host's sessions
                    for session in sessions:
                        if id(session) in self.metrics:
                            metrics = self.metrics[id(session)]
                            if "session_metrics" not in host_stats:
                                host_stats["session_metrics"] = []
                            host_stats["session_metrics"].append({
                                "requests": metrics.request_count,
                                "errors": metrics.error_count,
                                "uptime": time.time() - metrics.created_at
                            })

                    stats["hosts"][host] = host_stats

                return stats

    # Context manager for automatic session lifecycle management
    @asynccontextmanager
    async def managed_session(manager: AdvancedSessionManager, host: str = None):
        """
        Context manager that automatically handles session checkout/checkin.

        Usage:
            async with managed_session(session_manager, "mainframe.example.com") as session:
                await session.string("TEST")
                await session.key("Enter")
        """
        session = None
        try:
            session = await manager.get_session(host)
            yield session
        finally:
            if session:
                await manager.return_session(session)

    # Example usage
    async def session_management_example():
        """Demonstrate advanced session management patterns."""

        # Configure multiple hosts
        hosts = {
            "mainframe1.example.com": {"port": 23, "terminal": "IBM-3278-4"},
            "mainframe2.example.com": {"port": 23, "terminal": "IBM-3279-3"},
            "printerhost.example.com": {"port": 23, "terminal": "IBM-3281-1"}
        }

        manager = AdvancedSessionManager(hosts)
        await manager.start_monitoring()

        try:
            # Use managed session
            async with managed_session(manager, "mainframe1.example.com") as session:
                await session.string("HELLO")
                await session.key("Enter")
                response = session.ascii(session.read())
                print(f"Response: {response}")

            # Get statistics
            stats = await manager.get_statistics()
            print(f"Session pool statistics: {stats}")

        finally:
            await manager.stop_monitoring()

Error Handling and Recovery Strategies
---------------------------------------

Comprehensive error handling and recovery patterns for production environments. For basic error handling examples, see the :doc:`examples` section on error handling patterns.

.. code-block:: python

    import asyncio
    import logging
    import traceback
    from enum import Enum
    from typing import Callable, Optional, Dict, Any
    from dataclasses import dataclass
    from pure3270 import AsyncSession
    from pure3270.exceptions import TN3270Error, ConnectionError, TimeoutError

    class ErrorSeverity(Enum):
        """Error severity levels for handling strategy determination."""
        LOW = "low"          # Non-critical, can continue
        MEDIUM = "medium"    # May require recovery
        HIGH = "high"        # Critical, needs immediate attention
        CRITICAL = "critical" # Fatal, terminate session

    class RecoveryStrategy(Enum):
        """Available recovery strategies."""
        RETRY = "retry"
        RECONNECT = "reconnect"
        SWITCH_HOST = "switch_host"
        ESCALATE = "escalate"
        TERMINATE = "terminate"

    @dataclass
    class ErrorContext:
        """Context information for error handling decisions."""
        error_type: type
        error_message: str
        session_state: str
        host: str
        operation: str
        timestamp: float
        retry_count: int = 0

    @dataclass
    class RecoveryConfig:
        """Configuration for error recovery mechanisms."""
        max_retries: int = 3
        retry_delay: float = 1.0
        backoff_multiplier: float = 2.0
        max_reconnect_attempts: int = 5
        failover_hosts: list = None
        circuit_breaker_threshold: int = 5
        circuit_breaker_timeout: float = 300.0

    class CircuitBreaker:
        """Circuit breaker pattern for preventing cascade failures."""

        def __init__(self, failure_threshold: int, recovery_timeout: float):
            self.failure_threshold = failure_threshold
            self.recovery_timeout = recovery_timeout
            self.failure_count = 0
            self.last_failure_time = 0
            self.state = "closed"  # closed, open, half-open

        def can_execute(self) -> bool:
            """Check if operation can be executed."""
            if self.state == "closed":
                return True
            elif self.state == "open":
                if time.time() - self.last_failure_time >= self.recovery_timeout:
                    self.state = "half-open"
                    return True
                return False
            else:  # half-open
                return True

        def record_success(self):
            """Record successful operation."""
            self.failure_count = 0
            self.state = "closed"

        def record_failure(self):
            """Record failed operation."""
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = "open"

    class AdvancedErrorHandler:
        """Advanced error handling with automatic recovery strategies."""

        def __init__(self, recovery_config: RecoveryConfig = None):
            self.config = recovery_config or RecoveryConfig()
            self.circuit_breakers: Dict[str, CircuitBreaker] = {}
            self.error_callbacks: Dict[type, Callable] = {}
            self.recovery_strategies: Dict[ErrorSeverity, RecoveryStrategy] = {
                ErrorSeverity.LOW: RecoveryStrategy.RETRY,
                ErrorSeverity.MEDIUM: RecoveryStrategy.RETRY,
                ErrorSeverity.HIGH: RecoveryStrategy.RECONNECT,
                ErrorSeverity.CRITICAL: RecoveryStrategy.TERMINATE
            }

        async def handle_error(self, error: Exception, context: ErrorContext) -> bool:
            """
            Handle error with appropriate recovery strategy.

            Returns:
                bool: True if error was handled successfully, False otherwise
            """
            severity = self._determine_severity(error, context)
            strategy = self.recovery_strategies.get(severity, RecoveryStrategy.TERMINATE)

            logging.error(f"Error: {error}, Severity: {severity}, Strategy: {strategy}")

            try:
                if strategy == RecoveryStrategy.RETRY:
                    return await self._handle_with_retry(error, context, severity)
                elif strategy == RecoveryStrategy.RECONNECT:
                    return await self._handle_with_reconnect(error, context, severity)
                elif strategy == RecoveryStrategy.SWITCH_HOST:
                    return await self._handle_with_failover(error, context, severity)
                elif strategy == RecoveryStrategy.ESCALATE:
                    await self._handle_with_escalation(error, context, severity)
                    return False
                else:  # TERMINATE
                    return False

            except Exception as recovery_error:
                logging.error(f"Recovery failed: {recovery_error}")
                return False

        def _determine_severity(self, error: Exception, context: ErrorContext) -> ErrorSeverity:
            """Determine error severity based on error type and context."""
            if isinstance(error, ConnectionError):
                return ErrorSeverity.HIGH
            elif isinstance(error, TimeoutError):
                return ErrorSeverity.MEDIUM
            elif isinstance(error, TN3270Error):
                if "protocol" in str(error).lower():
                    return ErrorSeverity.HIGH
                else:
                    return ErrorSeverity.MEDIUM
            elif isinstance(error, KeyboardInterrupt):
                return ErrorSeverity.CRITICAL
            else:
                return ErrorSeverity.LOW

        async def _handle_with_retry(self, error: Exception, context: ErrorContext,
                                   severity: ErrorSeverity) -> bool:
            """Handle error with retry strategy."""
            max_retries = self.config.max_retries
            delay = self.config.retry_delay

            for attempt in range(max_retries):
                try:
                    if await self._execute_with_circuit_breaker(context.host):
                        return True
                    else:
                        break
                except Exception as e:
                    logging.warning(f"Retry attempt {attempt + 1} failed: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay)
                        delay *= self.config.backoff_multiplier
                    else:
                        # Final retry failed, escalate
                        return await self._handle_with_reconnect(error, context, severity)

            return False

        async def _handle_with_reconnect(self, error: Exception, context: ErrorContext,
                                       severity: ErrorSeverity) -> bool:
            """Handle error with reconnection strategy."""
            for attempt in range(self.config.max_reconnect_attempts):
                try:
                    logging.info(f"Reconnection attempt {attempt + 1}")

                    # Wait before reconnecting
                    if attempt > 0:
                        await asyncio.sleep(self.config.retry_delay * attempt)

                    # Create new session (implementation depends on your session management)
                    new_session = await self._create_new_session(context.host)

                    if new_session:
                        # Test connection
                        await asyncio.wait_for(new_session.read(), timeout=10.0)
                        logging.info("Reconnection successful")
                        return True

                except Exception as e:
                    logging.warning(f"Reconnection attempt {attempt + 1} failed: {e}")

            return False

        async def _handle_with_failover(self, error: Exception, context: ErrorContext,
                                      severity: ErrorSeverity) -> bool:
            """Handle error with host failover strategy."""
            if not self.config.failover_hosts:
                return False

            for failover_host in self.config.failover_hosts:
                try:
                    logging.info(f"Attempting failover to {failover_host}")

                    new_session = await self._create_new_session(failover_host)
                    if new_session:
                        logging.info(f"Failover to {failover_host} successful")
                        return True

                except Exception as e:
                    logging.warning(f"Failover to {failover_host} failed: {e}")

            return False

        async def _handle_with_escalation(self, error: Exception, context: ErrorContext,
                                        severity: ErrorSeverity):
            """Handle error with escalation (alerts, logging, etc.)."""
            logging.critical(f"Critical error requiring escalation: {error}")
            logging.critical(f"Context: {context}")

            # In real implementation, send alerts, create tickets, etc.
            await self._send_alert(error, context)

        async def _execute_with_circuit_breaker(self, host: str) -> bool:
            """Execute operation with circuit breaker protection."""
            if host not in self.circuit_breakers:
                self.circuit_breakers[host] = CircuitBreaker(
                    self.config.circuit_breaker_threshold,
                    self.config.circuit_breaker_timeout
                )

            breaker = self.circuit_breakers[host]

            if not breaker.can_execute():
                logging.warning(f"Circuit breaker open for {host}")
                return False

            try:
                # Execute operation here
                result = True  # Placeholder for actual operation
                breaker.record_success()
                return result
            except Exception as e:
                breaker.record_failure()
                raise e

        async def _create_new_session(self, host: str) -> AsyncSession:
            """Create a new session for reconnection."""
            session = AsyncSession()
            await session.connect(host)
            return session

        async def _send_alert(self, error: Exception, context: ErrorContext):
            """Send alert for critical errors."""
            # Implementation would send alerts via email, Slack, etc.
            logging.critical(f"ALERT: {error} at {context.host} during {context.operation}")

    class ResilientSessionWrapper:
        """Wrapper that adds resilience to existing sessions."""

        def __init__(self, session: AsyncSession, error_handler: AdvancedErrorHandler):
            self.session = session
            self.error_handler = error_handler
            self.operation_retry_map = {
                "read": self._safe_read,
                "write": self._safe_write,
                "connect": self._safe_connect,
                "key": self._safe_key,
                "string": self._safe_string
            }

        def __getattr__(self, name):
            """Proxy attribute access to wrapped session."""
            if name in self.operation_retry_map:
                return self.operation_retry_map[name]
            return getattr(self.session, name)

        async def _safe_read(self, *args, **kwargs):
            """Safe read operation with error handling."""
            context = ErrorContext(
                error_type=type(None),
                error_message="",
                session_state="reading",
                host="unknown",  # Should be populated from session
                operation="read",
                timestamp=time.time()
            )

            try:
                return await self.session.read(*args, **kwargs)
            except Exception as error:
                context.error_type = type(error)
                context.error_message = str(error)

                handled = await self.error_handler.handle_error(error, context)
                if handled:
                    # Retry the operation
                    return await self.session.read(*args, **kwargs)
                else:
                    raise error

        async def _safe_write(self, data: bytes, *args, **kwargs):
            """Safe write operation with error handling."""
            context = ErrorContext(
                error_type=type(None),
                error_message="",
                session_state="writing",
                host="unknown",
                operation="write",
                timestamp=time.time()
            )

            try:
                return await self.session.write(data, *args, **kwargs)
            except Exception as error:
                context.error_type = type(error)
                context.error_message = str(error)

                handled = await self.error_handler.handle_error(error, context)
                if handled:
                    return await self.session.write(data, *args, **kwargs)
                else:
                    raise error

        async def _safe_connect(self, *args, **kwargs):
            """Safe connect operation with error handling."""
            context = ErrorContext(
                error_type=type(None),
                error_message="",
                session_state="connecting",
                host=args[0] if args else "unknown",
                operation="connect",
                timestamp=time.time()
            )

            try:
                return await self.session.connect(*args, **kwargs)
            except Exception as error:
                context.error_type = type(error)
                context.error_message = str(error)

                handled = await self.error_handler.handle_error(error, context)
                if handled:
                    return await self.session.connect(*args, **kwargs)
                else:
                    raise error

        async def _safe_key(self, key: str, *args, **kwargs):
            """Safe key operation with error handling."""
            context = ErrorContext(
                error_type=type(None),
                error_message="",
                session_state="keying",
                host="unknown",
                operation="key",
                timestamp=time.time()
            )

            try:
                return await self.session.key(key, *args, **kwargs)
            except Exception as error:
                context.error_type = type(error)
                context.error_message = str(error)

                handled = await self.error_handler.handle_error(error, context)
                if handled:
                    return await self.session.key(key, *args, **kwargs)
                else:
                    raise error

        async def _safe_string(self, text: str, *args, **kwargs):
            """Safe string operation with error handling."""
            context = ErrorContext(
                error_type=type(None),
                error_message="",
                session_state="string_input",
                host="unknown",
                operation="string",
                timestamp=time.time()
            )

            try:
                return await self.session.string(text, *args, **kwargs)
            except Exception as error:
                context.error_type = type(error)
                context.error_message = str(error)

                handled = await self.error_handler.handle_error(error, context)
                if handled:
                    return await self.session.string(text, *args, **kwargs)
                else:
                    raise error

    # Example usage of advanced error handling
    async def error_handling_example():
        """Demonstrate advanced error handling patterns."""

        # Configure error handling
        recovery_config = RecoveryConfig(
            max_retries=3,
            retry_delay=1.0,
            backoff_multiplier=2.0,
            max_reconnect_attempts=5,
            failover_hosts=["backup1.example.com", "backup2.example.com"]
        )

        error_handler = AdvancedErrorHandler(recovery_config)

        # Create resilient session wrapper
        session = AsyncSession()
        resilient_session = ResilientSessionWrapper(session, error_handler)

        try:
            # Connect with automatic error handling
            await resilient_session.connect('mainframe.example.com')

            # Perform operations with automatic recovery
            await resilient_session.string("LOGON")
            await resilient_session.key("Enter")

            # This will automatically retry and recover from errors
            screen_data = await resilient_session.read()

        except Exception as e:
            print(f"Operation failed after all recovery attempts: {e}")
        finally:
            await session.close()

Performance Optimization Techniques
-----------------------------------

Performance optimization strategies for high-throughput environments. For detailed performance examples and benchmarking, see the :doc:`examples` section on performance optimization.

.. code-block:: python

    import asyncio
    import time
    import gc
    from typing import Dict, List, Optional, Callable
    from dataclasses import dataclass
    from pure3270 import AsyncSession
    from pure3270.emulation.screen_buffer import ScreenBuffer

    @datlass
    class PerformanceMetrics:
        """Performance metrics for optimization analysis."""
        operations_per_second: float
        average_response_time: float
        peak_memory_usage: int
        throughput_bytes_per_second: int
        error_rate: float
        connection_reuse_ratio: float

    class ConnectionPool:
        """Optimized connection pool for high-performance scenarios."""

        def __init__(self, host: str, port: int, min_size: int = 5, max_size: int = 20):
            self.host = host
            self.port = port
            self.min_size = min_size
            self.max_size = max_size
            self.idle_pool: List[AsyncSession] = []
            self.active_sessions: Dict[int, AsyncSession] = {}
            self.in_use: set = set()
            self._lock = asyncio.Lock()
            self._metrics = PerformanceMetrics(0, 0, 0, 0, 0, 0)

        async def get_session(self) -> AsyncSession:
            """Get session from pool with optimization."""
            async with self._lock:
                # Try to reuse idle session
                if self.idle_pool:
                    session = self.idle_pool.pop(0)

                    # Quick health check
                    if await self._quick_health_check(session):
                        return session
                    else:
                        # Session is unhealthy, close it
                        await self._close_session(session)

                # Create new session if pool not at max
                if len(self.active_sessions) + len(self.idle_pool) < self.max_size:
                    session = await self._create_optimized_session()
                    return session

                # Pool at capacity, wait for available session
                return await self._wait_for_session()

        async def return_session(self, session: AsyncSession):
            """Return session to pool with optimization."""
            async with self._lock:
                session_id = id(session)
                self.active_sessions.pop(session_id, None)

                # Only return healthy sessions to pool
                if await self._quick_health_check(session):
                    if len(self.idle_pool) < self.max_size:
                        self.idle_pool.append(session)
                    else:
                        await self._close_session(session)
                else:
                    await self._close_session(session)

        async def _create_optimized_session(self) -> AsyncSession:
            """Create session with performance optimizations."""
            session = AsyncSession()
            session._performance_mode = True

            # Pre-configure for performance
            session._buffer_pool = []
            session._optimization_level = "high"

            await session.connect(self.host, self.port)
            return session

        async def _quick_health_check(self, session: AsyncSession) -> bool:
            """Quick health check for performance."""
            try:
                # Set short timeout for health check
                await asyncio.wait_for(session.read(), timeout=1.0)
                return True
            except:
                return False

        async def _close_session(self, session: AsyncSession):
            """Clean up session resources."""
            try:
                await session.close()
            except:
                pass
            finally:
                # Force garbage collection
                gc.collect()

        async def _wait_for_session(self) -> AsyncSession:
            """Wait for available session from pool."""
            # Implementation would use asyncio.Queue or similar
            # For brevity, just create new session
            return await self._create_optimized_session()

    class ScreenBufferOptimizer:
        """Optimizations for screen buffer operations."""

        def __init__(self):
            self.buffer_cache: Dict[str, ScreenBuffer] = {}
            self.parse_cache: Dict[str, dict] = {}
            self._cache_size_limit = 100

        def optimize_screen_reading(self, session: AsyncSession, operation: Callable):
            """Decorator to optimize screen reading operations."""
            async def wrapper(*args, **kwargs):
                # Use cached screen if available and recent
                cache_key = f"{session.host}:{hash(str(args))}"

                if cache_key in self.buffer_cache:
                    cached_buffer = self.buffer_cache[cache_key]
                    if cached_buffer._timestamp and time.time() - cached_buffer._timestamp < 5.0:
                        return cached_buffer

                # Perform operation
                result = await operation(*args, **kwargs)

                # Cache result if it's a screen buffer
                if hasattr(result, 'to_text'):
                    self._cache_screen_buffer(cache_key, result)

                return result

            return wrapper

        def _cache_screen_buffer(self, key: str, buffer: ScreenBuffer):
            """Cache screen buffer with size management."""
            if len(self.buffer_cache) >= self._cache_size_limit:
                # Remove oldest cache entry
                oldest_key = min(self.buffer_cache.keys(),
                               key=lambda k: self.buffer_cache[k]._timestamp)
                del self.buffer_cache[oldest_key]

            buffer._timestamp = time.time()
            self.buffer_cache[key] = buffer

    class BatchOperationOptimizer:
        """Optimizations for batch operations."""

        def __init__(self, batch_size: int = 10, timeout: float = 0.1):
            self.batch_size = batch_size
            self.timeout = timeout
            self.pending_operations = []

        async def submit_batch(self, operations: List[Callable]):
            """Submit operations for batch processing."""
            for operation in operations:
                task = asyncio.create_task(operation())
                self.pending_operations.append(task)

                if len(self.pending_operations) >= self.batch_size:
                    await self._process_batch()

            # Process remaining operations
            if self.pending_operations:
                await self._process_batch()

        async def _process_batch(self):
            """Process pending operations in batch."""
            if not self.pending_operations:
                return

            # Wait for all operations with timeout
            completed = await asyncio.wait_for(
                asyncio.gather(*self.pending_operations, return_exceptions=True),
                timeout=self.timeout
            )

            # Clear completed operations
            self.pending_operations.clear()

            # Return results
            return completed

    class AsyncBatchedTN3270Client:
        """High-performance batched TN3270 client."""

        def __init__(self, host: str, port: int):
            self.host = host
            self.port = port
            self.pool = ConnectionPool(host, port, min_size=5, max_size=20)
            self.buffer_optimizer = ScreenBufferOptimizer()
            self.batch_optimizer = BatchOperationOptimizer()
            self.metrics = PerformanceMetrics(0, 0, 0, 0, 0, 0)

        async def batch_operations(self, operations: List[dict]) -> List[Any]:
            """
            Execute operations in batch for optimal performance.

            operations: List of dicts with 'type': 'key'|'string'|'read', 'data': value
            """
            session = await self.pool.get_session()

            try:
                # Group operations by type for optimization
                key_operations = []
                string_operations = []
                read_operations = []

                for op in operations:
                    if op['type'] == 'key':
                        key_operations.append(op['data'])
                    elif op['type'] == 'string':
                        string_operations.append(op['data'])
                    elif op['type'] == 'read':
                        read_operations.append(op['data'])

                # Execute batched operations
                results = []

                # Batch key operations
                if key_operations:
                    start_time = time.time()
                    for key in key_operations:
                        await session.key(key)

                    key_time = time.time() - start_time
                    print(f"Executed {len(key_operations)} key operations in {key_time:.3f}s")

                # Batch string operations
                if string_operations:
                    start_time = time.time()
                    for text in string_operations:
                        await session.string(text)

                    string_time = time.time() - start_time
                    print(f"Executed {len(string_operations)} string operations in {string_time:.3f}s")

                # Batch read operations
                if read_operations:
                    start_time = time.time()
                    for _ in read_operations:
                        data = await session.read()
                        results.append(data)

                    read_time = time.time() - start_time
                    print(f"Executed {len(read_operations)} read operations in {read_time:.3f}s")

                return results

            finally:
                await self.pool.return_session(session)

        async def high_throughput_scenario(self, num_operations: int = 1000):
            """Demonstrate high-throughput scenario."""
            start_time = time.time()

            # Create batch operations
            operations = []
            for i in range(num_operations):
                operations.append({
                    'type': 'key',
                    'data': f'Enter' if i % 10 == 0 else 'Tab'
                })

                if i % 20 == 0:  # Add reads periodically
                    operations.append({
                        'type': 'read',
                        'data': None
                    })

            # Execute batch
            results = await self.batch_operations(operations)

            end_time = time.time()
            total_time = end_time - start_time

            # Calculate metrics
            self.metrics.operations_per_second = num_operations / total_time
            self.metrics.average_response_time = total_time / num_operations

            print(f"Performance metrics:")
            print(f"  Operations: {num_operations}")
            print(f"  Total time: {total_time:.3f}s")
            print(f"  Ops/second: {self.metrics.operations_per_second:.1f}")
            print(f"  Avg response: {self.metrics.average_response_time:.4f}s")

    class MemoryOptimizer:
        """Memory usage optimization for large-scale operations."""

        def __init__(self, max_memory_mb: int = 512):
            self.max_memory_bytes = max_memory_mb * 1024 * 1024
            self.session_memory_tracker = {}

        def track_session_memory(self, session: AsyncSession):
            """Track memory usage of a session."""
            import psutil
            import os

            process = psutil.Process(os.getpid())
            session_memory = process.memory_info().rss
            self.session_memory_tracker[id(session)] = session_memory

            if self._should_cleanup():
                self._cleanup_memory()

        def _should_cleanup(self) -> bool:
            """Check if memory cleanup is needed."""
            import psutil
            import os

            current_memory = psutil.Process(os.getpid()).memory_info().rss
            return current_memory > self.max_memory_bytes

        def _cleanup_memory(self):
            """Perform memory cleanup."""
            # Clear caches
            gc.collect()

            # Reset session memory tracker
            self.session_memory_tracker.clear()

    # Example usage of performance optimizations
    async def performance_optimization_example():
        """Demonstrate performance optimization techniques."""

        # Create optimized client
        client = AsyncBatchedTN3270Client('mainframe.example.com')

        # Configure memory optimization
        memory_optimizer = MemoryOptimizer(max_memory_mb=256)

        try:
            # High-throughput scenario
            await client.high_throughput_scenario(1000)

            # Memory tracking
            session = await client.pool.get_session()
            memory_optimizer.track_session_memory(session)
            await client.pool.return_session(session)

        finally:
            # Cleanup
            memory_optimizer._cleanup_memory()
