#!/usr/bin/env python3
"""
Attribution Comment Generator for Pure3270

This tool helps contributors generate properly formatted attribution comments
for code that is ported from or inspired by third-party sources.

The tool ensures compliance with:
- THIRD_PARTY_NOTICES.md attribution requirements
- PORTING_GUIDELINES.md porting standards
- MIT license compatibility requirements

Usage:
    python tools/generate_attribution.py --type module --source "IBM s3270" --url "https://github.com/rhacker/x3270"
    python tools/generate_attribution.py --type function --source "ebcdic package" --function parse_ebcdic
    python tools/generate_attribution.py --interactive
"""

import argparse
import sys
import textwrap
from pathlib import Path
from typing import List, Optional

# Import our templates
from tools.attribution_templates import AttributionTemplates


class AttributionGenerator:
    """Interactive and command-line tool for generating attribution comments."""

    def __init__(self) -> None:
        """Initialize the attribution generator."""
        self.templates = AttributionTemplates()
        self.common_sources = {
            "s3270": {
                "name": "IBM s3270/x3270 Terminal Emulator",
                "url": "https://github.com/rhacker/x3270",
                "license": "BSD-3-Clause",
            },
            "ebcdic": {
                "name": "ebcdic Python Package",
                "url": "https://pypi.org/project/ebcdic/",
                "license": "MIT License",
            },
            "python": {
                "name": "Python Standard Library",
                "url": "https://docs.python.org/3/library/",
                "license": "Python Software Foundation License (PSFL)",
            },
        }

    def generate_module_attribution(self, args) -> str:
        """Generate module-level attribution comment."""
        return self.templates.module_attribution(
            source_name=args.source_name,
            source_url=args.source_url,
            license_name=args.license,
            description=args.description,
            compatibility_notes=args.compatibility,
            modification_notes=args.modifications,
            integration_points=args.integration_points,
            rfc_references=args.rfc_refs,
        )

    def generate_function_attribution(self, args) -> str:
        """Generate function-level attribution comment."""
        return self.templates.function_attribution(
            source_name=args.source_name,
            source_url=args.source_url,
            license_name=args.license,
            description=args.description,
            function_name=args.function_name,
            compatibility_notes=args.compatibility,
            rfc_references=args.rfc_refs,
        )

    def generate_class_attribution(self, args) -> str:
        """Generate class-level attribution comment."""
        return self.templates.class_attribution(
            source_name=args.source_name,
            source_url=args.source_url,
            license_name=args.license,
            description=args.description,
            class_name=args.class_name,
            compatibility_notes=args.compatibility,
            integration_layer=args.integration_layer,
        )

    def generate_protocol_attribution(self, args) -> str:
        """Generate protocol implementation attribution comment."""
        return self.templates.protocol_attribution(
            source_name=args.source_name,
            source_url=args.source_url,
            license_name=args.license,
            protocol_name=args.protocol_name,
            rfc_numbers=args.rfc_numbers,
            description=args.description,
            compatibility_notes=args.compatibility,
        )

    def generate_s3270_attribution(self, args) -> str:
        """Generate s3270 compatibility attribution comment."""
        return self.templates.s3270_compatibility_attribution(
            component_type=args.component_type,
            s3270_commands=args.s3270_commands,
            description=args.description,
            integration_layer=args.integration_layer,
        )

    def generate_ebcdic_attribution(self, args) -> str:
        """Generate EBCDIC codec attribution comment."""
        return self.templates.ebcdic_attribution(
            codec_name=args.codec_name,
            description=args.description,
            fallback_behavior=args.fallback_behavior,
        )

    def generate_third_party_notice(self, args) -> str:
        """Generate THIRD_PARTY_NOTICES.md entry."""
        return self.templates.generate_third_party_notice(
            source_name=args.source_name,
            source_url=args.source_url,
            license_name=args.license,
            license_text=args.license_text,
            description=args.description,
            ported_components=args.components,
            integration_layer=args.integration_layer,
            modifications=args.modifications,
            compatibility=args.notice_compatibility,
            optional_dependency=args.optional,
        )

    def interactive_mode(self):
        """Run interactive mode to guide users through attribution creation."""
        print("Pure3270 Attribution Comment Generator")
        print("=" * 40)
        print()
        print("This tool will help you create properly formatted attribution comments")
        print("for code that is ported from or inspired by third-party sources.")
        print()

        # Ask for attribution type
        print("What type of attribution do you need?")
        print("1. Module-level (entire file)")
        print("2. Function/method")
        print("3. Class")
        print("4. Protocol implementation")
        print("5. s3270 compatibility")
        print("6. EBCDIC codec")
        print("7. THIRD_PARTY_NOTICES.md entry")
        print()

        while True:
            try:
                choice = input("Enter your choice (1-7): ").strip()
                if choice in ["1", "2", "3", "4", "5", "6", "7"]:
                    break
                print("Please enter a number between 1 and 7.")
            except KeyboardInterrupt:
                print("\nExiting...")
                sys.exit(0)

        # Common questions
        print()
        print("Source Information:")
        print("-" * 20)

        # Check if it's a common source
        source_name = input(
            "Source project name (or 'list' for common sources): "
        ).strip()
        if source_name.lower() == "list":
            print("\nCommon sources:")
            for key, info in self.common_sources.items():
                print(f"- {key}: {info['name']}")
            print()
            source_name = input("Source project name: ").strip()

        # Use common source if available
        if source_name.lower() in self.common_sources:
            source_info = self.common_sources[source_name.lower()]
            source_name = source_info["name"]
            source_url = source_info["url"]
            license_name = source_info["license"]
            print(f"Using common source: {source_name}")
        else:
            source_url = input("Source URL: ").strip()
            license_name = input("License name: ").strip()

        description = input("Description of what was ported/adapted: ").strip()

        # Generate based on type
        if choice == "1":  # Module
            compatibility = input("Compatibility notes (optional): ").strip()
            modifications = input("Modification notes (optional): ").strip()
            integration_input = input(
                "Integration points (comma-separated, optional): "
            ).strip()
            integration_points = (
                [p.strip() for p in integration_input.split(",") if p.strip()]
                if integration_input
                else None
            )
            rfc_input = input("RFC references (comma-separated, optional): ").strip()
            rfc_refs = (
                [r.strip() for r in rfc_input.split(",") if r.strip()]
                if rfc_input
                else None
            )

            result = self.templates.module_attribution(
                source_name=source_name,
                source_url=source_url,
                license_name=license_name,
                description=description,
                compatibility_notes=compatibility or None,
                modification_notes=modifications or None,
                integration_points=integration_points,
                rfc_references=rfc_refs,
            )

        elif choice == "2":  # Function
            function_name = input("Function/method name: ").strip()
            compatibility = input("Compatibility notes (optional): ").strip()
            rfc_input = input("RFC references (comma-separated, optional): ").strip()
            rfc_refs = (
                [r.strip() for r in rfc_input.split(",") if r.strip()]
                if rfc_input
                else None
            )

            result = self.templates.function_attribution(
                source_name=source_name,
                source_url=source_url,
                license_name=license_name,
                description=description,
                function_name=function_name,
                compatibility_notes=compatibility or None,
                rfc_references=rfc_refs,
            )

        elif choice == "3":  # Class
            class_name = input("Class name: ").strip()
            compatibility = input("Compatibility notes (optional): ").strip()
            integration_layer = (
                input(
                    "Integration layer (Protocol/Emulation/Session, optional): "
                ).strip()
                or None
            )

            result = self.templates.class_attribution(
                source_name=source_name,
                source_url=source_url,
                license_name=license_name,
                description=description,
                class_name=class_name,
                compatibility_notes=compatibility or None,
                integration_layer=integration_layer,
            )

        elif choice == "4":  # Protocol
            protocol_name = input("Protocol name (e.g., TN3270, TN3270E): ").strip()
            rfc_input = input("RFC numbers (comma-separated): ").strip()
            rfc_numbers = [r.strip() for r in rfc_input.split(",") if r.strip()]
            compatibility = input("Compatibility notes (optional): ").strip()

            result = self.templates.protocol_attribution(
                source_name=source_name,
                source_url=source_url,
                license_name=license_name,
                protocol_name=protocol_name,
                rfc_numbers=rfc_numbers,
                description=description,
                compatibility_notes=compatibility or None,
            )

        elif choice == "5":  # s3270
            component_type = input(
                "Component type (e.g., Protocol Handler, Command Implementation): "
            ).strip()
            commands_input = input("s3270 commands (comma-separated): ").strip()
            s3270_commands = [c.strip() for c in commands_input.split(",") if c.strip()]
            integration_layer = (
                input("Integration layer (optional): ").strip() or "Protocol"
            )

            result = self.templates.s3270_compatibility_attribution(
                component_type=component_type,
                s3270_commands=s3270_commands,
                description=description,
                integration_layer=integration_layer,
            )

        elif choice == "6":  # EBCDIC
            codec_name = input("Codec name: ").strip()
            fallback = (
                input("Fallback behavior (optional): ").strip()
                or "Falls back to standard library CP037 codec"
            )

            result = self.templates.ebcdic_attribution(
                codec_name=codec_name,
                description=description,
                fallback_behavior=fallback,
            )

        elif choice == "7":  # Third-party notice
            license_text = input("Complete license text (paste here): ").strip()
            components_input = input("Ported components (comma-separated): ").strip()
            ported_components = [
                c.strip() for c in components_input.split(",") if c.strip()
            ]
            integration_layer = input("Integration layer: ").strip()
            modifications = input("Modifications made: ").strip()
            compatibility = input("Compatibility statement: ").strip()
            optional_input = input("Optional dependency? (y/n): ").strip().lower()
            optional = optional_input == "y"

            result = self.templates.generate_third_party_notice(
                source_name=source_name,
                source_url=source_url,
                license_name=license_name,
                license_text=license_text,
                description=description,
                ported_components=ported_components,
                integration_layer=integration_layer,
                modifications=modifications,
                compatibility=compatibility,
                optional_dependency=optional,
            )

        # Output the result
        print()
        print("Generated Attribution Comment:")
        print("=" * 40)
        print(result)
        print("=" * 40)
        print()

        # Ask if user wants to save to file
        save_file = input("Save to file? (y/n): ").strip().lower()
        if save_file == "y":
            filename = input("Filename (or press Enter for default): ").strip()
            if not filename:
                if choice == "1":
                    filename = "module_attribution.txt"
                elif choice == "7":
                    filename = "third_party_notice.md"
                else:
                    filename = "attribution_comment.txt"

            try:
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(result)
                print(f"Saved to {filename}")
            except Exception as e:
                print(f"Error saving file: {e}")

        return result


def main():
    """Main entry point for the attribution generator."""
    parser = argparse.ArgumentParser(
        description="Generate attribution comments for Pure3270",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --interactive
  %(prog)s --type module --source "IBM s3270" --url "https://github.com/rhacker/x3270" --license "BSD-3-Clause"
  %(prog)s --type function --source "ebcdic package" --function parse_ebcdic --description "EBCDIC parsing logic"
  %(prog)s --type protocol --source "s3270" --protocol TN3270 --rfcs 1576,2355
  %(prog)s --type s3270 --component "Command Implementation" --commands "String,Asc,Ebcdic"
        """,
    )

    parser.add_argument(
        "--interactive", "-i", action="store_true", help="Run in interactive mode"
    )

    parser.add_argument(
        "--type",
        "-t",
        choices=[
            "module",
            "function",
            "class",
            "protocol",
            "s3270",
            "ebcdic",
            "notice",
        ],
        help="Type of attribution to generate",
    )

    # Common arguments
    parser.add_argument("--source-name", "-s", help="Source project name")
    parser.add_argument("--source-url", "-u", help="Source project URL")
    parser.add_argument("--license", "-l", help="License name")
    parser.add_argument(
        "--description", "-d", help="Description of what was ported/adapted"
    )

    # Module-specific arguments
    parser.add_argument("--compatibility", "-c", help="Compatibility notes")
    parser.add_argument("--modifications", "-m", help="Modification notes")
    parser.add_argument(
        "--integration-points", nargs="*", help="Integration points in Pure3270"
    )
    parser.add_argument("--rfc-refs", nargs="*", help="RFC references")

    # Function-specific arguments
    parser.add_argument("--function-name", "-f", help="Function/method name")

    # Class-specific arguments
    parser.add_argument("--class-name", help="Class name")
    parser.add_argument(
        "--integration-layer", help="Integration layer (Protocol/Emulation/Session)"
    )

    # Protocol-specific arguments
    parser.add_argument(
        "--protocol-name", "-p", help="Protocol name (e.g., TN3270, TN3270E)"
    )
    parser.add_argument("--rfc-numbers", nargs="*", help="RFC numbers this implements")

    # s3270-specific arguments
    parser.add_argument("--component-type", help="Component type")
    parser.add_argument(
        "--s3270-commands", nargs="*", help="s3270 commands this implements"
    )

    # EBCDIC-specific arguments
    parser.add_argument("--codec-name", help="Codec name")
    parser.add_argument("--fallback-behavior", help="Fallback behavior description")

    # Third-party notice arguments
    parser.add_argument("--license-text", help="Complete license text")
    parser.add_argument("--components", nargs="*", help="Ported components")
    parser.add_argument("--modifications", help="Modifications made")
    parser.add_argument("--compatibility", help="Compatibility statement")
    parser.add_argument(
        "--optional", action="store_true", help="Mark as optional dependency"
    )

    args = parser.parse_args()

    generator = AttributionGenerator()

    if args.interactive:
        generator.interactive_mode()
    elif args.type:
        # Validate required arguments
        if (
            not args.source_name
            or not args.source_url
            or not args.license
            or not args.description
        ):
            print(
                "Error: Missing required arguments. Use --interactive for guided mode."
            )
            sys.exit(1)

        # Generate the appropriate attribution
        if args.type == "module":
            result = generator.generate_module_attribution(args)
        elif args.type == "function":
            if not args.function_name:
                print("Error: --function-name required for function attribution")
                sys.exit(1)
            result = generator.generate_function_attribution(args)
        elif args.type == "class":
            if not args.class_name:
                print("Error: --class-name required for class attribution")
                sys.exit(1)
            result = generator.generate_class_attribution(args)
        elif args.type == "protocol":
            if not args.protocol_name or not args.rfc_numbers:
                print(
                    "Error: --protocol-name and --rfc-numbers required for protocol attribution"
                )
                sys.exit(1)
            result = generator.generate_protocol_attribution(args)
        elif args.type == "s3270":
            if not args.component_type or not args.s3270_commands:
                print(
                    "Error: --component-type and --s3270-commands required for s3270 attribution"
                )
                sys.exit(1)
            result = generator.generate_s3270_attribution(args)
        elif args.type == "ebcdic":
            if not args.codec_name:
                print("Error: --codec-name required for EBCDIC attribution")
                sys.exit(1)
            result = generator.generate_ebcdic_attribution(args)
        elif args.type == "notice":
            if not args.license_text or not args.components:
                print(
                    "Error: --license-text and --components required for third-party notice"
                )
                sys.exit(1)
            result = generator.generate_third_party_notice(args)

        print(result)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
