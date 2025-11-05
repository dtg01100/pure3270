#!/usr/bin/env python3
"""
State Machine Visualizer for Pure3270

Visualizes TN3270 protocol state machines for debugging and analysis.
Supports both text-based and graphical (if graphviz available) representations.

Usage:
    python state_machine_visualizer.py --handler-states
    python state_machine_visualizer.py --sna-states
    python state_machine_visualizer.py --from-session session.json
    python state_machine_visualizer.py --from-trace trace.json --output diagram.png
"""

import argparse
import json
import sys
from typing import Dict, List, Optional

try:
    from graphviz import Digraph

    GRAPHVIZ_AVAILABLE = True
except ImportError:
    GRAPHVIZ_AVAILABLE = False

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class StateMachineVisualizer:
    """Visualizes TN3270 state machines."""

    def __init__(self):
        self.console = Console() if RICH_AVAILABLE else None

    # TN3270 Handler State Machine Definition
    HANDLER_STATES = {
        "DISCONNECTED": {
            "description": "Not connected to host",
            "color": "gray",
            "transitions": ["CONNECTING", "CLOSING", "CONNECTED"],
        },
        "CONNECTING": {
            "description": "Establishing connection",
            "color": "yellow",
            "transitions": ["NEGOTIATING", "ERROR", "DISCONNECTED"],
        },
        "NEGOTIATING": {
            "description": "Negotiating TN3270 parameters",
            "color": "blue",
            "transitions": ["CONNECTED", "ASCII_MODE", "TN3270_MODE", "ERROR"],
        },
        "CONNECTED": {
            "description": "Connected, mode not yet determined",
            "color": "green",
            "transitions": ["TN3270_MODE", "ASCII_MODE", "ERROR", "CLOSING"],
        },
        "ASCII_MODE": {
            "description": "Connected in ASCII/text mode",
            "color": "cyan",
            "transitions": ["CONNECTED", "ERROR", "CLOSING"],
        },
        "TN3270_MODE": {
            "description": "Connected in TN3270 structured field mode",
            "color": "purple",
            "transitions": ["CONNECTED", "ERROR", "CLOSING"],
        },
        "ERROR": {
            "description": "Error state, connection failed",
            "color": "red",
            "transitions": ["RECOVERING", "DISCONNECTED", "CLOSING"],
        },
        "RECOVERING": {
            "description": "Attempting to recover from error",
            "color": "orange",
            "transitions": ["CONNECTED", "ERROR", "DISCONNECTED"],
        },
        "CLOSING": {
            "description": "Closing connection",
            "color": "brown",
            "transitions": ["DISCONNECTED", "ERROR"],
        },
    }

    # SNA Session State Machine Definition
    SNA_STATES = {
        "NORMAL": {
            "description": "Normal SNA session operation",
            "color": "green",
            "transitions": ["ERROR", "SESSION_DOWN", "LU_BUSY"],
        },
        "ERROR": {
            "description": "SNA session error occurred",
            "color": "red",
            "transitions": ["PENDING_RECOVERY", "SESSION_DOWN"],
        },
        "PENDING_RECOVERY": {
            "description": "Waiting to attempt recovery",
            "color": "yellow",
            "transitions": ["NORMAL", "ERROR", "SESSION_DOWN"],
        },
        "SESSION_DOWN": {
            "description": "SNA session is down",
            "color": "gray",
            "transitions": ["NORMAL", "ERROR"],
        },
        "LU_BUSY": {
            "description": "Logical unit is busy",
            "color": "orange",
            "transitions": ["NORMAL", "ERROR"],
        },
        "INVALID_SEQUENCE": {
            "description": "Invalid sequence number received",
            "color": "red",
            "transitions": ["ERROR", "SESSION_DOWN"],
        },
        "STATE_ERROR": {
            "description": "Internal state machine error",
            "color": "red",
            "transitions": ["ERROR", "SESSION_DOWN"],
        },
    }

    def visualize_handler_states(self, output_file: Optional[str] = None) -> None:
        """Visualize the TN3270 handler state machine."""
        self._visualize_state_machine(
            "TN3270 Handler State Machine", self.HANDLER_STATES, output_file
        )

    def visualize_sna_states(self, output_file: Optional[str] = None) -> None:
        """Visualize the SNA session state machine."""
        self._visualize_state_machine(
            "SNA Session State Machine", self.SNA_STATES, output_file
        )

    def visualize_from_session_data(
        self, session_data: Dict, output_file: Optional[str] = None
    ) -> None:
        """Visualize state machine from session data."""
        if "current_state" in session_data:
            current_state = session_data["current_state"]
            state_history = session_data.get("state_history", [])
            transition_counts = session_data.get("transition_counts", {})

            title = f"TN3270 Handler State Machine (Current: {current_state})"
            self._visualize_state_machine_with_data(
                title,
                self.HANDLER_STATES,
                current_state,
                state_history,
                transition_counts,
                output_file,
            )
        else:
            print("No state information found in session data")

    def visualize_from_trace(
        self, trace_file: str, output_file: Optional[str] = None
    ) -> None:
        """Visualize state transitions from trace file."""
        with open(trace_file, "r") as f:
            trace_data = json.load(f)

        # Extract state transitions from trace
        state_transitions = []
        current_state = None

        # Look for state change events in the trace
        if "events" in trace_data:
            for event in trace_data["events"]:
                if "state" in event or "current_state" in event:
                    new_state = event.get("state") or event.get("current_state")
                    if new_state != current_state:
                        state_transitions.append(
                            {
                                "from": current_state,
                                "to": new_state,
                                "timestamp": event.get("timestamp"),
                                "reason": event.get("reason", "unknown"),
                            }
                        )
                        current_state = new_state

        if state_transitions:
            self._visualize_state_transitions(
                "State Transitions from Trace",
                self.HANDLER_STATES,
                state_transitions,
                output_file,
            )
        else:
            print("No state transitions found in trace")

    def _visualize_state_machine(
        self, title: str, states: Dict, output_file: Optional[str] = None
    ) -> None:
        """Generic state machine visualization."""
        if output_file and GRAPHVIZ_AVAILABLE:
            self._create_graphviz_diagram(title, states, output_file)
        else:
            self._create_text_diagram(title, states)

    def _visualize_state_machine_with_data(
        self,
        title: str,
        states: Dict,
        current_state: str,
        state_history: List,
        transition_counts: Dict,
        output_file: Optional[str] = None,
    ) -> None:
        """Visualize state machine with current state and history."""
        if output_file and GRAPHVIZ_AVAILABLE:
            self._create_graphviz_diagram_with_data(
                title,
                states,
                current_state,
                state_history,
                transition_counts,
                output_file,
            )
        else:
            self._create_text_diagram_with_data(
                title, states, current_state, state_history, transition_counts
            )

    def _visualize_state_transitions(
        self,
        title: str,
        states: Dict,
        transitions: List[Dict],
        output_file: Optional[str] = None,
    ) -> None:
        """Visualize state transitions over time."""
        if output_file and GRAPHVIZ_AVAILABLE:
            self._create_transition_graphviz_diagram(
                title, states, transitions, output_file
            )
        else:
            self._create_transition_text_diagram(title, states, transitions)

    def _create_text_diagram(self, title: str, states: Dict) -> None:
        """Create a text-based state machine diagram."""
        if self.console:
            table = Table(title=title, show_header=True)
            table.add_column("State", style="bold")
            table.add_column("Description")
            table.add_column("Transitions")

            for state_name, state_info in states.items():
                transitions = ", ".join(state_info["transitions"])
                table.add_row(state_name, state_info["description"], transitions)

            self.console.print(table)
        else:
            print(f"=== {title} ===")
            for state_name, state_info in states.items():
                transitions = ", ".join(state_info["transitions"])
                print(f"{state_name}: {state_info['description']}")
                print(f"  -> {transitions}")
                print()

    def _create_text_diagram_with_data(
        self,
        title: str,
        states: Dict,
        current_state: str,
        state_history: List,
        transition_counts: Dict,
    ) -> None:
        """Create text diagram with current state and statistics."""
        if self.console:
            # Current state panel
            current_panel = Panel(
                f"[bold green]{current_state}[/bold green]\n"
                f"{states[current_state]['description']}",
                title="Current State",
                border_style="green",
            )
            self.console.print(current_panel)
            print()

            # State history table
            if state_history:
                history_table = Table(
                    title="Recent State Transitions", show_header=True
                )
                history_table.add_column("From", style="dim")
                history_table.add_column("To", style="bold")
                history_table.add_column("Timestamp")
                history_table.add_column("Reason")

                for transition in state_history[-10:]:  # Last 10 transitions
                    from_state, timestamp, reason = transition
                    history_table.add_row(
                        from_state or "None",
                        current_state if from_state else transition[0],
                        f"{timestamp:.3f}",
                        reason,
                    )

                self.console.print(history_table)
                print()

            # Transition counts
            if transition_counts:
                counts_table = Table(title="State Transition Counts", show_header=True)
                counts_table.add_column("State", style="bold")
                counts_table.add_column("Count", justify="right")

                for state, count in sorted(transition_counts.items()):
                    counts_table.add_row(state, str(count))

                self.console.print(counts_table)

        else:
            print(f"=== {title} ===")
            print(f"Current State: {current_state}")
            print(f"Description: {states[current_state]['description']}")
            print()

            if state_history:
                print("Recent Transitions:")
                for transition in state_history[-5:]:
                    from_state, timestamp, reason = transition
                    print(
                        f"  {from_state or 'None'} -> {current_state} ({timestamp:.3f}s) - {reason}"
                    )
                print()

            if transition_counts:
                print("Transition Counts:")
                for state, count in sorted(transition_counts.items()):
                    print(f"  {state}: {count}")

    def _create_transition_text_diagram(
        self, title: str, states: Dict, transitions: List[Dict]
    ) -> None:
        """Create text diagram showing state transitions over time."""
        if self.console:
            table = Table(title=title, show_header=True)
            table.add_column("Time", style="dim")
            table.add_column("Transition", style="bold")
            table.add_column("Reason")

            for transition in transitions:
                from_state = transition.get("from") or "Start"
                to_state = transition["to"]
                timestamp = transition.get("timestamp", 0)
                reason = transition.get("reason", "unknown")

                table.add_row(f"{timestamp:.3f}", f"{from_state} → {to_state}", reason)

            self.console.print(table)
        else:
            print(f"=== {title} ===")
            for transition in transitions:
                from_state = transition.get("from") or "Start"
                to_state = transition["to"]
                timestamp = transition.get("timestamp", 0)
                reason = transition.get("reason", "unknown")
                print(f"{timestamp:.3f}s: {from_state} -> {to_state} ({reason})")

    def _create_graphviz_diagram(
        self, title: str, states: Dict, output_file: str
    ) -> None:
        """Create GraphViz diagram of state machine."""
        dot = Digraph(comment=title, format="png")
        dot.attr(label=title, fontsize="20")

        # Add nodes
        for state_name, state_info in states.items():
            color = state_info["color"]
            dot.node(
                state_name,
                f"{state_name}\n{state_info['description']}",
                fillcolor=color,
                style="filled",
            )

        # Add edges
        for state_name, state_info in states.items():
            for transition in state_info["transitions"]:
                dot.edge(state_name, transition)

        # Save diagram
        dot.render(output_file.replace(".png", ""), cleanup=True)
        print(f"Diagram saved to {output_file}")

    def _create_graphviz_diagram_with_data(
        self,
        title: str,
        states: Dict,
        current_state: str,
        state_history: List,
        transition_counts: Dict,
        output_file: str,
    ) -> None:
        """Create GraphViz diagram with current state highlighted."""
        dot = Digraph(comment=title, format="png")
        dot.attr(label=title, fontsize="20")

        # Add nodes with transition counts
        for state_name, state_info in states.items():
            color = state_info["color"]
            count = transition_counts.get(state_name, 0)

            if state_name == current_state:
                # Highlight current state
                label = f"{state_name}\n{state_info['description']}\n[count: {count}]"
                dot.node(
                    state_name,
                    label,
                    fillcolor=color,
                    style="filled,bold",
                    color="black",
                    penwidth="3",
                )
            else:
                label = f"{state_name}\n{state_info['description']}\n[count: {count}]"
                dot.node(state_name, label, fillcolor=color, style="filled")

        # Add edges
        for state_name, state_info in states.items():
            for transition in state_info["transitions"]:
                dot.edge(state_name, transition)

        # Save diagram
        dot.render(output_file.replace(".png", ""), cleanup=True)
        print(f"Diagram saved to {output_file}")

    def _create_transition_graphviz_diagram(
        self, title: str, states: Dict, transitions: List[Dict], output_file: str
    ) -> None:
        """Create GraphViz diagram showing transition path."""
        dot = Digraph(comment=title, format="png")
        dot.attr(label=title, fontsize="20")

        # Add all states
        for state_name, state_info in states.items():
            color = state_info["color"]
            dot.node(
                state_name,
                f"{state_name}\n{state_info['description']}",
                fillcolor=color,
                style="filled",
            )

        # Add transition edges with timing
        for i, transition in enumerate(transitions):
            from_state = transition.get("from")
            to_state = transition["to"]
            timestamp = transition.get("timestamp", 0)
            reason = transition.get("reason", "unknown")

            if from_state:
                label = f"{i+1}. {timestamp:.3f}s\n{reason}"
                dot.edge(from_state, to_state, label=label, color="red", penwidth="2")

        # Save diagram
        dot.render(output_file.replace(".png", ""), cleanup=True)
        print(f"Transition diagram saved to {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="State Machine Visualizer for Pure3270"
    )
    parser.add_argument(
        "--handler-states",
        action="store_true",
        help="Visualize TN3270 handler state machine",
    )
    parser.add_argument(
        "--sna-states", action="store_true", help="Visualize SNA session state machine"
    )
    parser.add_argument("--from-session", help="Visualize from session JSON file")
    parser.add_argument(
        "--from-trace", help="Visualize state transitions from trace JSON file"
    )
    parser.add_argument(
        "--output", help="Output file for graphical diagram (requires graphviz)"
    )

    args = parser.parse_args()

    visualizer = StateMachineVisualizer()

    if args.handler_states:
        visualizer.visualize_handler_states(args.output)
    elif args.sna_states:
        visualizer.visualize_sna_states(args.output)
    elif args.from_session:
        with open(args.from_session, "r") as f:
            session_data = json.load(f)
        visualizer.visualize_from_session_data(session_data, args.output)
    elif args.from_trace:
        visualizer.visualize_from_trace(args.from_trace, args.output)
    else:
        print(
            "Please specify one of: --handler-states, --sna-states, --from-session, --from-trace"
        )
        print("\nAvailable state machines:")
        print("  TN3270 Handler: Connection and protocol negotiation states")
        print("  SNA Session: SNA protocol session states")
        sys.exit(1)


if __name__ == "__main__":
    main()
