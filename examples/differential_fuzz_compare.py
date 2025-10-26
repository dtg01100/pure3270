#!/usr/bin/env python3
"""
Differential fuzz: compare pure3270 P3270Client vs local s3270 wrapper (bin/s3270)

This runner was extended to provide more robust s3270 command mapping,
improved screen normalization, and clearer issue reporting.
"""

import argparse
import json
import random
import re
import shlex
import shutil
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple

from pure3270.p3270_client import P3270Client

# Basic fuzz settings (kept intentionally small for fast runs)
HOST = "127.0.0.1"  # Default to local mock server
PORT = 2324
FUZZ_SEED = 456
MAX_SEQUENCES = 5
MAX_COMMANDS_PER_SEQUENCE = 20
SCREEN_ROWS = 24
SCREEN_COLS = 80

# Simple command set (subset reused from existing fuzz script)
FUZZ_COMMANDS = [
    "Enter",
    "Tab",
    "BackTab",
    "Home",
    "BackSpace",
    "PF(1)",
    "PF(2)",
    "PF(3)",
    "Clear",
    "EraseEOF",
    "EraseInput",
    "Up",
    "Down",
    "Left",
    "Right",
    "SysReq",
    "Attn",
    "Test",
    "Reset",
]

TEXT_COMMANDS = [
    "String(login)",
    "String(password)",
    "String(test)",
    "String(1234)",
    "String(ABCDEFGHIJKLMNOPQRSTUVWXYZ)",
]

EDGE_CASE_COMMANDS = [
    "HexString(414243)",
    "HexString(00FF)",
    "MoveCursor(0,0)",
    "MoveCursor(23,79)",
    "Ascii(0,0,10)",
]


def parse_arguments():
    p = argparse.ArgumentParser(
        description="Differential fuzz: pure3270 vs s3270 (local bin/s3270)"
    )
    p.add_argument("--host", default=HOST)
    p.add_argument("--port", type=int, default=PORT)
    p.add_argument("--seed", type=int, default=FUZZ_SEED)
    p.add_argument("--max-sequences", type=int, default=MAX_SEQUENCES)
    p.add_argument("--max-commands", type=int, default=MAX_COMMANDS_PER_SEQUENCE)
    p.add_argument(
        "--no-s3270",
        action="store_true",
        help="Skip running s3270 (useful for smoke runs)",
    )
    p.add_argument(
        "--s3270-cmd",
        default=None,
        help="Command to run s3270 (overrides default repo wrapper). Example: 's3270'",
    )
    p.add_argument(
        "--per-command",
        action="store_true",
        help="Compare screens after each command (slower)",
    )
    return p.parse_args()


class S3270Runner:
    """Run sequences against bin/s3270 by feeding lines to its stdin."""

    def __init__(
        self, bin_cmd: Optional[List[str]] = None, timeout: float = 5.0
    ) -> None:
        # Prefer an explicit bin_cmd if provided.
        if bin_cmd:
            self.bin_cmd = bin_cmd
        else:
            # Prefer system 's3270' if available on PATH
            ssys = shutil.which("s3270")
            if ssys:
                self.bin_cmd = [ssys]
            else:
                # Fall back to the repo wrapper using the same Python interpreter
                import sys as _sys

                self.bin_cmd = [_sys.executable, "bin/s3270"]
        self.timeout = timeout

    @staticmethod
    def _map_command_for_s3270(cmd: str) -> str:
        """Map a sequence token like String(x) or PF(1) to s3270 stdin line.

        Preferred syntax: 'Command arg1 arg2 ...' (space separated).

        Rules:
        - String(text) => String <text> (preserves spaces)
        - HexString(hex) => HexString <hex>
        - PF(n), PA(n) => PF <n>, PA <n>
        - Key(name) => Key <name>
        - MoveCursor(r,c) => MoveCursor <r> <c>
        - Ascii(r,c,n) => Ascii <r> <c> <n>
        - Fallback: attempt sensible shlex-friendly split, otherwise raw token
        """
        token = cmd.strip()
        if not token:
            return token

        # If shape is NAME(args)
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\((.*)\)$", token)
        if m:
            name = m.group(1)
            args_str = m.group(2)
            # Special-case String to preserve content verbatim
            if name == "String":
                # if empty -> "String", else "String <content>"
                return "String " + args_str if args_str != "" else "String"
            if name == "HexString":
                return "HexString " + args_str if args_str != "" else "HexString"
            if name in ("PF", "PA", "Key"):
                # allow formats like PF(1) or PF(1, ) -> take first numeric token
                parts = (
                    re.split(r"\s*,\s*|\s+", args_str.strip())
                    if args_str.strip()
                    else []
                )
                return " ".join([name] + parts) if parts else name
            if name == "MoveCursor":
                parts = (
                    re.split(r"\s*,\s*|\s+", args_str.strip())
                    if args_str.strip()
                    else []
                )
                return " ".join([name] + parts) if parts else name
            if name == "Ascii":
                parts = re.split(r"\s*,\s*|\s+", args_str.strip())
                return " ".join([name] + parts)
            # Generic: split by comma if present, else by whitespace
            parts = (
                [p.strip() for p in args_str.split(",")]
                if "," in args_str
                else args_str.split()
            )
            parts = [p for p in parts if p != ""]
            return " ".join([name] + parts) if parts else name

        # If token already looks like "Command arg1 arg2" keep it
        try:
            # validate with shlex to ensure it's printable
            _ = shlex.split(token)
            return token
        except Exception:
            return token

    def run_sequence(
        self, sequence: List[str], host: str, port: int
    ) -> Tuple[str, str]:
        """Execute sequence against s3270 wrapper and return (stdout, stderr)."""
        # Build input script to feed to s3270: connect, commands, PrintText, Quit
        lines: List[str] = [f"Connect {host}:{port}"]
        for c in sequence:
            lines.append(self._map_command_for_s3270(c))
        # request a printout of screen text then exit
        lines.append("PrintText")
        lines.append("Quit")
        input_data = "\n".join(lines) + "\n"

        try:
            proc = subprocess.Popen(
                self.bin_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout, stderr = proc.communicate(input=input_data, timeout=self.timeout)
            return stdout or "", stderr or ""
        except FileNotFoundError:
            # If bin/s3270 is not present, return special marker in stderr
            return "", "s3270-not-found"
        except subprocess.TimeoutExpired:
            try:
                proc.kill()
            except Exception:
                pass
            return "", "timeout"
        except Exception as e:
            return "", str(e)


class DifferentialFuzzer:
    def __init__(
        self,
        host: str,
        port: int,
        seed: int,
        max_sequences: int,
        max_commands: int,
        run_s3270: bool = True,
        s3270_cmd: Optional[str] = None,
        per_command: bool = False,
    ) -> None:
        self.host = host
        self.port = port
        self.random = random.Random(seed)
        self.max_sequences = max_sequences
        self.max_commands = max_commands
        self.run_s3270 = run_s3270
        self.per_command = per_command

        bin_cmd = None
        if s3270_cmd:
            # allow passing a simple command string (like "s3270") or space-separated command
            bin_cmd = s3270_cmd.split()

        self.srunner = S3270Runner(bin_cmd=bin_cmd) if run_s3270 else None

        self.stats: Dict[str, int] = {
            "sequences_tested": 0,
            "differences": 0,
            "s3270_errors": 0,
            "p3270_errors": 0,
        }
        self.issues: List[Dict[str, Any]] = []

    def generate_sequence(self) -> List[str]:
        n = self.random.randint(1, self.max_commands)
        seq: List[str] = []
        for _ in range(n):
            r = self.random.random()
            if r < 0.25:
                seq.append(self.random.choice(TEXT_COMMANDS))
            elif r < 0.45:
                seq.append(self.random.choice(EDGE_CASE_COMMANDS))
            else:
                seq.append(self.random.choice(FUZZ_COMMANDS))
        return seq

    @staticmethod
    def _clean_line_for_compare(line: str) -> str:
        # Remove non-printable characters and normalize spaces
        cleaned = re.sub(r"[^\x20-\x7E]", " ", line)
        cleaned = re.sub(r"\s+$", "", cleaned)
        return cleaned

    @classmethod
    def normalize_screen(cls, screen: Optional[str]) -> str:
        """Normalize textual screen produced by P3270Client.getScreen() or s3270 PrintText output.

        Steps:
        - Guard for None
        - Split into lines, clean each line of non-printables
        - Pad/truncate each line to SCREEN_COLS
        - Use first SCREEN_ROWS lines (pad with empty lines as needed)
        - Return joined text for deterministic comparison
        """
        if not screen:
            lines: List[str] = []
        else:
            raw_lines = screen.splitlines()
            lines = [cls._clean_line_for_compare(l) for l in raw_lines]

        # Truncate or pad lines to SCREEN_COLS
        norm_lines: List[str] = []
        for i in range(min(len(lines), SCREEN_ROWS)):
            line = lines[i][:SCREEN_COLS].ljust(SCREEN_COLS)
            norm_lines.append(line)
        # Pad to SCREEN_ROWS
        while len(norm_lines) < SCREEN_ROWS:
            norm_lines.append(" " * SCREEN_COLS)
        return "\n".join(norm_lines)

    def run_single(self, sequence: List[str]) -> bool:
        """Run sequence on P3270Client, optionally on s3270, compare final screens."""
        self.stats["sequences_tested"] += 1
        seq_no = self.stats["sequences_tested"]
        p3270 = P3270Client(hostName=self.host, hostPort=self.port)
        try:
            p3270.connect()
        except Exception as e:
            self.stats["p3270_errors"] += 1
            self.issues.append(
                {
                    "sequence_number": seq_no,
                    "sequence": sequence,
                    "error": f"p3270 connect failed: {e}",
                }
            )
            return False

        try:
            p_initial_raw = p3270.getScreen()
        except Exception:
            p_initial_raw = ""
        p_initial = self.normalize_screen(p_initial_raw)

        # Execute sequence via P3270Client API (best-effort mapping).
        # If per-command comparison is enabled, after each command we capture
        # the current screen from p3270 and request a PrintText from s3270 for
        # the same prefix, then compare immediately.
        seq_so_far: List[str] = []
        for idx, cmd in enumerate(sequence):
            seq_so_far.append(cmd)
            try:
                if cmd.startswith("String("):
                    text = cmd[7:-1]
                    p3270.sendText(text)
                elif cmd == "Enter":
                    p3270.sendEnter()
                elif cmd.startswith("PF("):
                    num = int(cmd[3:-1])
                    p3270.sendPF(num)
                elif cmd.startswith("PA("):
                    num = int(cmd[3:-1])
                    p3270.sendPA(num)
                elif cmd == "Clear":
                    p3270.clearScreen()
                elif cmd == "Tab":
                    p3270.sendTab()
                elif cmd == "Home":
                    p3270.sendHome()
                elif cmd == "BackTab":
                    p3270.sendBackTab()
                elif cmd.startswith("HexString("):
                    # best-effort: send raw bytes via p3270._sendCommand if available
                    hexpart = cmd[10:-1]
                    try:
                        b = bytes.fromhex(hexpart) if hexpart else b""
                        # p3270._sendCommand may accept different signatures; attempt best-effort
                        try:
                            p3270._sendCommand("HexString", b)
                        except TypeError:
                            # fallback: send as raw text
                            try:
                                p3270._sendCommand(f"HexString {hexpart}")
                            except Exception:
                                pass
                    except Exception:
                        pass
                else:
                    # Fallback: attempt to send raw command if API exposes it
                    try:
                        p3270._sendCommand(cmd)
                    except Exception:
                        # ignore unknown mapping for now
                        pass

                # small pause to allow server to respond in real setups
                time.sleep(0.02)

                # Per-command comparison (optional)
                if self.per_command and self.srunner:
                    try:
                        p_snapshot_raw = p3270.getScreen()
                    except Exception:
                        p_snapshot_raw = ""
                    p_snapshot = self.normalize_screen(p_snapshot_raw)

                    s_stdout_step, s_stderr_step = self.srunner.run_sequence(
                        seq_so_far, self.host, self.port
                    )
                    if s_stderr_step in ("s3270-not-found", "timeout"):
                        # record but continue with sequence execution
                        self.stats["s3270_errors"] += 1
                        self.issues.append(
                            {
                                "sequence_number": seq_no,
                                "step": idx + 1,
                                "sequence": seq_so_far.copy(),
                                "issue": s_stderr_step,
                                "p_snapshot": p_snapshot[:1000],
                            }
                        )
                    else:
                        s_snapshot = self.normalize_screen(s_stdout_step)
                        if p_snapshot != s_snapshot:
                            # record difference at this step and stop executing further commands
                            self.stats["differences"] += 1
                            total_chars = SCREEN_ROWS * SCREEN_COLS
                            diffs = sum(
                                1 for a, b in zip(p_snapshot, s_snapshot) if a != b
                            )
                            diff_percent = (
                                100.0 * diffs / total_chars if total_chars else 0.0
                            )
                            self.issues.append(
                                {
                                    "sequence_number": seq_no,
                                    "step": idx + 1,
                                    "sequence_prefix": seq_so_far.copy(),
                                    "p_snapshot": p_snapshot,
                                    "s_snapshot": s_snapshot,
                                    "s_stdout_snippet": (s_stdout_step or "")[:2000],
                                    "s_stderr": s_stderr_step,
                                    "diff_chars": diffs,
                                    "diff_percent": diff_percent,
                                    "timestamp": time.time(),
                                }
                            )
                            # attempt to disconnect and exit early
                            try:
                                p3270.disconnect()
                            except Exception:
                                pass
                            return False

            except Exception as e:
                # capture but continue
                self.stats["p3270_errors"] += 1
                self.issues.append(
                    {
                        "sequence_number": seq_no,
                        "sequence": sequence,
                        "error": f"p3270 command '{cmd}' failed: {e}",
                    }
                )

        try:
            p_final_raw = p3270.getScreen()
        except Exception:
            p_final_raw = ""
        p_final = self.normalize_screen(p_final_raw)

        # Run s3270 if enabled
        s_stdout = ""
        s_stderr = ""
        if self.run_s3270 and self.srunner:
            s_stdout, s_stderr = self.srunner.run_sequence(
                sequence, self.host, self.port
            )

        # Interpret s3270 result
        if s_stderr == "s3270-not-found":
            # mark and skip comparison
            self.stats["s3270_errors"] += 1
            self.issues.append(
                {
                    "sequence_number": seq_no,
                    "sequence": sequence,
                    "issue": "s3270-not-found",
                    "p3270_screen": p_final[:1000],
                }
            )
            try:
                p3270.disconnect()
            except Exception:
                pass
            return False
        if s_stderr == "timeout":
            self.stats["s3270_errors"] += 1
            self.issues.append(
                {
                    "sequence_number": seq_no,
                    "sequence": sequence,
                    "issue": "s3270-timeout",
                    "p3270_screen": p_final[:1000],
                }
            )
            try:
                p3270.disconnect()
            except Exception:
                pass
            return False

        s_screen = self.normalize_screen(s_stdout)

        # Compare screens character-by-character and record diff summary
        if p_final != s_screen:
            self.stats["differences"] += 1
            # compute a simple diff metric
            total_chars = SCREEN_ROWS * SCREEN_COLS
            diffs = sum(1 for a, b in zip(p_final, s_screen) if a != b)
            diff_percent = 100.0 * diffs / total_chars if total_chars else 0.0
            self.issues.append(
                {
                    "sequence_number": seq_no,
                    "sequence": sequence,
                    "p3270_screen": p_final,
                    "s3270_screen": s_screen,
                    "s3270_stdout_snippet": (s_stdout or "")[:2000],
                    "s3270_stderr": s_stderr,
                    "diff_chars": diffs,
                    "diff_percent": diff_percent,
                    "timestamp": time.time(),
                }
            )
            try:
                p3270.disconnect()
            except Exception:
                pass
            return False

        try:
            p3270.disconnect()
        except Exception:
            pass
        return True

    def run(self) -> None:
        for _ in range(self.max_sequences):
            seq = self.generate_sequence()
            print(f"Sequence {_+1}/{self.max_sequences}: {seq}")
            ok = self.run_single(seq)
            print(" OK" if ok else " DIFF/ERROR")
        # summary
        print("\nSummary:")
        print(f"Sequences tested: {self.stats['sequences_tested']}")
        print(f"Differences found: {self.stats['differences']}")
        print(f"P3270 errors recorded: {self.stats['p3270_errors']}")
        print(f"S3270 errors recorded: {self.stats['s3270_errors']}")
        # Save issues if any
        if self.issues:
            import os

            os.makedirs("test_output", exist_ok=True)
            with open("test_output/diff_fuzz_issues.json", "w") as f:
                json.dump(
                    {"seed": FUZZ_SEED, "issues": self.issues}, f, indent=2, default=str
                )

    def write_report(self, out_dir: str = "test_output") -> None:
        """Write human-readable summary reports for found issues."""
        import os

        os.makedirs(out_dir, exist_ok=True)

        summary_path = os.path.join(out_dir, "diff_fuzz_summary.txt")
        with open(summary_path, "w") as s:
            s.write("Differential Fuzz Summary\n")
            s.write("=========================\n\n")
            s.write(f"Seed: {FUZZ_SEED}\n")
            s.write(f"Sequences tested: {self.stats['sequences_tested']}\n")
            s.write(f"Differences found: {self.stats['differences']}\n")
            s.write(f"P3270 errors recorded: {self.stats['p3270_errors']}\n")
            s.write(f"S3270 errors recorded: {self.stats['s3270_errors']}\n\n")

            if not self.issues:
                s.write("No issues recorded.\n")
            else:
                for i, issue in enumerate(self.issues, 1):
                    s.write(f"Issue #{i}\n")
                    s.write("-" * 40 + "\n")
                    s.write(f"Sequence number: {issue.get('sequence_number', 'n/a')}\n")
                    if "step" in issue:
                        s.write(f"Step: {issue['step']}\n")
                    s.write(
                        f"Sequence: {issue.get('sequence') or issue.get('sequence_prefix') or issue.get('sequence_prefix', [])}\n"
                    )
                    if "issue" in issue:
                        s.write(f"Issue: {issue['issue']}\n")
                    if "error" in issue:
                        s.write(f"Error: {issue['error']}\n")
                    if "diff_percent" in issue:
                        s.write(
                            f"Diff (% chars): {issue['diff_percent']:.2f}% ({issue['diff_chars']} chars)\n"
                        )
                    # write small screen snippets
                    if "p_snapshot" in issue:
                        s.write("P3270 snapshot (first 6 lines):\n")
                        for line in issue["p_snapshot"].splitlines()[:6]:
                            s.write("  " + line.rstrip() + "\n")
                    if "s_snapshot" in issue:
                        s.write("S3270 snapshot (first 6 lines):\n")
                        for line in issue["s_snapshot"].splitlines()[:6]:
                            s.write("  " + line.rstrip() + "\n")
                    if "p3270_screen" in issue:
                        s.write("P3270 final screen (first 6 lines):\n")
                        for line in issue["p3270_screen"].splitlines()[:6]:
                            s.write("  " + line.rstrip() + "\n")
                    if "s3270_screen" in issue:
                        s.write("S3270 final screen (first 6 lines):\n")
                        for line in issue["s3270_screen"].splitlines()[:6]:
                            s.write("  " + line.rstrip() + "\n")
                    s.write(f"Timestamp: {issue.get('timestamp', '')}\n\n")

        # Create a CSV summary with basic metrics
        csv_path = os.path.join(out_dir, "diff_fuzz_summary.csv")
        with open(csv_path, "w") as c:
            c.write("sequence_number,step,diff_percent,diff_chars,issue\n")
            for issue in self.issues:
                seqnum = issue.get("sequence_number", "")
                step = issue.get("step", "")
                diff_percent = issue.get("diff_percent", 0.0)
                diff_chars = issue.get("diff_chars", 0)
                isu = issue.get("issue", "").replace(",", ";")
                c.write(f"{seqnum},{step},{diff_percent},{diff_chars},{isu}\n")

        # JSON already saved; ensure it's present
        json_path = os.path.join(out_dir, "diff_fuzz_issues.json")
        with open(json_path, "w") as f:
            json.dump(
                {"seed": FUZZ_SEED, "issues": self.issues}, f, indent=2, default=str
            )


def main() -> int:
    args = parse_arguments()
    fuzzer = DifferentialFuzzer(
        host=args.host,
        port=args.port,
        seed=args.seed,
        max_sequences=args.max_sequences,
        max_commands=args.max_commands,
        run_s3270=not args.no_s3270,
        s3270_cmd=(args.s3270_cmd if args.s3270_cmd else None),
    )
    fuzzer.run()
    # Exit code: 0 if no differences, 1 otherwise
    return 0 if fuzzer.stats["differences"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
