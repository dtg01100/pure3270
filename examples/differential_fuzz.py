"""Fuzz testing for pure3270 robustness and behavioral analysis.

This script performs comprehensive fuzz testing by generating random sequences
of TN3270 operations to identify crashes, unexpected behavior, and edge cases
in pure3270 implementation.
"""

import argparse
import asyncio
import json
import random
import statistics
import subprocess
import sys
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from pure3270.p3270_client import P3270Client

# Fuzz configuration
HOST = "127.0.0.1"
PORT = 2324  # Different port for mock server
MAX_SEQUENCES = 5  # Quick test
MAX_COMMANDS_PER_SEQUENCE = 20  # More commands per sequence
FUZZ_SEED = 456  # Different seed for round 2

# Network simulation settings
ENABLE_NETWORK_SIMULATION = True
LATENCY_MS = (10, 100)  # Min/max latency in ms
PACKET_LOSS_RATE = 0.05  # 5% packet loss
JITTER_MS = 20  # Jitter variation

# Possible commands to fuzz
FUZZ_COMMANDS = [
    # Basic navigation and input
    "Enter",
    "Tab",
    "BackTab",
    "Home",
    "Newline",
    "BackSpace",
    # Function keys (PF1-PF24)
    "PF(1)",
    "PF(2)",
    "PF(3)",
    "PF(4)",
    "PF(5)",
    "PF(6)",
    "PF(7)",
    "PF(8)",
    "PF(9)",
    "PF(10)",
    "PF(11)",
    "PF(12)",
    "PF(13)",
    "PF(14)",
    "PF(15)",
    "PF(16)",
    "PF(17)",
    "PF(18)",
    "PF(19)",
    "PF(20)",
    "PF(21)",
    "PF(22)",
    "PF(23)",
    "PF(24)",
    # Program attention keys
    "PA(1)",
    "PA(2)",
    "PA(3)",
    # Screen operations
    "Clear",
    "EraseEOF",
    "EraseInput",
    "Erase",
    # Field operations
    "Dup",
    "FieldMark",
    "FieldEnd",
    # Cursor movement
    "Up",
    "Down",
    "Left",
    "Right",
    "Left2",
    "Right2",
    # Special keys
    "SysReq",
    "Attn",
    "Test",
    "Reset",
    # System operations
    "CircumNot",
]

# Commands that might produce text input
TEXT_COMMANDS = [
    "String(test)",
    "String(hello world)",
    "String(123456)",
    "String(!@#$%^&*)",
    "String(ABCDEFGHIJKLMNOPQRSTUVWXYZ)",
    "String(abcdefghijklmnopqrstuvwxyz)",
    "String(0123456789)",
    "String(\x00\x01\x02\x03\x04\x05)",  # Control characters
    "String(🌟🚀💻)",  # Unicode
    "String(very_long_string_" + "x" * 100 + ")",  # Long string
    "String()",  # Empty string
]

# Special edge case commands
EDGE_CASE_COMMANDS = [
    "HexString(414243)",  # ABC in hex
    "HexString(00FF)",  # Binary data
    "HexString()",  # Empty hex
    "Key(Enter)",  # Alternative key syntax
    "Key(PF1)",
    "MoveCursor(0,0)",  # Cursor positioning
    "MoveCursor(23,79)",  # Bottom right
    "MoveCursor(-1,-1)",  # Invalid coordinates
    "Ascii(0,0,10)",  # Screen reading
    "Wait(0.1)",  # Timing
    "Pause(0.1)",
]


def parse_arguments():
    """Parse command-line arguments for fuzz testing configuration."""
    parser = argparse.ArgumentParser(
        description="Fuzz testing for pure3270 robustness and behavioral analysis"
    )

    # Basic configuration
    parser.add_argument(
        "--host", default=HOST, help=f"TN3270 server host (default: {HOST})"
    )
    parser.add_argument(
        "--port", type=int, default=PORT, help=f"TN3270 server port (default: {PORT})"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=FUZZ_SEED,
        help=f"Random seed for reproducible tests (default: {FUZZ_SEED})",
    )

    # Continuous running options
    parser.add_argument(
        "--continuous", action="store_true", help="Enable continuous running mode"
    )
    parser.add_argument(
        "--max-duration",
        type=int,
        help="Maximum test duration in seconds (0 for unlimited)",
    )
    parser.add_argument(
        "--max-sequences",
        type=int,
        default=MAX_SEQUENCES,
        help=f"Maximum number of sequences to test (default: {MAX_SEQUENCES})",
    )

    # Stopping conditions
    parser.add_argument(
        "--stop-on-issues", type=int, help="Stop after finding this many issues"
    )
    parser.add_argument(
        "--stop-on-crashes", type=int, help="Stop after finding this many crashes"
    )
    parser.add_argument(
        "--stop-on-errors", type=int, help="Stop after finding this many errors"
    )

    # Checkpointing
    parser.add_argument(
        "--checkpoint-file", help="File to save/load checkpoints for resumable testing"
    )
    parser.add_argument(
        "--checkpoint-interval",
        type=int,
        default=100,
        help="Save checkpoint every N sequences (default: 100)",
    )

    # Network simulation
    parser.add_argument(
        "--no-network-sim", action="store_true", help="Disable network simulation"
    )
    parser.add_argument(
        "--latency",
        type=str,
        default=f"{LATENCY_MS[0]}-{LATENCY_MS[1]}",
        help=f"Network latency range in ms (default: {LATENCY_MS[0]}-{LATENCY_MS[1]})",
    )
    parser.add_argument(
        "--packet-loss",
        type=float,
        default=PACKET_LOSS_RATE,
        help=f"Packet loss rate (0.0-1.0) (default: {PACKET_LOSS_RATE})",
    )
    parser.add_argument(
        "--jitter",
        type=int,
        default=JITTER_MS,
        help=f"Network jitter in ms (default: {JITTER_MS})",
    )

    return parser.parse_args()


class FuzzTester:
    """Fuzz tester for pure3270 robustness and behavioral analysis."""

    def __init__(self, host: str, port: int, seed: int = FUZZ_SEED):
        self.host = host
        self.port = port
        self.seed = seed
        self.random = random.Random(seed)
        self.issues_found = 0
        self.sequences_tested = 0
        self.crashes_found = 0
        self.errors_found = 0
        self.unexpected_behavior = 0
        self.network_timeouts = 0
        self.connection_failures = 0
        self.sequence_times = []
        self.start_time = None
        self.end_time = None

        # Detailed issue tracking for results file
        self.detailed_issues: List[Dict[str, Any]] = []

        # Checkpointing support
        self.checkpoint_file = None
        self.checkpoint_interval = 100
        self.last_checkpoint_time = 0

    def save_checkpoint(self, checkpoint_file: str):
        """Save current testing state to a checkpoint file."""
        checkpoint_data = {
            "seed": self.seed,
            "sequences_tested": self.sequences_tested,
            "issues_found": self.issues_found,
            "crashes_found": self.crashes_found,
            "errors_found": self.errors_found,
            "unexpected_behavior": self.unexpected_behavior,
            "network_timeouts": self.network_timeouts,
            "connection_failures": self.connection_failures,
            "sequence_times": self.sequence_times,
            "start_time": self.start_time,
            "detailed_issues": self.detailed_issues,
            "random_state": self.random.getstate(),
            "timestamp": time.time(),
        }

        try:
            with open(checkpoint_file, "w") as f:
                json.dump(checkpoint_data, f, indent=2, default=str)
            print(
                f"Checkpoint saved to {checkpoint_file} (sequences: {self.sequences_tested})"
            )
        except Exception as e:
            print(f"Failed to save checkpoint: {e}")

    def load_checkpoint(self, checkpoint_file: str) -> bool:
        """Load testing state from a checkpoint file. Returns True if loaded successfully."""
        try:
            with open(checkpoint_file, "r") as f:
                checkpoint_data = json.load(f)

            self.sequences_tested = checkpoint_data.get("sequences_tested", 0)
            self.issues_found = checkpoint_data.get("issues_found", 0)
            self.crashes_found = checkpoint_data.get("crashes_found", 0)
            self.errors_found = checkpoint_data.get("errors_found", 0)
            self.unexpected_behavior = checkpoint_data.get("unexpected_behavior", 0)
            self.network_timeouts = checkpoint_data.get("network_timeouts", 0)
            self.connection_failures = checkpoint_data.get("connection_failures", 0)
            self.sequence_times = checkpoint_data.get("sequence_times", [])
            self.start_time = checkpoint_data.get("start_time", time.time())
            self.detailed_issues = checkpoint_data.get("detailed_issues", [])

            # Restore random state for reproducible continuation
            if "random_state" in checkpoint_data:
                random_state = checkpoint_data["random_state"]
                # Convert list back to tuple structure expected by random.setstate
                # Format: [version, [mersenne_values], gauss_next]
                if isinstance(random_state, list) and len(random_state) >= 2:
                    try:
                        version = random_state[0]
                        mersenne_values = (
                            tuple(random_state[1])
                            if isinstance(random_state[1], list)
                            else random_state[1]
                        )
                        gauss_next = random_state[2] if len(random_state) > 2 else None
                        self.random.setstate((version, mersenne_values, gauss_next))
                    except (IndexError, TypeError) as e:
                        print(
                            f"Warning: Could not restore random state: {e}, continuing with current state"
                        )
                else:
                    print(
                        "Warning: Invalid random state format in checkpoint, continuing with current state"
                    )

            print(
                f"Checkpoint loaded from {checkpoint_file} (sequences: {self.sequences_tested})"
            )
            return True
        except FileNotFoundError:
            print(f"No checkpoint file found at {checkpoint_file}, starting fresh")
            return False
        except Exception as e:
            print(f"Failed to load checkpoint: {e}")
            return False

    def should_save_checkpoint(self, current_sequence: int) -> bool:
        """Check if we should save a checkpoint based on interval and time."""
        if not self.checkpoint_file:
            return False

        # Check sequence interval
        if current_sequence % self.checkpoint_interval == 0:
            return True

        # Check time interval (save every 5 minutes)
        current_time = time.time()
        if current_time - self.last_checkpoint_time > 300:  # 5 minutes
            self.last_checkpoint_time = current_time
            return True

        return False

    def generate_command_sequence(self) -> List[str]:
        """Generate a random sequence of commands with diverse patterns."""
        num_commands = self.random.randint(1, MAX_COMMANDS_PER_SEQUENCE)
        commands = []

        for i in range(num_commands):
            rand_val = self.random.random()

            if rand_val < 0.25:  # 25% chance of text input
                cmd = self.random.choice(TEXT_COMMANDS)
            elif rand_val < 0.45:  # 20% chance of edge cases
                cmd = self.random.choice(EDGE_CASE_COMMANDS)
            else:  # 55% chance of regular commands
                cmd = self.random.choice(FUZZ_COMMANDS)

            commands.append(cmd)

        # Add some pattern-based sequences for better coverage
        if self.random.random() < 0.3:  # 30% chance to add a common workflow pattern
            pattern = self.random.choice(
                [
                    [
                        "String(login)",
                        "Tab",
                        "String(password)",
                        "Enter",
                    ],  # Login sequence
                    [
                        "Clear",
                        "String(data)",
                        "Tab",
                        "String(more)",
                        "Enter",
                    ],  # Data entry
                    [
                        "Home",
                        "String(header)",
                        "Newline",
                        "String(body)",
                        "Enter",
                    ],  # Form filling
                    [
                        "PF(1)",
                        "Wait(0.5)",
                        "PF(2)",
                        "String(test)",
                        "Enter",
                    ],  # Menu navigation
                ]
            )
            commands.extend(pattern)

        return commands

    def normalize_screen(self, screen: str) -> str:
        """Normalize screen output for comparison."""
        # Remove timestamps, connection messages, etc.
        lines = screen.split("\n")
        # Keep only the main screen content (typically lines 2-25 for 3270)
        if len(lines) > 25:
            lines = lines[1:25]  # Skip first line, take next 24
        return "\n".join(lines).strip()

    def test_sequence(self, sequence: List[str]) -> bool:
        """Test a single command sequence for robustness."""
        self.sequences_tested += 1
        sequence_start = time.time()

        # Start pure3270 session
        p3270 = P3270Client(hostName=self.host, hostPort=self.port)
        initial_screen = ""
        errors_encountered = []

        try:
            # Connect
            p3270.connect()
            initial_screen = self.normalize_screen(p3270.getScreen())

            # Execute command sequence
            for i, cmd in enumerate(sequence):
                try:
                    # Send to pure3270
                    if cmd.startswith("String("):
                        text = cmd[7:-1]  # Extract text from String(text)
                        p3270.sendText(text)
                    elif cmd == "Enter":
                        p3270.sendEnter()
                    elif cmd.startswith("PF("):
                        key_num = int(cmd[3:-1])  # Extract from PF(num)
                        p3270.sendPF(key_num)
                    elif cmd.startswith("PA("):
                        key_num = int(cmd[3:-1])  # Extract from PA(num)
                        p3270.sendPA(key_num)
                    elif cmd == "Clear":
                        p3270.clearScreen()
                    elif cmd == "CLEAR":
                        p3270.clearScreen()
                    elif cmd == "Tab":
                        p3270.sendTab()
                    elif cmd == "Home":
                        p3270.sendHome()
                    elif cmd == "BackTab":
                        p3270.sendBackTab()
                    else:
                        # For other commands, try to send directly
                        try:
                            p3270._sendCommand(cmd)
                        except Exception as e:
                            errors_encountered.append(f"Command {i} ({cmd}): {e}")
                            self.errors_found += 1

                    # Small delay between commands
                    time.sleep(0.05)

                except Exception as e:
                    errors_encountered.append(f"Command {i} ({cmd}): {e}")
                    self.errors_found += 1
                    # Continue testing despite errors

            # Get final screen
            final_screen = self.normalize_screen(p3270.getScreen())

            # Analyze results
            if errors_encountered:
                self.issues_found += 1
                print(f"ISSUES FOUND in sequence {self.sequences_tested}:")
                for error in errors_encountered:
                    print(f"  {error}")
                    # Check for network-related errors
                    error_str = str(error).lower()
                    if "timeout" in error_str:
                        self.network_timeouts += 1
                    elif "connection" in error_str or "reset" in error_str:
                        self.connection_failures += 1

                print(f"Command sequence: {sequence}")

                # Record detailed issue
                self.detailed_issues.append(
                    {
                        "sequence_number": self.sequences_tested,
                        "issue_type": "command_errors",
                        "command_sequence": sequence,
                        "errors": errors_encountered,
                        "initial_screen": initial_screen,
                        "final_screen": final_screen,
                        "timestamp": time.time(),
                    }
                )
                return False

            # Check for unexpected behavior (screen should change or stay same predictably)
            screen_changed = initial_screen != final_screen
            has_input_commands = any(
                cmd.startswith(("String(", "HexString(")) for cmd in sequence
            )
            has_pure_navigation = any(
                cmd
                in [
                    "Tab",
                    "BackTab",
                    "Home",
                    "Newline",
                    "Left",
                    "Right",
                    "Up",
                    "Down",
                    "Left2",
                    "Right2",
                    "BackSpace",
                ]
                for cmd in sequence
            )
            has_screen_modifying_commands = any(
                cmd.startswith(
                    (
                        "PF(",
                        "PA(",
                        "Erase",
                        "Clear",
                        "Enter",
                        "Test",
                        "SysReq",
                        "Attn",
                        "Reset",
                        "Delete",
                        "CircumNot",
                        "FieldMark",
                        "Dup",
                        "FieldExit",
                        "Key(",
                    )
                )
                or cmd
                in [
                    "Enter",
                    "Clear",
                    "Test",
                    "SysReq",
                    "Attn",
                    "Reset",
                    "DeleteField",
                    "DeleteWord",
                    "Erase",
                    "EraseEOF",
                    "EraseInput",
                    "FieldEnd",
                    "FieldMark",
                    "Dup",
                    "FieldExit",
                    "CircumNot",
                ]
                for cmd in sequence
            )

            # Flag if input commands were sent but screen didn't change (might indicate issues)
            if has_input_commands and not screen_changed and len(sequence) > 1:
                self.unexpected_behavior += 1
                print(f"UNEXPECTED BEHAVIOR in sequence {self.sequences_tested}:")
                print("Input commands sent but screen unchanged")
                print(f"Command sequence: {sequence}")

                # Record detailed issue
                self.detailed_issues.append(
                    {
                        "sequence_number": self.sequences_tested,
                        "issue_type": "input_no_screen_change",
                        "command_sequence": sequence,
                        "description": "Input commands were sent but screen did not change",
                        "initial_screen": initial_screen,
                        "final_screen": final_screen,
                        "has_input_commands": has_input_commands,
                        "has_pure_navigation": has_pure_navigation,
                        "has_screen_modifying_commands": has_screen_modifying_commands,
                        "screen_changed": screen_changed,
                        "timestamp": time.time(),
                    }
                )
                return False

            # Flag if only pure navigation commands caused screen changes (these should not change screen)
            if (
                not has_screen_modifying_commands
                and not has_input_commands
                and screen_changed
                and len(sequence) > 3
            ):
                self.unexpected_behavior += 1
                print(f"UNEXPECTED BEHAVIOR in sequence {self.sequences_tested}:")
                print("Pure navigation commands caused screen changes")
                print(f"Command sequence: {sequence}")

                # Record detailed issue
                self.detailed_issues.append(
                    {
                        "sequence_number": self.sequences_tested,
                        "issue_type": "navigation_screen_change",
                        "command_sequence": sequence,
                        "description": "Pure navigation commands caused unexpected screen changes",
                        "initial_screen": initial_screen,
                        "final_screen": final_screen,
                        "has_input_commands": has_input_commands,
                        "has_pure_navigation": has_pure_navigation,
                        "has_screen_modifying_commands": has_screen_modifying_commands,
                        "screen_changed": screen_changed,
                        "timestamp": time.time(),
                    }
                )
                return False

            sequence_time = time.time() - sequence_start
            self.sequence_times.append(sequence_time)
            print(f"Sequence {self.sequences_tested}: OK ({sequence_time:.3f}s)")
            return True

        except Exception as e:
            sequence_time = time.time() - sequence_start
            self.sequence_times.append(sequence_time)
            self.crashes_found += 1
            print(
                f"CRASH in sequence {self.sequences_tested}: {e} ({sequence_time:.3f}s)"
            )
            print(f"Command sequence: {sequence}")

            # Record detailed issue
            self.detailed_issues.append(
                {
                    "sequence_number": self.sequences_tested,
                    "issue_type": "crash",
                    "command_sequence": sequence,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "sequence_time": sequence_time,
                    "timestamp": time.time(),
                }
            )
            return False
        finally:
            try:
                p3270.disconnect()
            except:
                pass

    def run_fuzz_test(
        self,
        max_sequences: int = MAX_SEQUENCES,
        max_duration: Optional[int] = None,
        stop_on_issues: Optional[int] = None,
        stop_on_crashes: Optional[int] = None,
        stop_on_errors: Optional[int] = None,
        continuous: bool = False,
        checkpoint_file: Optional[str] = None,
        checkpoint_interval: int = 100,
    ) -> Tuple[int, int]:
        """Run the fuzz test with multiple random sequences."""
        # Configure checkpointing
        self.checkpoint_file = checkpoint_file
        self.checkpoint_interval = checkpoint_interval

        # Load checkpoint if available
        if checkpoint_file and not continuous:
            self.load_checkpoint(checkpoint_file)

        print(f"Starting fuzz test with seed {self.seed}")
        if max_duration:
            print(f"Testing for maximum {max_duration} seconds...")
        else:
            print(f"Testing {max_sequences} random sequences...")

        if not self.start_time:
            self.start_time = time.time()

        sequence_start = self.sequences_tested

        try:
            while True:
                # Check stopping conditions
                current_time = time.time()
                elapsed_time = current_time - self.start_time

                if max_duration and elapsed_time >= max_duration:
                    print(f"Stopping: Maximum duration of {max_duration}s reached")
                    break

                if self.sequences_tested >= max_sequences:
                    print(f"Stopping: Maximum sequences of {max_sequences} reached")
                    break

                if stop_on_issues and self.issues_found >= stop_on_issues:
                    print(
                        f"Stopping: Found {self.issues_found} issues (limit: {stop_on_issues})"
                    )
                    break

                if stop_on_crashes and self.crashes_found >= stop_on_crashes:
                    print(
                        f"Stopping: Found {self.crashes_found} crashes (limit: {stop_on_crashes})"
                    )
                    break

                if stop_on_errors and self.errors_found >= stop_on_errors:
                    print(
                        f"Stopping: Found {self.errors_found} errors (limit: {stop_on_errors})"
                    )
                    break

                sequence = self.generate_command_sequence()
                sequence_num = self.sequences_tested + 1
                print(f"\nTesting sequence {sequence_num}: {sequence}")
                self.test_sequence(sequence)

                # Save checkpoint if needed
                if self.should_save_checkpoint(sequence_num) and checkpoint_file:
                    self.save_checkpoint(checkpoint_file)

                # Small delay between sequences to prevent overwhelming the system
                time.sleep(0.1)

        except KeyboardInterrupt:
            print("\nTest interrupted by user")
        finally:
            self.end_time = time.time()
        total_time = self.end_time - self.start_time

        print("\nFuzz test completed:")
        print(f"Sequences tested: {self.sequences_tested}")
        print(f"Issues found: {self.issues_found}")
        print(f"Crashes found: {self.crashes_found}")
        print(f"Errors found: {self.errors_found}")
        print(f"Unexpected behavior: {self.unexpected_behavior}")
        print(f"Network timeouts: {self.network_timeouts}")
        print(f"Connection failures: {self.connection_failures}")

        # Performance statistics
        if self.sequence_times:
            print(f"\nPerformance Statistics:")
            print(f"Total test time: {total_time:.2f}s")
            print(f"Average sequence time: {statistics.mean(self.sequence_times):.3f}s")
            print(
                f"Median sequence time: {statistics.median(self.sequence_times):.3f}s"
            )
            print(f"Min sequence time: {min(self.sequence_times):.3f}s")
            print(f"Max sequence time: {max(self.sequence_times):.3f}s")
            print(f"Sequences per second: {self.sequences_tested / total_time:.2f}")

        if ENABLE_NETWORK_SIMULATION:
            print(
                f"Network simulation: ENABLED (latency: {LATENCY_MS}ms, loss: {PACKET_LOSS_RATE*100}%, jitter: {JITTER_MS}ms)"
            )
        else:
            print("Network simulation: DISABLED")

        # Save results to file for CI artifacts
        import json
        import os

        os.makedirs("test_output", exist_ok=True)

        # Basic summary file
        with open("test_output/fuzz_test_results.txt", "w") as f:
            f.write("Fuzz Test Results\n")
            f.write("==================\n\n")
            f.write(f"Sequences tested: {self.sequences_tested}\n")
            f.write(f"Issues found: {self.issues_found}\n")
            f.write(f"Crashes found: {self.crashes_found}\n")
            f.write(f"Errors found: {self.errors_found}\n")
            f.write(f"Unexpected behavior: {self.unexpected_behavior}\n")
            f.write(f"Network timeouts: {self.network_timeouts}\n")
            f.write(f"Connection failures: {self.connection_failures}\n\n")

            if self.sequence_times:
                f.write("Performance Statistics:\n")
                f.write("-" * 25 + "\n")
                f.write(f"Total test time: {total_time:.2f}s\n")
                f.write(
                    f"Average sequence time: {statistics.mean(self.sequence_times):.3f}s\n"
                )
                f.write(
                    f"Median sequence time: {statistics.median(self.sequence_times):.3f}s\n"
                )
                f.write(
                    f"Min sequence time: {statistics.mean(self.sequence_times):.3f}s\n"
                )
                f.write(
                    f"Max sequence time: {statistics.mean(self.sequence_times):.3f}s\n"
                )
                f.write(
                    f"Sequences per second: {self.sequences_tested / total_time:.2f}\n\n"
                )

            network_status = "ENABLED" if ENABLE_NETWORK_SIMULATION else "DISABLED"
            f.write(f"Network simulation: {network_status}\n")
            if ENABLE_NETWORK_SIMULATION:
                f.write(f"  Latency: {LATENCY_MS}ms\n")
                f.write(f"  Packet loss: {PACKET_LOSS_RATE*100}%\n")
                f.write(f"  Jitter: {JITTER_MS}ms\n")

            f.write(f"\nTest result: {'PASS' if self.issues_found == 0 else 'FAIL'}\n")

        # Detailed issues file (only if issues were found)
        if self.detailed_issues:
            with open("test_output/fuzz_test_detailed_issues.json", "w") as f:
                json.dump(
                    {
                        "test_run": {
                            "seed": self.seed,
                            "sequences_tested": self.sequences_tested,
                            "total_time": total_time,
                            "network_simulation": ENABLE_NETWORK_SIMULATION,
                            "latency_ms": (
                                LATENCY_MS if ENABLE_NETWORK_SIMULATION else None
                            ),
                            "packet_loss_rate": (
                                PACKET_LOSS_RATE if ENABLE_NETWORK_SIMULATION else None
                            ),
                            "jitter_ms": (
                                JITTER_MS if ENABLE_NETWORK_SIMULATION else None
                            ),
                        },
                        "summary": {
                            "issues_found": self.issues_found,
                            "crashes_found": self.crashes_found,
                            "errors_found": self.errors_found,
                            "unexpected_behavior": self.unexpected_behavior,
                            "network_timeouts": self.network_timeouts,
                            "connection_failures": self.connection_failures,
                        },
                        "issues": self.detailed_issues,
                    },
                    f,
                    indent=2,
                    default=str,
                )

            # Also create a human-readable detailed issues file
            with open("test_output/fuzz_test_detailed_issues.txt", "w") as f:
                f.write("Detailed Fuzz Test Issues\n")
                f.write("=========================\n\n")
                f.write(f"Test run with seed: {self.seed}\n")
                f.write(f"Total sequences tested: {self.sequences_tested}\n")
                f.write(f"Total issues found: {len(self.detailed_issues)}\n\n")

                for i, issue in enumerate(self.detailed_issues, 1):
                    f.write(f"Issue #{i}\n")
                    f.write("-" * 20 + "\n")
                    f.write(f"Sequence number: {issue['sequence_number']}\n")
                    f.write(f"Issue type: {issue['issue_type']}\n")
                    f.write(f"Command sequence: {issue['command_sequence']}\n")

                    if "description" in issue:
                        f.write(f"Description: {issue['description']}\n")

                    if "error" in issue:
                        f.write(f"Error: {issue['error']}\n")
                        if "error_type" in issue:
                            f.write(f"Error type: {issue['error_type']}\n")

                    if "errors" in issue:
                        f.write("Command errors:\n")
                        for error in issue["errors"]:
                            f.write(f"  - {error}\n")

                    if "sequence_time" in issue:
                        f.write(
                            f"Sequence execution time: {issue['sequence_time']:.3f}s\n"
                        )

                    if "initial_screen" in issue and "final_screen" in issue:
                        f.write("Screen state:\n")
                        f.write(
                            f"  Screen changed: {issue.get('screen_changed', 'unknown')}\n"
                        )
                        f.write("  Initial screen (first 200 chars):\n")
                        f.write(
                            f"    {issue['initial_screen'][:200]}{'...' if len(issue['initial_screen']) > 200 else ''}\n"
                        )
                        f.write("  Final screen (first 200 chars):\n")
                        f.write(
                            f"    {issue['final_screen'][:200]}{'...' if len(issue['final_screen']) > 200 else ''}\n"
                        )

                    if "has_input_commands" in issue:
                        f.write(f"Command analysis:\n")
                        f.write(
                            f"  Has input commands: {issue['has_input_commands']}\n"
                        )
                        f.write(
                            f"  Has pure navigation: {issue['has_pure_navigation']}\n"
                        )
                        f.write(
                            f"  Has screen modifying commands: {issue['has_screen_modifying_commands']}\n"
                        )

                    f.write(f"Timestamp: {issue['timestamp']}\n\n")

        total_issues = (
            self.issues_found
            + self.crashes_found
            + self.errors_found
            + self.unexpected_behavior
        )
        return self.sequences_tested, total_issues


class MockTN3270Server:
    """Mock TN3270 server for fuzz testing with network simulation."""

    def __init__(self, host: str = "127.0.0.1", port: int = 2324):
        self.host = host
        self.port = port
        self.server = None
        self.running = False
        self.connections_handled = 0
        self.errors_encountered = 0
        self.packets_sent = 0
        self.packets_lost = 0
        self.total_latency_ms = 0
        self.random = random.Random(
            FUZZ_SEED + 1
        )  # Different seed for network simulation

    def simulate_network_delay(self) -> float:
        """Simulate network latency with jitter."""
        if not ENABLE_NETWORK_SIMULATION:
            return 0.0

        base_latency = self.random.uniform(LATENCY_MS[0], LATENCY_MS[1])
        jitter = self.random.uniform(-JITTER_MS, JITTER_MS)
        delay_ms = max(0, base_latency + jitter)
        self.total_latency_ms += delay_ms
        return delay_ms / 1000.0  # Convert to seconds

    def simulate_packet_loss(self) -> bool:
        """Simulate packet loss."""
        if not ENABLE_NETWORK_SIMULATION:
            return False

        lost = self.random.random() < PACKET_LOSS_RATE
        if lost:
            self.packets_lost += 1
        else:
            self.packets_sent += 1
        return lost

    async def handle_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        """Handle a client connection."""
        self.connections_handled += 1
        client_addr = writer.get_extra_info("peername")
        print(
            f"Mock server: New connection from {client_addr} (#{self.connections_handled})"
        )

        try:
            # Basic TN3270 handshake - just accept negotiations
            buffer = bytearray()

            while True:
                try:
                    data = await asyncio.wait_for(reader.read(1024), timeout=1.0)
                    if not data:
                        break

                    buffer.extend(data)

                    # Simple IAC handling - just acknowledge
                    if b"\xff" in buffer:  # IAC
                        # Simulate network conditions for IAC response
                        delay = self.simulate_network_delay()
                        if delay > 0:
                            await asyncio.sleep(delay)

                        if not self.simulate_packet_loss():
                            # Send DO TERMINAL-TYPE response
                            response = b"\xff\xfa\x18\x01IBM-3278-2\xff\xf0"  # SB TERMINAL-TYPE IS IBM-3278-2 SE
                            writer.write(response)
                            await writer.drain()

                        # Clear IAC commands from buffer
                        buffer = buffer.replace(
                            b"\xff\xfb\x18", b""
                        )  # WILL TERMINAL-TYPE
                        buffer = buffer.replace(
                            b"\xff\xfd\x18", b""
                        )  # DO TERMINAL-TYPE

                    # Send a basic screen update occasionally
                    if len(buffer) > 10:
                        # Simulate network conditions before sending
                        delay = self.simulate_network_delay()
                        if delay > 0:
                            await asyncio.sleep(delay)

                        if not self.simulate_packet_loss():
                            # Send a simple TN3270 data stream with some text
                            screen_data = (
                                b"\x00\x00\x00\x00\x00\x00"  # TN3270 header
                                b"\x00\x00\x00\x00\x00\x00"  # More header
                                b"\x00\x00\x00\x00\x00\x00"  # More header
                                b"\x00\x00\x00\x00\x00\x00"  # More header
                                b"\x00\x00\x00\x00\x00\x00"  # More header
                                b"\x00\x00\x00\x00\x00\x00"  # More header
                            )
                            writer.write(screen_data)
                            await writer.drain()
                        buffer.clear()

                except asyncio.TimeoutError:
                    # Send periodic keepalive with network simulation
                    delay = self.simulate_network_delay()
                    if delay > 0:
                        await asyncio.sleep(delay)

                    if not self.simulate_packet_loss():
                        writer.write(b"\x00")
                        await writer.drain()
                except Exception as e:
                    self.errors_encountered += 1
                    print(f"Mock server error: {e}")
                    break

        except Exception as e:
            self.errors_encountered += 1
            print(f"Mock server connection error: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            print(f"Mock server: Connection from {client_addr} closed")

    async def start_server(self):
        """Start the mock server."""
        self.server = await asyncio.start_server(
            self.handle_connection, self.host, self.port
        )
        self.running = True
        print(f"Mock TN3270 server started on {self.host}:{self.port}")

        try:
            async with self.server:
                await self.server.serve_forever()
        except Exception as e:
            print(f"Mock server error: {e}")
        finally:
            self.running = False

    def start_in_thread(self):
        """Start the server in a background thread."""

        def run_server():
            asyncio.run(self.start_server())

        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
        time.sleep(1)  # Wait for server to start
        return thread

    def get_stats(self) -> Dict[str, Any]:
        """Get server statistics."""
        packet_loss_rate = (
            (self.packets_lost / (self.packets_sent + self.packets_lost)) * 100
            if (self.packets_sent + self.packets_lost) > 0
            else 0
        )
        avg_latency = (
            self.total_latency_ms / (self.packets_sent + self.packets_lost)
            if (self.packets_sent + self.packets_lost) > 0
            else 0
        )

        return {
            "connections_handled": self.connections_handled,
            "errors_encountered": self.errors_encountered,
            "running": self.running,
            "packets_sent": self.packets_sent,
            "packets_lost": self.packets_lost,
            "packet_loss_rate_percent": round(packet_loss_rate, 2),
            "average_latency_ms": round(avg_latency, 2),
            "network_simulation_enabled": ENABLE_NETWORK_SIMULATION,
        }


def main() -> int:
    """Main entry point."""
    args = parse_arguments()

    # Update global configuration based on arguments
    global ENABLE_NETWORK_SIMULATION, LATENCY_MS, PACKET_LOSS_RATE, JITTER_MS

    ENABLE_NETWORK_SIMULATION = not args.no_network_sim
    if args.latency:
        try:
            latency_parts = args.latency.split("-")
            LATENCY_MS = (int(latency_parts[0]), int(latency_parts[1]))
        except (ValueError, IndexError):
            print(f"Invalid latency format: {args.latency}, using default {LATENCY_MS}")
    PACKET_LOSS_RATE = args.packet_loss
    JITTER_MS = args.jitter

    # Start mock TN3270 server
    print("Starting mock TN3270 server...")
    mock_server = MockTN3270Server(args.host, args.port)
    server_thread = mock_server.start_in_thread()

    try:
        tester = FuzzTester(args.host, args.port, args.seed)
        sequences, differences = tester.run_fuzz_test(
            max_sequences=args.max_sequences,
            max_duration=args.max_duration,
            stop_on_issues=args.stop_on_issues,
            stop_on_crashes=args.stop_on_crashes,
            stop_on_errors=args.stop_on_errors,
            continuous=args.continuous,
            checkpoint_file=args.checkpoint_file,
            checkpoint_interval=args.checkpoint_interval,
        )

        print(f"\nServer stats: {mock_server.get_stats()}")

        if differences > 0:
            print(f"\n⚠️  Found {differences} behavioral differences")
            return 1
        else:
            print("\n✅ No differences found - implementation is robust")
            return 0
    finally:
        print("Stopping server...")
        # The server thread will be terminated when main exits


if __name__ == "__main__":
    raise SystemExit(main())
