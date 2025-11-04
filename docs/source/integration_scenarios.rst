Integration Scenarios
======================

This section provides real-world integration examples and production deployment scenarios for Pure3270 in enterprise environments.

Enterprise Integration Examples
--------------------------------

Bank Processing System Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Complete enterprise banking application integration with transaction processing:

.. code-block:: python

    import asyncio
    import json
    import logging
    from datetime import datetime
    from typing import Dict, List, Optional
    from dataclasses import dataclass
    from pure3270 import AsyncSession, setup_logging

    @dataclass
    class Transaction:
        """Banking transaction data structure."""
        transaction_id: str
        account_number: str
        transaction_type: str
        amount: float
        description: str
        timestamp: datetime
        status: str

    class BankingSystemInterface:
        """Interface to mainframe banking system via TN3270."""

        def __init__(self, hosts: List[str], credentials: dict):
            self.hosts = hosts
            self.credentials = credentials
            self.session_manager = None
            self.transaction_logger = logging.getLogger('banking.transactions')
            self.performance_monitor = {}

        async def initialize(self):
            """Initialize banking system connection."""
            setup_logging(level="INFO", component="banking")

            # Initialize session manager with failover
            self.session_manager = await self._create_session_manager()

            # Setup transaction logging
            handler = logging.FileHandler('banking_transactions.log')
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.transaction_logger.addHandler(handler)
            self.transaction_logger.setLevel(logging.INFO)

        async def process_transaction(self, transaction: Transaction) -> bool:
            """
            Process a banking transaction through the mainframe system.

            This represents a real enterprise banking transaction flow.
            """
            session = None
            try:
                # Get session with automatic failover
                session = await self.session_manager.get_session()

                # Log transaction start
                self.transaction_logger.info(
                    f"Starting transaction {transaction.transaction_id} "
                    f"for account {transaction.account_number}"
                )

                # Navigate to transaction entry screen
                await self._navigate_to_transaction_screen(session)

                # Enter transaction details
                success = await self._enter_transaction_data(session, transaction)

                if success:
                    # Submit transaction
                    result = await self._submit_transaction(session, transaction)

                    if result:
                        self.transaction_logger.info(
                            f"Transaction {transaction.transaction_id} completed successfully"
                        )
                        return True
                    else:
                        self.transaction_logger.error(
                            f"Transaction {transaction.transaction_id} failed submission"
                        )
                        return False
                else:
                    self.transaction_logger.error(
                        f"Transaction {transaction.transaction_id} failed data entry"
                    )
                    return False

            except Exception as e:
                self.transaction_logger.error(
                    f"Transaction {transaction.transaction_id} failed with error: {e}"
                )
                return False
            finally:
                if session:
                    await self.session_manager.return_session(session)

        async def _navigate_to_transaction_screen(self, session: AsyncSession):
            """Navigate to the transaction entry screen."""
            # Clear any existing screen
            await session.key("CLEAR")
            await asyncio.sleep(0.5)

            # Navigate to transaction module
            await session.string("TXN")
            await session.key("ENTER")

            # Wait for screen to load
            await asyncio.sleep(1.0)

            # Verify we're on the correct screen
            screen = session.ascii(session.read())
            if "TRANSACTION ENTRY" not in screen.upper():
                raise Exception("Failed to navigate to transaction screen")

        async def _enter_transaction_data(self, session: AsyncSession,
                                        transaction: Transaction) -> bool:
            """Enter transaction data into mainframe screen."""
            try:
                # Enter account number
                await self._enter_field(session, 5, 10, transaction.account_number)

                # Enter transaction type
                await self._enter_field(session, 6, 10, transaction.transaction_type)

                # Enter amount (formatted)
                amount_str = f"{transaction.amount:.2f}"
                await self._enter_field(session, 7, 10, amount_str)

                # Enter description
                await self._enter_field(session, 8, 10, transaction.description[:30])

                return True

            except Exception as e:
                self.transaction_logger.error(f"Data entry failed: {e}")
                return False

        async def _enter_field(self, session: AsyncSession, row: int,
                             col: int, value: str):
            """Enter value into specific screen field."""
            # Position cursor
            await self._position_cursor(session, row, col)

            # Clear field
            await session.key("CLEAR")
            await asyncio.sleep(0.1)

            # Enter value
            await session.string(value)

        async def _position_cursor(self, session: AsyncSession, row: int, col: int):
            """Position cursor at specific screen location."""
            # Implementation depends on screen navigation
            # This is a simplified version
            for _ in range(row):
                await session.key("DOWN")
            for _ in range(col):
                await session.key("RIGHT")

        async def _submit_transaction(self, session: AsyncSession,
                                    transaction: Transaction) -> bool:
            """Submit transaction and verify result."""
            # Submit
            await session.key("ENTER")
            await asyncio.sleep(2.0)

            # Read response
            response = session.ascii(session.read())

            # Check for success/error messages
            if "TRANSACTION COMPLETED" in response.upper():
                return True
            elif "ERROR" in response.upper():
                # Log error details
                error_msg = self._extract_error_message(response)
                self.transaction_logger.error(f"Transaction error: {error_msg}")
                return False
            else:
                # Unknown response, treat as error
                return False

        def _extract_error_message(self, screen_text: str) -> str:
            """Extract error message from screen text."""
            lines = screen_text.split('\n')
            for line in lines:
                if "ERROR" in line.upper():
                    return line.strip()
            return "Unknown error"

        async def batch_process_transactions(self, transactions: List[Transaction]) -> Dict[str, bool]:
            """Process multiple transactions in batch for efficiency."""
            results = {}

            # Group transactions by type for optimization
            transaction_groups = {}
            for transaction in transactions:
                ttype = transaction.transaction_type
                if ttype not in transaction_groups:
                    transaction_groups[ttype] = []
                transaction_groups[ttype].append(transaction)

            # Process each group
            for ttype, group_transactions in transaction_groups.items():
                self.transaction_logger.info(
                    f"Processing {len(group_transactions)} transactions of type {ttype}"
                )

                for transaction in group_transactions:
                    success = await self.process_transaction(transaction)
                    results[transaction.transaction_id] = success

                    # Small delay to avoid overwhelming mainframe
                    await asyncio.sleep(0.1)

            return results

        async def close(self):
            """Cleanup banking system connection."""
            if self.session_manager:
                await self.session_manager.stop()

    class HighAvailabilityBankingSystem:
        """High-availability banking system with multiple mainframe connections."""

        def __init__(self, primary_hosts: List[str], backup_hosts: List[str]):
            self.primary_interface = BankingSystemInterface(primary_hosts, {})
            self.backup_interface = BankingSystemInterface(backup_hosts, {})
            self.is_primary_active = True
            self.failover_threshold = 3

        async def initialize(self):
            """Initialize both primary and backup systems."""
            try:
                await self.primary_interface.initialize()
                await self.backup_interface.initialize()
                print("High-availability banking system initialized")
            except Exception as e:
                print(f"Initialization failed: {e}")
                raise

        async def process_transaction_with_failover(self, transaction: Transaction) -> bool:
            """Process transaction with automatic failover capability."""
            # Try primary system first
            if self.is_primary_active:
                try:
                    success = await self.primary_interface.process_transaction(transaction)
                    if success:
                        return True
                    else:
                        # Check if we should failover
                        if not await self._check_primary_health():
                            await self._perform_failover()
                            return await self._retry_with_backup(transaction)
                except Exception as e:
                    print(f"Primary system failed: {e}")
                    await self._perform_failover()
                    return await self._retry_with_backup(transaction)
            else:
                # Use backup system
                return await self._retry_with_backup(transaction)

        async def _check_primary_health(self) -> bool:
            """Check if primary system is healthy."""
            try:
                session = await self.primary_interface.session_manager.get_session()
                await asyncio.wait_for(session.read(), timeout=5.0)
                await self.primary_interface.session_manager.return_session(session)
                return True
            except:
                return False

        async def _perform_failover(self):
            """Perform failover to backup system."""
            print("Performing failover to backup system")
            self.is_primary_active = False

            # Log failover event
            logging.info("Primary system failover completed")

        async def _retry_with_backup(self, transaction: Transaction) -> bool:
            """Retry transaction with backup system."""
            try:
                return await self.backup_interface.process_transaction(transaction)
            except Exception as e:
                print(f"Backup system failed: {e}")
                return False

    # Example usage
    async def banking_system_example():
        """Demonstrate enterprise banking system integration."""

        # Configure banking system
        primary_hosts = ["mainframe1.bank.com", "mainframe2.bank.com"]
        backup_hosts = ["backup-mainframe.bank.com"]

        ha_system = HighAvailabilityBankingSystem(primary_hosts, backup_hosts)
        await ha_system.initialize()

        try:
            # Create sample transactions
            transactions = [
                Transaction(
                    transaction_id="TXN001",
                    account_number="1234567890",
                    transaction_type="DEPOSIT",
                    amount=1000.00,
                    description="Customer deposit",
                    timestamp=datetime.now(),
                    status="PENDING"
                ),
                Transaction(
                    transaction_id="TXN002",
                    account_number="0987654321",
                    transaction_type="WITHDRAWAL",
                    amount=500.00,
                    description="Cash withdrawal",
                    timestamp=datetime.now(),
                    status="PENDING"
                )
            ]

            # Process transactions with failover
            for transaction in transactions:
                success = await ha_system.process_transaction_with_failover(transaction)
                print(f"Transaction {transaction.transaction_id}: {'SUCCESS' if success else 'FAILED'}")

        finally:
            await ha_system.primary_interface.close()
            await ha_system.backup_interface.close()

Multi-Session Management
------------------------

Enterprise Multi-Host Session Management
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Managing multiple mainframe connections with load balancing and session affinity:

.. code-block:: python

    import asyncio
    import hashlib
    from typing import Dict, List, Set, Optional
    from dataclasses import dataclass
    from enum import Enum
    from pure3270 import AsyncSession, setup_logging

    class SessionRole(Enum):
        """Define session roles for different operations."""
        READ_ONLY = "read"
        TRANSACTIONAL = "write"
        BATCH = "batch"
        ADMIN = "admin"
        PRINTER = "printer"

    class HostType(Enum):
        """Define different types of mainframe hosts."""
        PRODUCTION = "production"
        STAGING = "staging"
        DEVELOPMENT = "development"
        ARCHIVE = "archive"

    @dataclass
    class HostConfig:
        """Configuration for mainframe host."""
        host: str
        port: int
        host_type: HostType
        terminal_type: str = "IBM-3278-4"
        max_sessions: int = 10
        timeout: float = 30.0
        ssl_context: Optional[dict] = None

    @dataclass
    class SessionInfo:
        """Information about active session."""
        session_id: str
        host_config: HostConfig
        role: SessionRole
        created_at: float
        last_activity: float
        active: bool = True

    class EnterpriseSessionManager:
        """Enterprise-grade session manager with multiple host support."""

        def __init__(self):
            self.hosts: Dict[str, HostConfig] = {}
            self.sessions: Dict[str, SessionInfo] = {}
            self.session_pools: Dict[str, List[SessionInfo]] = {}
            self.active_sessions: Dict[str, AsyncSession] = {}
            self._lock = asyncio.Lock()
            self._health_monitor_task = None

        async def add_host(self, host_config: HostConfig):
            """Add a mainframe host to the manager."""
            self.hosts[host_config.host] = host_config
            self.session_pools[host_config.host] = []
            print(f"Added host: {host_config.host} ({host_config.host_type.value})")

        async def get_session(self, host: str = None, role: SessionRole = SessionRole.TRANSACTIONAL) -> AsyncSession:
            """
            Get a session for specific host and role.

            Uses load balancing and session affinity for optimal performance.
            """
            if host is None:
                host = await self._select_optimal_host(role)

            if host not in self.hosts:
                raise ValueError(f"Unknown host: {host}")

            host_config = self.hosts[host]

            async with self._lock:
                # Check for available session in pool
                available_sessions = [s for s in self.session_pools[host]
                                    if s.active and s.role == role]

                if available_sessions:
                    # Return most recently used session
                    session_info = min(available_sessions, key=lambda s: s.last_activity)
                    async_session = self.active_sessions[session_info.session_id]

                    # Update activity tracking
                    session_info.last_activity = asyncio.get_event_loop().time()
                    return async_session

                # Create new session if under limit
                current_sessions = len([s for s in self.sessions.values()
                                      if s.host_config.host == host and s.active])

                if current_sessions < host_config.max_sessions:
                    return await self._create_session(host, role)

                # Pool full, wait for available session
                return await self._wait_for_available_session(host, role)

        async def _select_optimal_host(self, role: SessionRole) -> str:
            """Select optimal host based on role and load."""
            suitable_hosts = []

            for host, config in self.hosts.items():
                # Filter by role requirements
                if self._host_suitable_for_role(config, role):
                    current_load = len([s for s in self.sessions.values()
                                      if s.host_config.host == host and s.active])

                    suitable_hosts.append((host, current_load, config))

            if not suitable_hosts:
                raise ValueError(f"No suitable host found for role {role}")

            # Select host with lowest load
            optimal_host = min(suitable_hosts, key=lambda x: x[1])
            return optimal_host[0]

        def _host_suitable_for_role(self, config: HostConfig, role: SessionRole) -> bool:
            """Check if host is suitable for the given role."""
            if role == SessionRole.READ_ONLY:
                return True
            elif role == SessionRole.TRANSACTIONAL:
                return config.host_type in [HostType.PRODUCTION, HostType.STAGING]
            elif role == SessionRole.BATCH:
                return config.host_type in [HostType.PRODUCTION, HostType.STAGING, HostType.DEVELOPMENT]
            elif role == SessionRole.ADMIN:
                return config.host_type == HostType.PRODUCTION
            else:
                return False

        async def _create_session(self, host: str, role: SessionRole) -> AsyncSession:
            """Create new session for host and role."""
            host_config = self.hosts[host]

            session = AsyncSession(terminal_type=host_config.terminal_type)
            await session.connect(host, port=host_config.port, ssl_context=host_config.ssl_context)

            # Generate session ID
            session_id = hashlib.md5(f"{host}:{role}:{asyncio.get_event_loop().time()}".encode()).hexdigest()[:8]

            # Track session info
            session_info = SessionInfo(
                session_id=session_id,
                host_config=host_config,
                role=role,
                created_at=asyncio.get_event_loop().time(),
                last_activity=asyncio.get_event_loop().time()
            )

            async with self._lock:
                self.sessions[session_id] = session_info
                self.session_pools[host].append(session_info)
                self.active_sessions[session_id] = session

            print(f"Created {role.value} session {session_id} for {host}")
            return session

        async def return_session(self, session: AsyncSession):
            """Return session to pool."""
            session_id = None
            for sid, s in self.active_sessions.items():
                if s == session:
                    session_id = sid
                    break

            if session_id:
                async with self._lock:
                    session_info = self.sessions.get(session_id)
                    if session_info:
                        session_info.last_activity = asyncio.get_event_loop().time()
                        print(f"Returned {session_info.role.value} session {session_id}")

        async def _wait_for_available_session(self, host: str, role: SessionRole) -> AsyncSession:
            """Wait for available session in pool."""
            # This is a simplified implementation
            # In production, would use asyncio.Queue or similar
            for _ in range(30):  # Wait up to 30 seconds
                await asyncio.sleep(1)
                try:
                    return await self.get_session(host, role)
                except:
                    continue
            raise TimeoutError("No session available")

        async def start_health_monitoring(self):
            """Start background health monitoring."""
            async def monitor():
                while True:
                    try:
                        await self._check_all_sessions()
                        await asyncio.sleep(30)  # Check every 30 seconds
                    except Exception as e:
                        print(f"Health monitor error: {e}")
                        await asyncio.sleep(5)

            self._health_monitor_task = asyncio.create_task(monitor())

        async def _check_all_sessions(self):
            """Check health of all active sessions."""
            async with self._lock:
                unhealthy_sessions = []

                for session_id, session_info in list(self.sessions.items()):
                    if not session_info.active:
                        continue

                    session = self.active_sessions.get(session_id)
                    if session:
                        try:
                            # Quick health check
                            await asyncio.wait_for(session.read(), timeout=2.0)
                        except:
                            unhealthy_sessions.append(session_id)

                # Remove unhealthy sessions
                for session_id in unhealthy_sessions:
                    await self._cleanup_session(session_id)

        async def _cleanup_session(self, session_id: str):
            """Cleanup unhealthy session."""
            session_info = self.sessions.get(session_id)
            if session_info:
                session_info.active = False

                session = self.active_sessions.pop(session_id, None)
                if session:
                    try:
                        await session.close()
                    except:
                        pass

                # Remove from pool
                host = session_info.host_config.host
                if host in self.session_pools:
                    self.session_pools[host] = [s for s in self.session_pools[host]
                                              if s.session_id != session_id]

                print(f"Cleaned up unhealthy session {session_id}")

    class SessionAffinityManager:
        """Manage session affinity for user sessions."""

        def __init__(self, session_manager: EnterpriseSessionManager):
            self.session_manager = session_manager
            self.user_sessions: Dict[str, str] = {}  # user_id -> session_id
            self._lock = asyncio.Lock()

        async def get_session_for_user(self, user_id: str, preferred_host: str = None) -> AsyncSession:
            """Get session with affinity for specific user."""
            async with self._lock:
                # Check if user already has a session
                if user_id in self.user_sessions:
                    session_id = self.user_sessions[user_id]
                    session_info = self.session_manager.sessions.get(session_id)

                    if session_info and session_info.active:
                        return self.session_manager.active_sessions[session_id]
                    else:
                        # Clean up old session
                        self.user_sessions.pop(user_id, None)

                # Create new session with user affinity
                if preferred_host:
                    session = await self.session_manager.get_session(preferred_host, SessionRole.TRANSACTIONAL)
                else:
                    # Use consistent hashing to select host
                    host = self._hash_to_host(user_id)
                    session = await self.session_manager.get_session(host, SessionRole.TRANSACTIONAL)

                # Track user session
                session_id = id(session)
                for sid, s in self.session_manager.active_sessions.items():
                    if s == session:
                        self.user_sessions[user_id] = sid
                        break

                return session

        def _hash_to_host(self, user_id: str) -> str:
            """Hash user ID to consistent host selection."""
            hash_value = int(hashlib.md5(user_id.encode()).hexdigest()[:8], 16)
            host_names = list(self.session_manager.hosts.keys())
            return host_names[hash_value % len(host_names)]

        async def release_user_session(self, user_id: str):
            """Release session for user."""
            async with self._lock:
                session_id = self.user_sessions.pop(user_id, None)
                if session_id:
                    session = self.session_manager.active_sessions.get(session_id)
                    if session:
                        await self.session_manager.return_session(session)

    # Example usage of enterprise session management
    async def enterprise_session_example():
        """Demonstrate enterprise multi-session management."""

        # Configure hosts
        session_manager = EnterpriseSessionManager()

        # Add production hosts
        await session_manager.add_host(HostConfig(
            host="prod-mainframe1.corp.com",
            port=23,
            host_type=HostType.PRODUCTION,
            terminal_type="IBM-3278-4",
            max_sessions=15
        ))

        await session_manager.add_host(HostConfig(
            host="prod-mainframe2.corp.com",
            port=23,
            host_type=HostType.PRODUCTION,
            terminal_type="IBM-3278-4",
            max_sessions=15
        ))

        # Add development host
        await session_manager.add_host(HostConfig(
            host="dev-mainframe.corp.com",
            port=23,
            host_type=HostType.DEVELOPMENT,
            terminal_type="IBM-3278-2",
            max_sessions=5
        ))

        # Start health monitoring
        await session_manager.start_health_monitoring()

        # Create session affinity manager
        affinity_manager = SessionAffinityManager(session_manager)

        try:
            # Get different types of sessions
            read_session = await session_manager.get_session(role=SessionRole.READ_ONLY)
            write_session = await session_manager.get_session(role=SessionRole.TRANSACTIONAL)
            admin_session = await session_manager.get_session(role=SessionRole.ADMIN)

            # Get session with user affinity
            user_session = await affinity_manager.get_session_for_user("user123")

            # Use sessions...
            print("All sessions obtained successfully")

        finally:
            if session_manager._health_monitor_task:
                session_manager._health_monitor_task.cancel()

Printer Emulation Scenarios
----------------------------

Enterprise Printer Management
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Multi-printer management for enterprise environments:

.. code-block:: python

    import asyncio
    import json
    from typing import Dict, List, Optional
    from dataclasses import dataclass
    from enum import Enum
    from pure3270 import AsyncPrinterSession, AsyncSession

    class PrinterType(Enum):
        """Types of printers in enterprise environment."""
        LASER = "laser"
        MATRIX = "dot_matrix"
        THERMAL = "thermal"
        BARCODE = "barcode"
        ARCHIVE = "archive"

    class PrintJobStatus(Enum):
        """Status of print jobs."""
        PENDING = "pending"
        PRINTING = "printing"
        COMPLETED = "completed"
        FAILED = "failed"
        CANCELLED = "cancelled"

    @dataclass
    class PrintJob:
        """Enterprise print job definition."""
        job_id: str
        printer_host: str
        document_name: str
        content: str
        priority: int
        copies: int
        printer_type: PrinterType
        submitted_at: float
        status: PrintJobStatus = PrintJobStatus.PENDING
        error_message: Optional[str] = None

    @dataclass
    class PrinterStatus:
        """Status information for printer."""
        host: str
        status: str
        job_count: int
        paper_level: int
        toner_level: int
        last_activity: float
        error_count: int

    class EnterprisePrinterManager:
        """Enterprise printer management system."""

        def __init__(self):
            self.printers: Dict[str, PrinterStatus] = {}
            self.print_jobs: Dict[str, PrintJob] = {}
            self.job_queue: List[str] = []
            self.printer_sessions: Dict[str, AsyncPrinterSession] = {}
            self._lock = asyncio.Lock()
            self._monitoring_task = None

        async def add_printer(self, printer_host: str, printer_type: PrinterType = PrinterType.LASER):
            """Add printer to management system."""
            self.printers[printer_host] = PrinterStatus(
                host=printer_host,
                status="unknown",
                job_count=0,
                paper_level=100,
                toner_level=100,
                last_activity=asyncio.get_event_loop().time(),
                error_count=0
            )
            print(f"Added printer: {printer_host} ({printer_type.value})")

        async def submit_print_job(self, job: PrintJob) -> str:
            """Submit print job to enterprise printer system."""
            async with self._lock:
                self.print_jobs[job.job_id] = job
                self.job_queue.append(job.job_id)

                print(f"Print job {job.job_id} submitted to {job.printer_host}")
                return job.job_id

        async def process_print_queue(self):
            """Process pending print jobs."""
        async with self._lock:
            while self.job_queue:
                job_id = self.job_queue.pop(0)
                job = self.print_jobs[job_id]

                if job.status == PrintJobStatus.CANCELLED:
                    continue

                try:
                    # Update job status
                    job.status = PrintJobStatus.PRINTING

                    # Process job
                    success = await self._process_job(job)

                    if success:
                        job.status = PrintJobStatus.COMPLETED
                        print(f"Job {job.job_id} completed successfully")
                    else:
                        job.status = PrintJobStatus.FAILED
                        print(f"Job {job.job_id} failed")

                except Exception as e:
                    job.status = PrintJobStatus.FAILED
                    job.error_message = str(e)
                    print(f"Job {job.job_id} failed with error: {e}")

        async def _process_job(self, job: PrintJob) -> bool:
            """Process individual print job."""
            try:
                # Get or create printer session
                printer_session = await self._get_printer_session(job.printer_host)

                # Send print job
                if job.printer_type == PrinterType.LASER:
                    return await self._print_laser_job(printer_session, job)
                elif job.printer_type == PrinterType.MATRIX:
                    return await self._print_matrix_job(printer_session, job)
                else:
                    # Generic print job
                    return await self._print_generic_job(printer_session, job)

            except Exception as e:
                self.printers[job.printer_host].error_count += 1
                raise e

        async def _get_printer_session(self, printer_host: str) -> AsyncPrinterSession:
            """Get or create printer session."""
            if printer_host in self.printer_sessions:
                return self.printer_sessions[printer_host]

            # Create new printer session
            session = AsyncPrinterSession(host=printer_host)
            await session.connect()

            self.printer_sessions[printer_host] = session
            return session

        async def _print_laser_job(self, session: AsyncPrinterSession, job: PrintJob) -> bool:
            """Print job on laser printer."""
            try:
                # Send multiple copies if required
                for copy in range(job.copies):
                    # Convert content to printer format
                    print_data = self._format_for_laser_printer(job.content)

                    # Send to printer
                    await session.send_print_data(print_data)

                    # Small delay between copies
                    if copy < job.copies - 1:
                        await asyncio.sleep(0.5)

                return True

            except Exception as e:
                print(f"Laser print failed: {e}")
                return False

        async def _print_matrix_job(self, session: AsyncPrinterSession, job: PrintJob) -> bool:
            """Print job on dot matrix printer."""
            try:
                # Matrix printers need special formatting
                print_data = self._format_for_matrix_printer(job.content)
                await session.send_print_data(print_data)
                return True

            except Exception as e:
                print(f"Matrix print failed: {e}")
                return False

        async def _print_generic_job(self, session: AsyncPrinterSession, job: PrintJob) -> bool:
            """Generic print job for unknown printer types."""
            try:
                print_data = job.content.encode('ascii')
                await session.send_print_data(print_data)
                return True

            except Exception as e:
                print(f"Generic print failed: {e}")
                return False

        def _format_for_laser_printer(self, content: str) -> bytes:
            """Format content for laser printer (PostScript/PCL)."""
            # Simplified PCL formatting
            pcl_data = b"\\x1B\\x45"  # Reset
            pcl_data += b"\\x1B(0N"  # Select symbol set
            pcl_data += content.encode('ascii', errors='ignore')
            pcl_data += b"\\x1B\\x0C"  # Form feed
            return pcl_data

        def _format_for_matrix_printer(self, content: str) -> bytes:
            """Format content for dot matrix printer."""
            # Dot matrix format
            ascii_content = content.encode('ascii', errors='ignore')
            # Add line feeds for impact printing
            formatted = ascii_content.replace(b'\\n', b'\\r\\n')
            return formatted

        async def cancel_print_job(self, job_id: str) -> bool:
            """Cancel pending print job."""
            async with self._lock:
                if job_id in self.print_jobs:
                    job = self.print_jobs[job_id]
                    if job.status == PrintJobStatus.PENDING:
                        job.status = PrintJobStatus.CANCELLED
                        return True
                return False

        async def get_printer_status(self, printer_host: str) -> Optional[PrinterStatus]:
            """Get current status of printer."""
            return self.printers.get(printer_host)

        async def get_print_job_status(self, job_id: str) -> Optional[PrintJob]:
            """Get status of print job."""
            return self.print_jobs.get(job_id)

        async def start_monitoring(self):
            """Start background printer monitoring."""
            async def monitor():
                while True:
                    try:
                        await self._monitor_all_printers()
                        await asyncio.sleep(30)  # Check every 30 seconds
                    except Exception as e:
                        print(f"Printer monitoring error: {e}")
                        await asyncio.sleep(5)

            self._monitoring_task = asyncio.create_task(monitor())

        async def _monitor_all_printers(self):
            """Monitor status of all printers."""
            for printer_host in list(self.printer_sessions.keys()):
                try:
                    await self._check_printer_status(printer_host)
                except Exception as e:
                    print(f"Error checking printer {printer_host}: {e}")

        async def _check_printer_status(self, printer_host: str):
            """Check status of specific printer."""
            session = self.printer_sessions[printer_host]

            try:
                # Get printer status
                status = await session.get_printer_status()

                # Update status
                if printer_host in self.printers:
                    self.printers[printer_host].status = f"0x{status:02x}"
                    self.printers[printer_host].last_activity = asyncio.get_event_loop().time()

                # Check for jobs
                output = await session.get_printer_output()
                if output:
                    self.printers[printer_host].job_count = len(output)

            except Exception as e:
                print(f"Printer {printer_host} check failed: {e}")
                self.printers[printer_host].error_count += 1

        async def cleanup(self):
            """Cleanup all printer sessions."""
            for session in self.printer_sessions.values():
                try:
                    await session.close()
                except:
                    pass

            if self._monitoring_task:
                self._monitoring_task.cancel()

    # Example usage of enterprise printer management
    async def printer_management_example():
        """Demonstrate enterprise printer management."""

        # Create printer manager
        printer_manager = EnterprisePrinterManager()

        # Add printers
        await printer_manager.add_printer("laser-printer1.corp.com", PrinterType.LASER)
        await printer_manager.add_printer("matrix-printer1.corp.com", PrinterType.MATRIX)
        await printer_manager.add_printer("archive-printer1.corp.com", PrinterType.ARCHIVE)

        # Start monitoring
        await printer_manager.start_monitoring()

        try:
            # Submit various print jobs
            jobs = [
                PrintJob(
                    job_id="JOB001",
                    printer_host="laser-printer1.corp.com",
                    document_name="Monthly Report",
                    content="Monthly business report content...",
                    priority=1,
                    copies=3,
                    printer_type=PrinterType.LASER,
                    submitted_at=asyncio.get_event_loop().time()
                ),
                PrintJob(
                    job_id="JOB002",
                    printer_host="matrix-printer1.corp.com",
                    document_name="Shipping Labels",
                    content="Shipping label content...",
                    priority=2,
                    copies=1,
                    printer_type=PrinterType.MATRIX,
                    submitted_at=asyncio.get_event_loop().time()
                )
            ]

            # Submit jobs
            for job in jobs:
                await printer_manager.submit_print_job(job)

            # Process queue
            await printer_manager.process_print_queue()

            # Check status
            for job in jobs:
                status = await printer_manager.get_print_job_status(job.job_id)
                print(f"Job {job.job_id}: {status.status.value if status else 'Unknown'}")

        finally:
            await printer_manager.cleanup()

MCP Server Integration Examples
-------------------------------

Pure3270 MCP Server for AI Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Integration with Model Context Protocol servers for AI-driven terminal operations:

.. code-block:: python

    import asyncio
    import json
    from typing import Dict, List, Optional, Any
    from dataclasses import dataclass
    from pure3270 import AsyncSession
    from mcp_server import MCPServer, tool, resource

    @dataclass
    class MCPTerminalSession:
        """MCP terminal session with AI integration."""
        session_id: str
        host: str
        terminal_type: str
        ai_context: Dict[str, Any]
        last_screen_state: str

    class Pure3270MCPServer(MCPServer):
        """MCP server providing TN3270 terminal access to AI systems."""

        def __init__(self):
            super().__init__("pure3270-terminal")
            self.sessions: Dict[str, MCPTerminalSession] = {}
            self.global_settings = {
                "default_terminal": "IBM-3278-2",
                "default_timeout": 30.0,
                "enable_ai_assistance": True
            }

        @tool("create_terminal_session")
        async def create_terminal_session(
            self,
            host: str,
            port: int = 23,
            terminal_type: str = None,
            ai_context: str = None
        ) -> str:
            """
            Create a new TN3270 terminal session.

            Args:
                host: Mainframe hostname
                port: TN3270 port (default 23)
                terminal_type: Terminal model (default: IBM-3278-2)
                ai_context: JSON context for AI assistance

            Returns:
                Session ID for subsequent operations
            """
            terminal_type = terminal_type or self.global_settings["default_terminal"]

            # Create session
            session = AsyncSession(terminal_type=terminal_type)
            await session.connect(host, port)

            # Generate session ID
            import uuid
            session_id = str(uuid.uuid4())[:8]

            # Create MCP session
            mcp_session = MCPTerminalSession(
                session_id=session_id,
                host=host,
                terminal_type=terminal_type,
                ai_context=json.loads(ai_context) if ai_context else {},
                last_screen_state=""
            )

            self.sessions[session_id] = mcp_session

            print(f"Created terminal session {session_id} for {host}")
            return session_id

        @tool("execute_terminal_command")
        async def execute_terminal_command(
            self,
            session_id: str,
            command: str,
            parameters: str = None
        ) -> str:
            """
            Execute a terminal command through the session.

            Args:
                session_id: Session ID from create_terminal_session
                command: Command to execute (key, string, read, etc.)
                parameters: JSON parameters for the command

            Returns:
                Command result and screen state
            """
            if session_id not in self.sessions:
                raise ValueError(f"Session {session_id} not found")

            session_info = self.sessions[session_id]
            session = await self._get_session_object(session_info)

            try:
                params = json.loads(parameters) if parameters else {}

                if command == "key":
                    key_name = params.get("key", "")
                    await session.key(key_name)
                    result = {"status": "success", "action": "key_pressed", "key": key_name}

                elif command == "string":
                    text = params.get("text", "")
                    await session.string(text)
                    result = {"status": "success", "action": "string_entered", "text": text}

                elif command == "read":
                    timeout = params.get("timeout", self.global_settings["default_timeout"])
                    screen_data = await asyncio.wait_for(session.read(), timeout=timeout)
                    screen_text = session.ascii(screen_data)
                    result = {
                        "status": "success",
                        "action": "screen_read",
                        "screen_data": screen_text,
                        "bytes_received": len(screen_data)
                    }

                elif command == "clear":
                    await session.key("CLEAR")
                    result = {"status": "success", "action": "screen_cleared"}

                else:
                    raise ValueError(f"Unknown command: {command}")

                # Update session state
                if command == "read":
                    session_info.last_screen_state = result.get("screen_data", "")

                return json.dumps(result)

            except Exception as e:
                error_result = {
                    "status": "error",
                    "action": command,
                    "error": str(e)
                }
                return json.dumps(error_result)

        @tool("ai_assisted_navigation")
        async def ai_assisted_navigation(
            self,
            session_id: str,
            goal_description: str,
            current_screen: str = None
        ) -> str:
            """
            AI-assisted navigation to accomplish a goal.

            Args:
                session_id: Session ID
                goal_description: Natural language description of what to accomplish
                current_screen: Current screen state (optional, will be read if not provided)

            Returns:
                Navigation steps and final screen state
            """
            if session_id not in self.sessions:
                raise ValueError(f"Session {session_id} not found")

            session_info = self.sessions[session_id]
            session = await self._get_session_object(session_info)

            # Get current screen if not provided
            if not current_screen:
                screen_data = await session.read()
                current_screen = session.ascii(screen_data)

            # AI planning (simplified - in real implementation would use LLM)
            navigation_plan = self._plan_navigation(current_screen, goal_description, session_info.ai_context)

            # Execute navigation plan
            executed_steps = []
            for step in navigation_plan:
                try:
                    if step["type"] == "key":
                        await session.key(step["key"])
                    elif step["type"] == "string":
                        await session.string(step["text"])

                    executed_steps.append(step)
                    await asyncio.sleep(0.5)  # Brief pause between steps

                except Exception as e:
                    executed_steps.append({
                        "type": "error",
                        "error": str(e),
                        "step": step
                    })
                    break

            # Get final screen state
            final_screen_data = await session.read()
            final_screen = session.ascii(final_screen_data)

            result = {
                "status": "success",
                "goal": goal_description,
                "steps_planned": len(navigation_plan),
                "steps_executed": len(executed_steps),
                "executed_steps": executed_steps,
                "final_screen": final_screen,
                "session_id": session_id
            }

            return json.dumps(result)

        @tool("batch_terminal_operations")
        async def batch_terminal_operations(
            self,
            session_id: str,
            operations: str
        ) -> str:
            """
            Execute multiple terminal operations in batch.

            Args:
                session_id: Session ID
                operations: JSON array of operations to execute

            Returns:
                Results of all operations
            """
            if session_id not in self.sessions:
                raise ValueError(f"Session {session_id} not found")

            session_info = self.sessions[session_id]
            session = await self._get_session_object(session_info)

            ops = json.loads(operations)
            results = []

            for op in ops:
                try:
                    command = op.get("command", "")
                    params = op.get("parameters", {})

                    if command == "key":
                        await session.key(params.get("key", ""))
                        results.append({"operation": op, "status": "success"})

                    elif command == "string":
                        await session.string(params.get("text", ""))
                        results.append({"operation": op, "status": "success"})

                    elif command == "read":
                        timeout = params.get("timeout", self.global_settings["default_timeout"])
                        screen_data = await asyncio.wait_for(session.read(), timeout=timeout)
                        screen_text = session.ascii(screen_data)
                        results.append({
                            "operation": op,
                            "status": "success",
                            "screen_data": screen_text
                        })

                    else:
                        results.append({
                            "operation": op,
                            "status": "error",
                            "error": f"Unknown command: {command}"
                        })

                except Exception as e:
                    results.append({
                        "operation": op,
                        "status": "error",
                        "error": str(e)
                    })

            return json.dumps({
                "status": "success",
                "total_operations": len(ops),
                "successful_operations": len([r for r in results if r["status"] == "success"]),
                "results": results
            })

        @tool("get_session_info")
        async def get_session_info(self, session_id: str) -> str:
            """Get information about a terminal session."""
            if session_id not in self.sessions:
                raise ValueError(f"Session {session_id} not found")

            session_info = self.sessions[session_id]

            return json.dumps({
                "session_id": session_info.session_id,
                "host": session_info.host,
                "terminal_type": session_info.terminal_type,
                "ai_context": session_info.ai_context,
                "last_screen_state": session_info.last_screen_state[:100] + "..." if len(session_info.last_screen_state) > 100 else session_info.last_screen_state
            })

        @tool("close_terminal_session")
        async def close_terminal_session(self, session_id: str) -> str:
            """Close a terminal session."""
            if session_id not in self.sessions:
                raise ValueError(f"Session {session_id} not found")

            session_info = self.sessions[session_id]
            session = await self._get_session_object(session_info)

            try:
                await session.close()
                del self.sessions[session_id]
                return json.dumps({"status": "success", "message": f"Session {session_id} closed"})
            except Exception as e:
                return json.dumps({"status": "error", "error": str(e)})

        @resource("terminal://sessions")
        async def list_sessions(self) -> str:
            """List all active terminal sessions."""
            sessions_list = []

            for session_id, session_info in self.sessions.items():
                sessions_list.append({
                    "session_id": session_id,
                    "host": session_info.host,
                    "terminal_type": session_info.terminal_type,
                    "ai_context_keys": list(session_info.ai_context.keys())
                })

            return json.dumps({
                "status": "success",
                "session_count": len(sessions_list),
                "sessions": sessions_list
            })

        async def _get_session_object(self, session_info: MCPTerminalSession) -> AsyncSession:
            """Get AsyncSession object from session info."""
            # This would cache session objects in a real implementation
            session = AsyncSession(terminal_type=session_info.terminal_type)
            await session.connect(session_info.host)
            return session

        def _plan_navigation(self, current_screen: str, goal: str, ai_context: Dict) -> List[Dict]:
            """Plan navigation steps based on goal and current screen."""
            # Simplified planning logic
            # In real implementation, would use AI/LLM for sophisticated planning

            steps = []

            if "login" in goal.lower():
                steps.append({"type": "key", "key": "CLEAR"})
                steps.append({"type": "string", "text": "LOGON"})
                steps.append({"type": "key", "key": "ENTER"})

            elif "menu" in goal.lower():
                steps.append({"type": "key", "key": "ENTER"})

            elif "exit" in goal.lower():
                steps.append({"type": "key", "key": "F3"})

            else:
                # Default to reading screen
                steps.append({"type": "key", "key": "ENTER"})

            return steps

    # Example MCP client usage
    class MCPClient:
        """Client for interacting with Pure3270 MCP server."""

        def __init__(self, server_url: str = "http://localhost:8000"):
            self.server_url = server_url

        async def create_session(self, host: str, terminal_type: str = "IBM-3278-2") -> str:
            """Create new terminal session."""
            # Implementation would make HTTP request to MCP server
            # For demo purposes, return mock session ID
            return "session123"

        async def ai_navigate_to_goal(self, session_id: str, goal: str) -> dict:
            """Use AI to navigate to accomplish goal."""
            # Implementation would call MCP server AI navigation tool
            return {
                "status": "success",
                "goal": goal,
                "steps_executed": 3,
                "final_screen": "Application main menu"
            }

    # Example usage of MCP integration
    async def mcp_integration_example():
        """Demonstrate MCP integration with AI assistance."""

        # Start MCP server (would be separate process in production)
        # server = Pure3270MCPServer()
        # await server.start()

        # Create MCP client
        client = MCPClient()

        # Create terminal session
        session_id = await client.create_session("mainframe.example.com", "IBM-3278-4")

        # Use AI to navigate to goal
        result = await client.ai_navigate_to_goal(session_id, "Navigate to transaction entry screen")

        print(f"AI navigation result: {result}")

Network Resilience Patterns
----------------------------

Enterprise Network Resilience
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Advanced network resilience patterns for mission-critical environments:

.. code-block:: python

    import asyncio
    import time
    from typing import Dict, List, Optional, Callable
    from dataclasses import dataclass
    from enum import Enum
    from pure3270 import AsyncSession, setup_logging
    from pure3270.exceptions import ConnectionError

    class NetworkCondition(Enum):
        """Network condition states."""
        HEALTHY = "healthy"
        DEGRADED = "degraded"
        FAILED = "failed"
        RECOVERING = "recovering"

    class CircuitBreakerState(Enum):
        """Circuit breaker states."""
        CLOSED = "closed"      # Normal operation
        OPEN = "open"          # Blocking requests
        HALF_OPEN = "half_open" # Testing recovery

    @dataclass
    class NetworkMetrics:
        """Network performance and reliability metrics."""
        latency_ms: float
        packet_loss_percent: float
        bandwidth_mbps: float
        error_rate: float
        availability_percent: float
        last_check: float

    @dataclass
    class FailoverRule:
        """Rule for automatic failover decisions."""
        primary_host: str
        backup_hosts: List[str]
        health_threshold: float
        latency_threshold_ms: float
        error_rate_threshold: float

    class AdvancedCircuitBreaker:
        """Advanced circuit breaker with multiple failure detection methods."""

        def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0,
                     half_open_max_calls: int = 3):
            self.failure_threshold = failure_threshold
            self.recovery_timeout = recovery_timeout
            self.half_open_max_calls = half_open_max_calls

            self.state = CircuitBreakerState.CLOSED
            self.failure_count = 0
            self.last_failure_time = 0
            self.half_open_calls = 0
            self.success_count = 0

        def can_execute(self) -> bool:
            """Check if operation can be executed."""
            current_time = time.time()

            if self.state == CircuitBreakerState.CLOSED:
                return True
            elif self.state == CircuitBreakerState.OPEN:
                if current_time - self.last_failure_time >= self.recovery_timeout:
                    self.state = CircuitBreakerState.HALF_OPEN
                    self.half_open_calls = 0
                    return True
                return False
            else:  # HALF_OPEN
                if self.half_open_calls < self.half_open_max_calls:
                    self.half_open_calls += 1
                    return True
                return False

        def record_success(self):
            """Record successful operation."""
            self.failure_count = 0
            self.success_count += 1

            if self.state == CircuitBreakerState.HALF_OPEN:
                if self.success_count >= self.half_open_max_calls:
                    self.state = CircuitBreakerState.CLOSED
                    print("Circuit breaker recovered - CLOSED state")

        def record_failure(self):
            """Record failed operation."""
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                if self.state != CircuitBreakerState.OPEN:
                    self.state = CircuitBreakerState.OPEN
                    print(f"Circuit breaker OPEN after {self.failure_count} failures")
            elif self.state == CircuitBreakerState.HALF_OPEN:
                self.state = CircuitBreakerState.OPEN
                print("Circuit breaker OPEN - half-open test failed")

    class NetworkResilienceManager:
        """Enterprise network resilience management."""

        def __init__(self):
            self.hosts: Dict[str, NetworkMetrics] = {}
            self.circuit_breakers: Dict[str, AdvancedCircuitBreaker] = {}
            self.failover_rules: Dict[str, FailoverRule] = {}
            self.health_monitor_tasks: Dict[str, asyncio.Task] = {}
            self.network_conditions: Dict[str, NetworkCondition] = {}
            self._lock = asyncio.Lock()

        async def add_host_with_failover(self, rule: FailoverRule):
            """Add host with automatic failover configuration."""
            self.failover_rules[rule.primary_host] = rule
            self.hosts[rule.primary_host] = NetworkMetrics(0, 0, 0, 0, 0, time.time())

            for backup_host in rule.backup_hosts:
                self.hosts[backup_host] = NetworkMetrics(0, 0, 0, 0, 0, time.time())

            # Start health monitoring for all hosts
            await self._start_health_monitoring(rule)

        async def get_resilient_session(self, host: str = None, max_retries: int = 5) -> AsyncSession:
            """Get session with comprehensive resilience features."""

            if host is None:
                host = await self._select_optimal_host()

            if host not in self.hosts:
                raise ValueError(f"Host {host} not registered")

            # Check circuit breaker
            if host not in self.circuit_breakers:
                self.circuit_breakers[host] = AdvancedCircuitBreaker()

            breaker = self.circuit_breakers[host]

            if not breaker.can_execute():
                # Try failover
                failover_host = await self._find_working_backup(host)
                if failover_host:
                    print(f"Circuit breaker open for {host}, using backup {failover_host}")
                    host = failover_host
                else:
                    raise ConnectionError(f"All hosts failed for {host}")

            # Retry with exponential backoff
            last_error = None
            delay = 1.0

            for attempt in range(max_retries):
                try:
                    session = await self._create_resilient_session(host)

                    # Test session with health check
                    await asyncio.wait_for(session.read(), timeout=5.0)

                    # Update success metrics
                    await self._update_success_metrics(host)
                    breaker.record_success()

                    return session

                except Exception as e:
                    last_error = e

                    # Record failure
                    breaker.record_failure()
                    await self._update_failure_metrics(host)

                    print(f"Connection attempt {attempt + 1} to {host} failed: {e}")

                    # Try failover if this is a critical failure
                    if await self._is_critical_failure(e):
                        failover_host = await self._find_working_backup(host)
                        if failover_host:
                            print(f"Critical failure, switching to backup {failover_host}")
                            host = failover_host

                    # Exponential backoff
                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay)
                        delay *= 1.5

            raise ConnectionError(f"Failed to connect after {max_retries} attempts: {last_error}")

        async def _create_resilient_session(self, host: str) -> AsyncSession:
            """Create session with resilience configurations."""
            session = AsyncSession()

            # Configure session for resilience
            session._resilience_mode = True
            session._connection_timeout = 30.0
            session._read_timeout = 30.0
            session._write_timeout = 30.0

            await session.connect(host)
            return session

        async def _select_optimal_host(self) -> str:
            """Select optimal host based on performance metrics."""
            suitable_hosts = []

            for host, metrics in self.hosts.items():
                if self.network_conditions.get(host, NetworkCondition.HEALTHY) == NetworkCondition.HEALTHY:
                    score = self._calculate_host_score(host, metrics)
                    suitable_hosts.append((host, score))

            if not suitable_hosts:
                # All hosts unhealthy, return best available
                return min(self.hosts.keys(), key=lambda h: self.hosts[h].error_rate)

            return min(suitable_hosts, key=lambda x: x[1])[0]

        def _calculate_host_score(self, host: str, metrics: NetworkMetrics) -> float:
            """Calculate host fitness score (lower is better)."""
            score = 0.0

            # Latency penalty
            score += metrics.latency_ms / 100.0

            # Error rate penalty
            score += metrics.error_rate * 10.0

            # Packet loss penalty
            score += metrics.packet_loss_percent

            # Availability bonus (lower availability increases score)
            score += (100 - metrics.availability_percent) / 10.0

            return score

        async def _find_working_backup(self, primary_host: str) -> Optional[str]:
            """Find working backup host for primary."""
            if primary_host not in self.failover_rules:
                return None

            rule = self.failover_rules[primary_host]

            # Try backup hosts in order
            for backup_host in rule.backup_hosts:
                condition = self.network_conditions.get(backup_host, NetworkCondition.HEALTHY)

                if condition == NetworkCondition.HEALTHY:
                    metrics = self.hosts.get(backup_host, NetworkMetrics(0, 0, 0, 0, 0, time.time()))

                    # Check if backup meets thresholds
                    if (metrics.latency_ms < rule.latency_threshold_ms and
                        metrics.error_rate < rule.error_rate_threshold):
                        return backup_host

            return None

        async def _is_critical_failure(self, error: Exception) -> bool:
            """Determine if failure is critical enough to trigger immediate failover."""
            critical_errors = [
                ConnectionRefusedError,
                TimeoutError,
                OSError,  # Network unreachable
            ]

            return isinstance(error, tuple(critical_errors))

        async def _start_health_monitoring(self, rule: FailoverRule):
            """Start health monitoring for host and its backups."""
            all_hosts = [rule.primary_host] + rule.backup_hosts

            for host in all_hosts:
                task = asyncio.create_task(self._monitor_host(host, rule))
                self.health_monitor_tasks[host] = task

        async def _monitor_host(self, host: str, rule: FailoverRule):
            """Monitor individual host health."""
            while True:
                try:
                    await self._check_host_health(host, rule)
                    await asyncio.sleep(30)  # Check every 30 seconds
                except Exception as e:
                    print(f"Health monitor error for {host}: {e}")
                    await asyncio.sleep(5)

        async def _check_host_health(self, host: str, rule: FailoverRule):
            """Perform comprehensive health check on host."""
            start_time = time.time()

            try:
                # Test connection
                session = AsyncSession()
                await asyncio.wait_for(session.connect(host), timeout=10.0)

                # Test read operation
                await asyncio.wait_for(session.read(), timeout=5.0)

                await session.close()

                # Calculate metrics
                latency = (time.time() - start_time) * 1000  # Convert to ms

                # Update host metrics
                if host in self.hosts:
                    self.hosts[host].latency_ms = latency
                    self.hosts[host].last_check = time.time()

                    # Determine network condition
                    if latency < rule.latency_threshold_ms:
                        self.network_conditions[host] = NetworkCondition.HEALTHY
                    elif latency < rule.latency_threshold_ms * 2:
                        self.network_conditions[host] = NetworkCondition.DEGRADED
                    else:
                        self.network_conditions[host] = NetworkCondition.FAILED

            except Exception as e:
                print(f"Health check failed for {host}: {e}")

                if host in self.hosts:
                    self.hosts[host].error_rate = min(100.0, self.hosts[host].error_rate + 5.0)
                    self.network_conditions[host] = NetworkCondition.FAILED

        async def _update_success_metrics(self, host: str):
            """Update metrics after successful operation."""
            if host in self.hosts:
                # Gradually decrease error rate on success
                self.hosts[host].error_rate = max(0.0, self.hosts[host].error_rate - 1.0)

                # Update availability
                uptime = time.time()
                self.hosts[host].availability_percent = min(100.0,
                    self.hosts[host].availability_percent + 0.1)

        async def _update_failure_metrics(self, host: str):
            """Update metrics after failed operation."""
            if host in self.hosts:
                # Increase error rate
                self.hosts[host].error_rate = min(100.0,
                    self.hosts[host].error_rate + 5.0)

                # Decrease availability
                self.hosts[host].availability_percent = max(0.0,
                    self.hosts[host].availability_percent - 1.0)

        async def get_network_status(self) -> Dict:
            """Get comprehensive network status report."""
            status = {
                "overall_condition": "unknown",
                "hosts": {},
                "failover_rules": {},
                "timestamp": time.time()
            }

            # Determine overall condition
            healthy_hosts = len([h for h in self.network_conditions.values()
                               if h == NetworkCondition.HEALTHY])
            total_hosts = len(self.network_conditions)

            if total_hosts == 0:
                status["overall_condition"] = "no_hosts"
            elif healthy_hosts == total_hosts:
                status["overall_condition"] = "all_healthy"
            elif healthy_hosts > total_hosts / 2:
                status["overall_condition"] = "degraded"
            else:
                status["overall_condition"] = "critical"

            # Host details
            for host in self.hosts:
                status["hosts"][host] = {
                    "condition": self.network_conditions.get(host, NetworkCondition.FAILED).value,
                    "metrics": {
                        "latency_ms": self.hosts[host].latency_ms,
                        "error_rate": self.hosts[host].error_rate,
                        "availability_percent": self.hosts[host].availability_percent,
                        "last_check": self.hosts[host].last_check
                    },
                    "circuit_breaker": {
                        "state": self.circuit_breakers.get(host, AdvancedCircuitBreaker()).state.value,
                        "failure_count": self.circuit_breakers.get(host, AdvancedCircuitBreaker()).failure_count
                    }
                }

            # Failover rules
            for primary, rule in self.failover_rules.items():
                status["failover_rules"][primary] = {
                    "backup_hosts": rule.backup_hosts,
                    "health_threshold": rule.health_threshold,
                    "latency_threshold_ms": rule.latency_threshold_ms,
                    "error_rate_threshold": rule.error_rate_threshold
                }

            return status

    # Example usage of network resilience
    async def network_resilience_example():
        """Demonstrate enterprise network resilience patterns."""

        # Create resilience manager
        manager = NetworkResilienceManager()

        # Configure failover rules
        await manager.add_host_with_failover(FailoverRule(
            primary_host="mainframe1.corp.com",
            backup_hosts=["mainframe2.corp.com", "mainframe3.corp.com"],
            health_threshold=0.95,
            latency_threshold_ms=500.0,
            error_rate_threshold=5.0
        ))

        try:
            # Get resilient session (automatically handles failover)
            session = await manager.get_resilient_session()

            # Use session normally
            await session.string("TEST")
            await session.key("ENTER")
            response = session.ascii(session.read())
            print(f"Response: {response}")

            # Get network status
            status = await manager.get_network_status()
            print(f"Network status: {status['overall_condition']}")

        finally:
            # Cleanup
            for task in manager.health_monitor_tasks.values():
                task.cancel()

Production Deployment Examples
-------------------------------

Enterprise Production Deployment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Production deployment configurations and monitoring:

.. code-block:: python

    import asyncio
    import yaml
    import logging
    from typing import Dict, List, Optional
    from dataclasses import dataclass
    from pure3270 import AsyncSession

    @dataclass
    class ProductionConfig:
        """Production deployment configuration."""
        hosts: List[str]
        monitoring_enabled: bool
        performance_targets: Dict[str, float]
        security_settings: Dict[str, bool]
        scaling_config: Dict[str, int]
        alerting_rules: Dict[str, str]

    class ProductionDeploymentManager:
        """Production deployment manager for enterprise TN3270 operations."""

        def __init__(self, config_file: str = "production_config.yaml"):
            self.config = self._load_config(config_file)
            self.session_pools: Dict[str, List[AsyncSession]] = {}
            self.metrics_collector = None
            self.alert_manager = None
            self.load_balancer = None
            self._setup_monitoring()

        def _load_config(self, config_file: str) -> ProductionConfig:
            """Load production configuration from file."""
            try:
                with open(config_file, 'r') as f:
                    config_data = yaml.safe_load(f)

                return ProductionConfig(**config_data)

            except FileNotFoundError:
                # Default production configuration
                return ProductionConfig(
                    hosts=["mainframe1.corp.com", "mainframe2.corp.com"],
                    monitoring_enabled=True,
                    performance_targets={
                        "max_response_time_ms": 1000,
                        "min_availability_percent": 99.5,
                        "max_error_rate_percent": 1.0
                    },
                    security_settings={
                        "require_ssl": True,
                        "certificate_validation": True,
                        "session_timeout_minutes": 30
                    },
                    scaling_config={
                        "min_sessions_per_host": 5,
                        "max_sessions_per_host": 50,
                        "autoscale_threshold": 80
                    },
                    alerting_rules={
                        "response_time_threshold": "2s",
                        "error_rate_threshold": "5%",
                        "availability_threshold": "99%"
                    }
                )

        def _setup_monitoring(self):
            """Setup production monitoring and alerting."""
            if not self.config.monitoring_enabled:
                return

            # Setup logging
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler('production_tn3270.log'),
                    logging.StreamHandler()
                ]
            )

            # Setup metrics collection
            self.metrics_collector = ProductionMetricsCollector(self.config)

            # Setup alerting
            self.alert_manager = ProductionAlertManager(self.config)

        async def initialize_production_environment(self):
            """Initialize production environment with all components."""
            print("Initializing production TN3270 environment...")

            # Initialize session pools
            await self._initialize_session_pools()

            # Start monitoring
            if self.config.monitoring_enabled:
                await self.metrics_collector.start()
                await self.alert_manager.start()

            # Setup load balancing
            self.load_balancer = ProductionLoadBalancer(self.config)

            print("Production environment initialized successfully")

        async def _initialize_session_pools(self):
            """Initialize session pools for all production hosts."""
            for host in self.config.hosts:
                pool = []

                for i in range(self.config.scaling_config["min_sessions_per_host"]):
                    try:
                        session = await self._create_production_session(host)
                        pool.append(session)
                        print(f"Created production session {i+1} for {host}")
                    except Exception as e:
                        print(f"Failed to create session {i+1} for {host}: {e}")

                self.session_pools[host] = pool
                print(f"Initialized pool with {len(pool)} sessions for {host}")

        async def _create_production_session(self, host: str) -> AsyncSession:
            """Create session with production optimizations."""
            session = AsyncSession(terminal_type="IBM-3278-4")

            # Configure for production performance
            session._connection_timeout = 15.0
            session._read_timeout = 30.0
            session._write_timeout = 30.0
            session._enable_keepalive = True
            session._buffer_size = 8192

            # Security settings
            if self.config.security_settings.get("require_ssl"):
                # Configure SSL context
                ssl_context = {
                    "verify_mode": "CERT_REQUIRED" if self.config.security_settings.get("certificate_validation") else "CERT_NONE"
                }
                await session.connect(host, ssl_context=ssl_context)
            else:
                await session.connect(host)

            return session

        async def process_production_workload(self, workload: List[Dict]) -> Dict:
            """Process production workload with monitoring and scaling."""
            start_time = asyncio.get_event_loop().time()
            results = []

            # Distribute workload across hosts
            for work_item in workload:
                host = self.load_balancer.select_host(work_item)

                try:
                    # Get session from pool
                    session = await self._get_session_from_pool(host)

                    # Process work item
                    result = await self._process_work_item(session, work_item)
                    results.append(result)

                    # Return session to pool
                    await self._return_session_to_pool(host, session)

                    # Record metrics
                    if self.config.monitoring_enabled:
                        self.metrics_collector.record_success(host, work_item)

                except Exception as e:
                    results.append({"status": "error", "error": str(e)})

                    if self.config.monitoring_enabled:
                        self.metrics_collector.record_failure(host, work_item, e)

            # Check if scaling is needed
            if self.config.monitoring_enabled:
                await self._check_scaling_requirements()

            end_time = asyncio.get_event_loop().time()
            processing_time = end_time - start_time

            # Generate performance report
            report = {
                "total_items": len(workload),
                "successful_items": len([r for r in results if r.get("status") == "success"]),
                "processing_time_seconds": processing_time,
                "items_per_second": len(workload) / processing_time,
                "host_distribution": self.load_balancer.get_distribution_stats()
            }

            return report

        async def _process_work_item(self, session: AsyncSession, work_item: Dict) -> Dict:
            """Process individual work item."""
            operation = work_item.get("operation", "read")
            parameters = work_item.get("parameters", {})

            if operation == "key":
                key = parameters.get("key", "")
                await session.key(key)
                return {"status": "success", "operation": "key", "key": key}

            elif operation == "string":
                text = parameters.get("text", "")
                await session.string(text)
                return {"status": "success", "operation": "string", "text": text[:20] + "..." if len(text) > 20 else text}

            elif operation == "read":
                timeout = parameters.get("timeout", 30.0)
                screen_data = await asyncio.wait_for(session.read(), timeout=timeout)
                screen_text = session.ascii(screen_data)
                return {
                    "status": "success",
                    "operation": "read",
                    "screen_length": len(screen_text),
                    "first_100_chars": screen_text[:100]
                }

            else:
                return {"status": "error", "error": f"Unknown operation: {operation}"}

        async def _check_scaling_requirements(self):
            """Check if automatic scaling is needed."""
            metrics = self.metrics_collector.get_current_metrics()

            for host in self.config.hosts:
                utilization = metrics.get(host, {}).get("utilization_percent", 0)

                if utilization > self.config.scaling_config["autoscale_threshold"]:
                    # Scale up
                    await self._scale_up_host(host)
                elif utilization < 20:  # Scale down threshold
                    # Scale down
                    await self._scale_down_host(host)

        async def _scale_up_host(self, host: str):
            """Scale up sessions for host."""
            current_count = len(self.session_pools.get(host, []))
            max_count = self.config.scaling_config["max_sessions_per_host"]

            if current_count < max_count:
                sessions_to_add = min(5, max_count - current_count)

                for _ in range(sessions_to_add):
                    try:
                        session = await self._create_production_session(host)
                        self.session_pools[host].append(session)
                        print(f"Scaled up: added session to {host}")
                    except Exception as e:
                        print(f"Scale up failed for {host}: {e}")

        async def _scale_down_host(self, host: str):
            """Scale down sessions for host."""
            min_count = self.config.scaling_config["min_sessions_per_host"]
            current_count = len(self.session_pools.get(host, []))

            if current_count > min_count:
                # Remove one session
                session = self.session_pools[host].pop()
                try:
                    await session.close()
                    print(f"Scaled down: removed session from {host}")
                except Exception as e:
                    print(f"Error closing session during scale down: {e}")

        async def shutdown_production_environment(self):
            """Gracefully shutdown production environment."""
            print("Shutting down production environment...")

            # Close all session pools
            for host, pool in self.session_pools.items():
                for session in pool:
                    try:
                        await session.close()
                    except Exception as e:
                        print(f"Error closing session: {e}")

            # Stop monitoring
            if self.metrics_collector:
                await self.metrics_collector.stop()

            if self.alert_manager:
                await self.alert_manager.stop()

            print("Production environment shutdown complete")

    class ProductionMetricsCollector:
        """Production metrics collection and reporting."""

        def __init__(self, config: ProductionConfig):
            self.config = config
            self.metrics: Dict[str, Dict] = {}
            self.collection_task = None

        async def start(self):
            """Start metrics collection."""
            self.collection_task = asyncio.create_task(self._collect_metrics())

        async def stop(self):
            """Stop metrics collection."""
            if self.collection_task:
                self.collection_task.cancel()

        def record_success(self, host: str, work_item: Dict):
            """Record successful operation."""
            if host not in self.metrics:
                self.metrics[host] = {
                    "total_operations": 0,
                    "successful_operations": 0,
                    "failed_operations": 0,
                    "response_times": [],
                    "start_time": asyncio.get_event_loop().time()
                }

            self.metrics[host]["total_operations"] += 1
            self.metrics[host]["successful_operations"] += 1

        def record_failure(self, host: str, work_item: Dict, error: Exception):
            """Record failed operation."""
            if host not in self.metrics:
                self.metrics[host] = {
                    "total_operations": 0,
                    "successful_operations": 0,
                    "failed_operations": 0,
                    "response_times": [],
                    "start_time": asyncio.get_event_loop().time()
                }

            self.metrics[host]["total_operations"] += 1
            self.metrics[host]["failed_operations"] += 1

        def get_current_metrics(self) -> Dict:
            """Get current metrics snapshot."""
            metrics = {}

            for host, data in self.metrics.items():
                total = data["total_operations"]
                if total > 0:
                    success_rate = (data["successful_operations"] / total) * 100
                    error_rate = (data["failed_operations"] / total) * 100

                    metrics[host] = {
                        "total_operations": total,
                        "success_rate_percent": success_rate,
                        "error_rate_percent": error_rate,
                        "availability_percent": success_rate,
                        "utilization_percent": min(100, total / 100)  # Simplified
                    }

            return metrics

        async def _collect_metrics(self):
            """Background metrics collection task."""
            while True:
                try:
                    current_metrics = self.get_current_metrics()

                    # Check performance targets
                    for host, metrics in current_metrics.items():
                        if metrics["response_time_ms"] > self.config.performance_targets["max_response_time_ms"]:
                            print(f"ALERT: {host} response time exceeds target")

                        if metrics["availability_percent"] < self.config.performance_targets["min_availability_percent"]:
                            print(f"ALERT: {host} availability below target")

                        if metrics["error_rate_percent"] > self.config.performance_targets["max_error_rate_percent"]:
                            print(f"ALERT: {host} error rate exceeds target")

                    await asyncio.sleep(60)  # Collect every minute

                except Exception as e:
                    print(f"Metrics collection error: {e}")
                    await asyncio.sleep(10)

    class ProductionAlertManager:
        """Production alerting system."""

        def __init__(self, config: ProductionConfig):
            self.config = config
            self.alert_history: List[Dict] = []
            self.alert_task = None

        async def start(self):
            """Start alert monitoring."""
            self.alert_task = asyncio.create_task(self._monitor_alerts())

        async def stop(self):
            """Stop alert monitoring."""
            if self.alert_task:
                self.alert_task.cancel()

        async def send_alert(self, alert_type: str, message: str, severity: str = "WARNING"):
            """Send alert to appropriate channels."""
            alert = {
                "timestamp": asyncio.get_event_loop().time(),
                "type": alert_type,
                "message": message,
                "severity": severity
            }

            self.alert_history.append(alert)

            # Log alert
            if severity == "CRITICAL":
                logging.critical(f"CRITICAL ALERT: {message}")
            elif severity == "ERROR":
                logging.error(f"ERROR ALERT: {message}")
            else:
                logging.warning(f"WARNING ALERT: {message}")

            # In production, would send to external alert systems
            # (email, Slack, PagerDuty, etc.)

        async def _monitor_alerts(self):
            """Background alert monitoring task."""
            while True:
                try:
                    # Check for alert patterns
                    recent_alerts = [a for a in self.alert_history
                                   if asyncio.get_event_loop().time() - a["timestamp"] < 300]

                    # Detect alert storms
                    if len(recent_alerts) > 10:
                        await self.send_alert(
                            "alert_storm",
                            f"High alert volume: {len(recent_alerts)} alerts in 5 minutes",
                            "CRITICAL"
                        )

                    await asyncio.sleep(30)

                except Exception as e:
                    print(f"Alert monitoring error: {e}")
                    await asyncio.sleep(10)

    class ProductionLoadBalancer:
        """Production load balancer for TN3270 sessions."""

        def __init__(self, config: ProductionConfig):
            self.config = config
            self.host_stats: Dict[str, Dict] = {}

            # Initialize host stats
            for host in config.hosts:
                self.host_stats[host] = {
                    "active_sessions": 0,
                    "total_requests": 0,
                    "avg_response_time": 0.0,
                    "error_count": 0
                }

        def select_host(self, work_item: Dict) -> str:
            """Select optimal host for work item."""
            # Simple round-robin with performance weighting
            return self.config.hosts[0]  # Simplified for demo

        def get_distribution_stats(self) -> Dict:
            """Get load distribution statistics."""
            return self.host_stats

    # Example production deployment
    async def production_deployment_example():
        """Demonstrate enterprise production deployment."""

        # Create deployment manager
        deployment_manager = ProductionDeploymentManager("production_config.yaml")

        try:
            # Initialize production environment
            await deployment_manager.initialize_production_environment()

            # Create sample workload
            workload = [
                {"operation": "read", "parameters": {"timeout": 10.0}},
                {"operation": "string", "parameters": {"text": "LOGON"}},
                {"operation": "key", "parameters": {"key": "ENTER"}},
            ] * 10  # Repeat for load testing

            # Process workload
            report = await deployment_manager.process_production_workload(workload)

            print("Production workload processing report:")
            print(f"  Total items: {report['total_items']}")
            print(f"  Success rate: {report['successful_items']}/{report['total_items']}")
            print(f"  Processing rate: {report['items_per_second']:.2f} items/sec")

            # Get metrics
            if deployment_manager.metrics_collector:
                metrics = deployment_manager.metrics_collector.get_current_metrics()
                print("Current metrics:")
                for host, host_metrics in metrics.items():
                    print(f"  {host}: {host_metrics}")

        finally:
            await deployment_manager.shutdown_production_environment()
