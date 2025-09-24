#!/usr/bin/env python3
"""
Attribution Comment Templates for Pure3270

This module provides standardized templates for attribution comments in code files.
These templates ensure consistent attribution formatting across the project and
help contributors properly document third-party code, inspiration, and compatibility.

Usage:
    from tools.attribution_templates import AttributionTemplates

    templates = AttributionTemplates()

    # Generate module-level attribution
    module_comment = templates.module_attribution(
        source_name="IBM s3270/x3270",
        source_url="https://github.com/rhacker/x3270",
        license_name="BSD-3-Clause",
        description="TN3270 protocol implementation based on s3270",
        compatibility_notes="Compatible with s3270 command interface"
    )

Templates are designed to work with:
- THIRD_PARTY_NOTICES.md for comprehensive attribution documentation
- PORTING_GUIDELINES.md for porting requirements
- MIT license compatibility requirements
"""

import textwrap
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class AttributionInfo:
    """Container for attribution information."""

    source_name: str
    source_url: str
    license_name: str
    description: str
    compatibility_notes: Optional[str] = None
    modification_notes: Optional[str] = None
    integration_points: Optional[List[str]] = None
    rfc_references: Optional[List[str]] = None


class AttributionTemplates:
    """
    Provides standardized templates for attribution comments in Pure3270 code.

    All templates follow the attribution requirements specified in:
    - THIRD_PARTY_NOTICES.md
    - PORTING_GUIDELINES.md
    """

    def __init__(self) -> None:
        """Initialize the attribution templates system."""
        self.current_year = datetime.now().year

    def _format_docstring(self, content: str, max_line_length: int = 88) -> str:
        """Format content as a properly indented docstring."""
        wrapped = textwrap.wrap(content, width=max_line_length - 4)
        if not wrapped:
            return '    """' + content + '"""'

        formatted_lines = ['    """' + wrapped[0]]
        for line in wrapped[1:]:
            formatted_lines.append("    " + line)
        formatted_lines.append('    """')
        return "\n".join(formatted_lines)

    def _format_license_header(
        self, license_name: str, copyright_info: str = ""
    ) -> str:
        """Format license header information."""
        header = f"    Licensed under {license_name}"
        if copyright_info:
            header += f"\n    {copyright_info}"
        return header

    def module_attribution(
        self,
        source_name: str,
        source_url: str,
        license_name: str,
        description: str,
        compatibility_notes: Optional[str] = None,
        modification_notes: Optional[str] = None,
        integration_points: Optional[List[str]] = None,
        rfc_references: Optional[List[str]] = None,
        copyright_info: str = "",
    ) -> str:
        """
        Generate module-level attribution comment for entire files.

        Args:
            source_name: Name of the original source project
            source_url: URL to the original project
            license_name: Name of the license (e.g., "BSD-3-Clause")
            description: Description of what was ported/adapted
            compatibility_notes: Notes about compatibility with original
            modification_notes: Description of modifications made
            integration_points: List of integration points in Pure3270
            rfc_references: List of RFC references if applicable
            copyright_info: Copyright information if different from default

        Returns:
            Formatted module-level attribution comment
        """
        info = AttributionInfo(
            source_name=source_name,
            source_url=source_url,
            license_name=license_name,
            description=description,
            compatibility_notes=compatibility_notes,
            modification_notes=modification_notes,
            integration_points=integration_points or [],
            rfc_references=rfc_references or [],
        )

        sections = []

        # Header section
        sections.append("ATTRIBUTION NOTICE")
        sections.append("=" * 50)
        sections.append(
            f"This module contains code ported from or inspired by: {info.source_name}"
        )
        sections.append(f"Source: {info.source_url}")
        sections.append(self._format_license_header(info.license_name, copyright_info))

        # Description section
        sections.append("")
        sections.append("DESCRIPTION")
        sections.append("-" * 20)
        sections.append(info.description)

        # Compatibility section
        if info.compatibility_notes:
            sections.append("")
            sections.append("COMPATIBILITY")
            sections.append("-" * 20)
            sections.append(info.compatibility_notes)

        # Modifications section
        if info.modification_notes:
            sections.append("")
            sections.append("MODIFICATIONS")
            sections.append("-" * 20)
            sections.append(info.modification_notes)

        # Integration points
        if info.integration_points:
            sections.append("")
            sections.append("INTEGRATION POINTS")
            sections.append("-" * 20)
            for point in info.integration_points:
                sections.append(f"- {point}")

        # RFC references
        if info.rfc_references:
            sections.append("")
            sections.append("RFC REFERENCES")
            sections.append("-" * 20)
            for rfc in info.rfc_references:
                sections.append(f"- {rfc}")

        # Footer
        sections.append("")
        sections.append("ATTRIBUTION REQUIREMENTS")
        sections.append("-" * 30)
        sections.append(
            "This attribution must be maintained when this code is modified or"
        )
        sections.append(
            "redistributed. See THIRD_PARTY_NOTICES.md for complete license text."
        )
        sections.append(f'Last updated: {datetime.now().strftime("%Y-%m-%d")}')

        return "\n".join(sections)

    def function_attribution(
        self,
        source_name: str,
        source_url: str,
        license_name: str,
        description: str,
        function_name: str,
        compatibility_notes: Optional[str] = None,
        rfc_references: Optional[List[str]] = None,
    ) -> str:
        """
        Generate function-level attribution comment.

        Args:
            source_name: Name of the original source project
            source_url: URL to the original project
            license_name: Name of the license
            description: Description of the function's origin
            function_name: Name of the function being attributed
            compatibility_notes: Notes about compatibility
            rfc_references: List of RFC references if applicable

        Returns:
            Formatted function-level attribution comment
        """
        content = f"""Ported from {source_name} ({source_url})

        {description}

        Licensed under {license_name}

        Compatibility: {compatibility_notes or 'Maintains compatibility with original implementation'}
        """

        if rfc_references:
            content += "\n        RFC References:\n"
            for rfc in rfc_references:
                content += f"        - {rfc}\n"

        return self._format_docstring(content.strip())

    def class_attribution(
        self,
        source_name: str,
        source_url: str,
        license_name: str,
        description: str,
        class_name: str,
        compatibility_notes: Optional[str] = None,
        integration_layer: Optional[str] = None,
    ) -> str:
        """
        Generate class-level attribution comment.

        Args:
            source_name: Name of the original source project
            source_url: URL to the original project
            license_name: Name of the license
            description: Description of the class's origin
            class_name: Name of the class being attributed
            compatibility_notes: Notes about compatibility
            integration_layer: Which layer this integrates into (Protocol/Emulation/Session)

        Returns:
            Formatted class-level attribution comment
        """
        content = f"""Ported from {source_name} ({source_url})

        {description}

        Integration Layer: {integration_layer or 'Protocol/Emulation/Session'}
        Compatibility: {compatibility_notes or 'Maintains compatibility with original implementation'}

        Licensed under {license_name}
        """

        return self._format_docstring(content.strip())

    def protocol_attribution(
        self,
        source_name: str,
        source_url: str,
        license_name: str,
        protocol_name: str,
        rfc_numbers: List[str],
        description: str,
        compatibility_notes: Optional[str] = None,
    ) -> str:
        """
        Generate protocol implementation attribution comment.

        Args:
            source_name: Name of the original source project
            source_url: URL to the original project
            license_name: Name of the license
            protocol_name: Name of the protocol (e.g., "TN3270", "TN3270E")
            rfc_numbers: List of RFC numbers this implements
            description: Description of the protocol implementation
            compatibility_notes: Notes about compatibility

        Returns:
            Formatted protocol attribution comment
        """
        content = f"""Protocol implementation ported from {source_name} ({source_url})

        Implements {protocol_name} protocol according to:
        {', '.join(f'RFC {rfc}' for rfc in rfc_numbers)}

        {description}

        Compatibility: {compatibility_notes or 'Follows RFC specifications and maintains compatibility with s3270'}
        Licensed under {license_name}
        """

        return self._format_docstring(content.strip())

    def s3270_compatibility_attribution(
        self,
        component_type: str,
        s3270_commands: List[str],
        description: str,
        integration_layer: str = "Protocol",
    ) -> str:
        """
        Generate s3270 compatibility attribution comment.

        Args:
            component_type: Type of component (e.g., "Protocol Handler", "Command Implementation")
            s3270_commands: List of s3270 commands this implements
            description: Description of the compatibility implementation
            integration_layer: Which layer this integrates into

        Returns:
            Formatted s3270 compatibility attribution comment
        """
        content = f"""s3270/x3270 Compatibility Implementation

        This {component_type.lower()} maintains compatibility with IBM s3270/x3270 terminal emulator.

        Compatible Commands/Features:
        {', '.join(s3270_commands)}

        {description}

        Integration Layer: {integration_layer}
        Source: https://github.com/rhacker/x3270
        License: BSD-3-Clause
        """

        return self._format_docstring(content.strip())

    def ebcdic_attribution(
        self,
        codec_name: str,
        description: str,
        fallback_behavior: str = "Falls back to standard library CP037 codec",
    ) -> str:
        """
        Generate EBCDIC codec attribution comment.

        Args:
            codec_name: Name of the codec being implemented
            description: Description of the codec implementation
            fallback_behavior: Description of fallback behavior

        Returns:
            Formatted EBCDIC attribution comment
        """
        content = f"""EBCDIC Codec Implementation

        Implements {codec_name} encoding/decoding for 3270 data streams.

        {description}

        Fallback: {fallback_behavior}
        Integration Layer: Emulation
        License: MIT (when using ebcdic package) / PSF (standard library fallback)
        """

        return self._format_docstring(content.strip())

    def generate_third_party_notice(
        self,
        source_name: str,
        source_url: str,
        license_name: str,
        license_text: str,
        description: str,
        ported_components: List[str],
        integration_layer: str,
        modifications: str,
        compatibility: str,
        optional_dependency: bool = False,
    ) -> str:
        """
        Generate THIRD_PARTY_NOTICES.md entry for a new dependency.

        Args:
            source_name: Name of the source project
            source_url: URL to the source project
            license_name: Name of the license
            license_text: Complete license text
            description: Description of the attribution
            ported_components: List of components that were ported
            integration_layer: Which layer this integrates into
            modifications: Description of modifications made
            compatibility: Compatibility statement
            optional_dependency: Whether this is an optional dependency

        Returns:
            Formatted THIRD_PARTY_NOTICES.md entry
        """
        sections = []

        # Header
        sections.append(f"## {source_name}")
        sections.append("")
        sections.append(f"**Project**: {source_name}")
        sections.append(f"**Website**: {source_url}")
        sections.append(f"**License**: {license_name}")
        if optional_dependency:
            sections.append("**Dependency Type**: Optional")
        sections.append("")

        # Attribution section
        sections.append("### Attribution")
        sections.append("")
        sections.append(description)
        sections.append("")

        # Usage/Integration section
        sections.append("#### Usage in Pure3270")
        for component in ported_components:
            sections.append(f"- **{component}**")
        sections.append(f"- **Integration Layer**: {integration_layer}")
        sections.append(f"- **Runtime Behavior**: {compatibility}")
        sections.append("")

        # Modifications section
        sections.append("#### Integration Points")
        sections.append(f"- {modifications}")
        sections.append("")

        # License section
        sections.append("### License Text")
        sections.append("")
        sections.append("```")
        sections.append(license_text.strip())
        sections.append("```")
        sections.append("")

        return "\n".join(sections)


# Convenience functions for common attribution patterns
def s3270_protocol_attribution(protocol_name: str, rfc_numbers: List[str]) -> str:
    """Generate standard s3270 protocol attribution."""
    templates = AttributionTemplates()
    return templates.protocol_attribution(
        source_name="IBM s3270/x3270",
        source_url="https://github.com/rhacker/x3270",
        license_name="BSD-3-Clause",
        protocol_name=protocol_name,
        rfc_numbers=rfc_numbers,
        description=f"Implementation follows RFC specifications and maintains compatibility with s3270 {protocol_name} handling",
        compatibility_notes="Compatible with s3270 protocol negotiation and data stream processing",
    )


def ebcdic_codec_attribution(codec_name: str) -> str:
    """Generate standard EBCDIC codec attribution."""
    templates = AttributionTemplates()
    return templates.ebcdic_attribution(
        codec_name=codec_name,
        description=f"Enhanced {codec_name} codec for international character support in 3270 data streams",
        fallback_behavior="Falls back to standard library CP037 codec when not available",
    )


def command_compatibility_attribution(commands: List[str]) -> str:
    """Generate standard s3270 command compatibility attribution."""
    templates = AttributionTemplates()
    return templates.s3270_compatibility_attribution(
        component_type="Command Implementation",
        s3270_commands=commands,
        description="Implements s3270-compatible command interface for 3270 terminal operations",
        integration_layer="Session",
    )
