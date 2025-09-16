import asyncio
import multiprocessing as mp
import os
import platform
import resource
import signal
import sys
from typing import Any, Callable, Tuple, Union


def set_memory_limit(max_memory_mb: int):
    """
    Set maximum memory limit for the current process.

    Args:
        max_memory_mb: Maximum memory in megabytes

    Returns:
        Actual limit in bytes if set, None otherwise.

    Note: Unix-only (uses resource.setrlimit). No-op on Windows/other platforms.
    """
    if platform.system() != 'Linux':
        return None

    try:
        max_memory_bytes = max_memory_mb * 1024 * 1024
        # RLIMIT_AS limits total virtual memory
        resource.setrlimit(resource.RLIMIT_AS, (max_memory_bytes, max_memory_bytes))
        return max_memory_bytes
    except Exception:
        return None

def run_with_limits(
    test_func: Callable[..., Any],
    time_limit: float,
    mem_limit: int,
    is_async: bool = False,
    *args,
    **kwargs
) -> Tuple[bool, Union[Any, str]]:
    """
    Run test_func with time and memory limits in an isolated subprocess.

    Args:
        test_func: The test function or method to run.
        time_limit: Maximum execution time in seconds (cross-platform via process timeout).
        mem_limit: Maximum memory in MB (Unix-only via setrlimit).
        is_async: If True, run test_func as async with asyncio.run (child imports asyncio).
        *args, **kwargs: Arguments to pass to test_func.

    Returns:
        Tuple (success: bool, result_or_error: Any or str)

    Notes:
        - Cross-platform time limit via mp.Process.join(timeout); Unix adds signal.alarm for precision.
        - Memory limit Unix-only; Windows no-op (add psutil for monitoring if needed, but avoids dep).
        - Child process inherits code, so @patch/mocks work if applied in test_func.
        - For async: Child does asyncio.run(test_func(*args, **kwargs)).
        - Configurable limits via env vars (see usage in scripts).
        - Exits child with os._exit(124) on Unix timeout for distinction.
    """
    def target(q: mp.Queue, func_args, func_kwargs):
        try:
            # Set memory limit (Unix-only)
            set_memory_limit(mem_limit)

            # Set Unix time limit with signal.alarm
            alarm_set = False
            if os.name == 'posix':
                def timeout_handler(signum, frame):
                    os._exit(124)  # Special exit code for timeout
                original_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(int(time_limit))
                alarm_set = True

            if is_async:
                # For async, run with asyncio (import in child to avoid issues)
                loop_result = asyncio.run(test_func(*func_args, **func_kwargs))
                result = loop_result
            else:
                result = test_func(*func_args, **func_kwargs)

            # Cancel alarm if set
            if alarm_set:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, original_handler)

            q.put(('success', result))
        except Exception as e:
            if alarm_set:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, original_handler)
            q.put(('error', str(e)))
        finally:
            q.put('done')

    q = mp.Queue()
    args_tuple = args if args else ()
    kwargs_dict = kwargs if kwargs else {}
    p = mp.Process(target=target, args=(q, args_tuple, kwargs_dict))
    p.start()

    # Wait with timeout
    p.join(timeout=time_limit)

    if p.is_alive():
        # Timeout: terminate and check exit code if Unix
        p.terminate()
        p.join()  # Wait for termination
        if os.name == 'posix' and p.exitcode == 124:
            return (False, f'Timeout after {time_limit}s (signal.alarm)')
        else:
            return (False, f'Timeout after {time_limit}s (process join)')

    # Get result from queue
    try:
        while True:
            msg = q.get_nowait()
            if msg == 'done':
                continue
            status, res = msg
            if status == 'success':
                return (True, res)
            else:
                return (False, res)
    except mp.queues.Empty:
        return (False, 'Process completed without result in queue')

# Convenience wrappers
def run_with_limits_sync(test_func: Callable, time_limit: float, mem_limit: int, *args, **kwargs) -> Tuple[bool, Union[Any, str]]:
    """Sync wrapper for run_with_limits."""
    return run_with_limits(test_func, time_limit, mem_limit, False, *args, **kwargs)

def run_with_limits_async(test_func: Callable, time_limit: float, mem_limit: int, *args, **kwargs) -> Tuple[bool, Union[Any, str]]:
    """Async wrapper for run_with_limits (runs asyncio.run in child)."""
    return run_with_limits(test_func, time_limit, mem_limit, True, *args, **kwargs)

# Limit getters for configurability
def get_unit_limits() -> Tuple[float, int]:
    """Get unit test limits (default 5s/100MB)."""
    time_limit = float(os.getenv('UNIT_TIME_LIMIT', '5'))
    mem_limit = int(os.getenv('UNIT_MEM_LIMIT', '100'))
    return time_limit, mem_limit

def get_integration_limits() -> Tuple[float, int]:
    """Get integration test limits (default 10s/200MB)."""
    time_limit = float(os.getenv('INT_TIME_LIMIT', '10'))
    mem_limit = int(os.getenv('INT_MEM_LIMIT', '200'))
    return time_limit, mem_limit
