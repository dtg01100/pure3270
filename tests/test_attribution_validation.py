#!/usr/bin/env python3
"""
Test suite for attribution comment validation.

This module tests the attribution scaffolding system to ensure:
- Attribution comments follow correct format
- All required information is present
- License compatibility is maintained
- Integration with existing documentation systems

Tests validate compliance with:
- THIRD_PARTY_NOTICES.md requirements
- PORTING_GUIDELINES.md standards
- MIT license compatibility
"""

import re
from typing import Any, Dict, List

import pytest

from tools.attribution_templates import (
    AttributionTemplates,
    python_standard_library_attribution,
)


class AttributionValidator:
    """Validates attribution comments for compliance with project standards."""

    def __init__(self) -> None:
        self.templates = AttributionTemplates()
        self.compatible_licenses = {
            "MIT License",
            "BSD-2-Clause",
            "BSD-3-Clause",
            "Apache License 2.0",
            "ISC License",
            "Python Software Foundation License (PSFL)",
        }

    def validate_module_attribution(self, attribution_text: str) -> Dict[str, Any]:
        issues: List[str] = []

        # Required sections
        required_sections = [
            "ATTRIBUTION NOTICE",
            "DESCRIPTION",
            "ATTRIBUTION REQUIREMENTS",
        ]
        for section in required_sections:
            if section not in attribution_text:
                issues.append(f"Missing required section: {section}")

        # License info
        if "Licensed under" not in attribution_text:
            issues.append("Missing license information")

        # Source info (must be present and non-empty)
        if "Source:" not in attribution_text:
            issues.append("Missing source information")
        else:
            for line in attribution_text.split("\n"):
                if line.strip().startswith("Source:"):
                    parts = line.split(":", 1)
                    if len(parts) < 2 or not parts[1].strip():
                        issues.append("Empty Source information")
                    break

        # Description non-empty if section present
        if "DESCRIPTION" in attribution_text:
            desc_section = self._extract_section(attribution_text, "DESCRIPTION")
            if not desc_section.strip():
                issues.append("Empty description section")

        # Updated date present
        if "Last updated:" not in attribution_text:
            issues.append("Missing update date")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "score": max(0, 10 - len(issues)),
        }

    def validate_function_attribution(self, attribution_text: str) -> Dict[str, Any]:
        issues: List[str] = []

        stripped = attribution_text.strip()
        if not (stripped.startswith('"""') and stripped.endswith('"""')):
            issues.append("Function attribution must be in docstring format")

        for phrase in ("Ported from", "Licensed under"):
            if phrase not in attribution_text:
                issues.append(f"Missing required phrase: {phrase}")

        if '"""' in attribution_text:
            content = (
                attribution_text.split('"""', 2)[1]
                if attribution_text.count('"""') >= 2
                else ""
            )
            if not content.strip():
                issues.append("Empty docstring content")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "score": max(0, 10 - len(issues)),
        }

    def validate_license_compatibility(self, license_name: str) -> bool:
        if not license_name:
            return False
        name = str(license_name).strip()
        if not name:
            return False
        return name in self.compatible_licenses

    def validate_rfc_references(self, rfc_numbers: List[str]) -> List[str]:
        issues: List[str] = []
        pattern = re.compile(r"^RFC\s*\d+$")
        if not rfc_numbers:
            return issues
        for rfc in rfc_numbers:
            # RFC entries must not have leading/trailing whitespace and must match exact pattern
            if not rfc or not isinstance(rfc, str):
                issues.append(f"Invalid RFC format: {rfc}. Expected format: 'RFC 1234'")
                continue
            if rfc != rfc.strip():
                issues.append(
                    f"Invalid RFC format (whitespace): {rfc}. Expected format: 'RFC 1234'"
                )
                continue
            if not pattern.match(rfc):
                issues.append(f"Invalid RFC format: {rfc}. Expected format: 'RFC 1234'")
        return issues

    def validate_url_format(self, url: str) -> bool:
        if not url or not isinstance(url, str):
            return False
        url = url.strip()
        if not url:
            return False
        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)
        except Exception:
            return False
        if parsed.scheme not in ("http", "https"):
            return False
        if not parsed.netloc:
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        # Hostname must not contain spaces
        if " " in hostname:
            return False
        if hostname != "localhost" and not re.match(r"^\d+\.\d+\.\d+\.\d+$", hostname):
            if "." not in hostname or ".." in hostname:
                return False
        try:
            port = parsed.port
        except ValueError:
            return False
        if port is not None and (port < 1 or port > 65535):
            return False
        return True

    def _extract_section(self, text: str, section_name: str) -> str:
        lines = text.split("\n")
        in_section = False
        content_lines: List[str] = []
        for line in lines:
            if line.strip() == section_name:
                in_section = True
                continue
            if in_section:
                # Skip divider lines (----)
                if line.strip().startswith("-") and not content_lines:
                    continue
                # If we hit another all-caps section header, stop collecting
                stripped = line.strip()
                if (
                    stripped
                    and stripped == stripped.upper()
                    and not stripped.startswith("-")
                    and not stripped.isdigit()
                ):
                    break
                # Blank lines before any content are ignored; blank after content ends section
                if line.strip() == "" and content_lines:
                    break
                content_lines.append(line)
        return "\n".join(content_lines)


class TestAttributionTemplatesGeneration:
    def setup_method(self) -> None:
        self.templates = AttributionTemplates()

    def test_module_attribution_generation(self) -> None:
        result = self.templates.module_attribution(
            source_name="IBM s3270/x3270",
            source_url="https://github.com/rhacker/x3270",
            license_name="BSD-3-Clause",
            description="TN3270 protocol implementation based on s3270",
            compatibility_notes="Compatible with s3270 command interface",
            modification_notes="Adapted for async Python implementation",
            integration_points=["Protocol layer", "Emulation layer"],
            rfc_references=["RFC 1576", "RFC 2355"],
        )
        assert isinstance(result, str)
        assert len(result) > 100
        assert "IBM s3270/x3270" in result
        assert "BSD-3-Clause" in result
        assert "TN3270 protocol implementation" in result

    def test_function_attribution_generation(self) -> None:
        result = self.templates.function_attribution(
            source_name="ebcdic package",
            source_url="https://pypi.org/project/ebcdic/",
            license_name="MIT License",
            description="EBCDIC encoding/decoding functionality",
            function_name="encode_ebcdic",
            compatibility_notes="Maintains compatibility with standard library",
            rfc_references=["RFC 1576"],
        )
        assert isinstance(result, str)
        assert result.startswith('    """')
        assert result.endswith('"""')
        assert "ebcdic package" in result
        assert "MIT License" in result
        assert "encode_ebcdic" in result

    def test_protocol_attribution_generation(self) -> None:
        result = self.templates.protocol_attribution(
            source_name="IBM s3270/x3270",
            source_url="https://github.com/rhacker/x3270",
            license_name="BSD-3-Clause",
            protocol_name="TN3270E",
            rfc_numbers=["RFC 1576", "RFC 2355"],
            description="Enhanced TN3270 protocol with printer session support",
            compatibility_notes="Full compatibility with s3270 TN3270E implementation",
        )
        assert isinstance(result, str)
        assert result.startswith('    """')
        assert result.endswith('"""')
        assert "TN3270E" in result
        assert "RFC 1576" in result
        assert "RFC 2355" in result

    def test_s3270_compatibility_attribution(self) -> None:
        result = self.templates.s3270_compatibility_attribution(
            component_type="Protocol Handler",
            s3270_commands=["String", "Ascii", "Ebcdic", "Enter", "PF(1-24)"],
            description="Implements s3270-compatible command interface",
            integration_layer="Protocol",
        )
        assert isinstance(result, str)
        assert result.startswith('    """')
        assert result.endswith('"""')
        assert "s3270/x3270 Compatibility" in result
        assert "String" in result
        assert "Ascii" in result

    def test_ebcdic_attribution_generation(self) -> None:
        result = self.templates.ebcdic_attribution(
            codec_name="EBCDIC-CP037",
            description="Enhanced EBCDIC codec with international character support",
            fallback_behavior="Falls back to standard library CP037 codec",
        )
        assert isinstance(result, str)
        assert result.startswith('    """')
        assert result.endswith('"""')
        assert "EBCDIC-CP037" in result
        assert "international character support" in result
        assert "fallback" in result.lower()

    def test_third_party_notice_generation(self) -> None:
        license_text = """MIT License

Copyright (c) 2024, Some Author

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the \"Software\"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""

        result = self.templates.generate_third_party_notice(
            source_name="Test Package",
            source_url="https://example.com/test-package",
            license_name="MIT License",
            license_text=license_text,
            description="Test package for attribution validation",
            ported_components=["test_module.py", "test_function()"],
            integration_layer="Emulation",
            modifications="Adapted for Pure3270's async architecture",
            compatibility="Maintains API compatibility with original",
            optional_dependency=True,
        )
        assert isinstance(result, str)
        assert "## Test Package" in result
        assert "MIT License" in result
        assert "test_module.py" in result
        assert "Emulation" in result
        assert "optional" in result.lower()


class TestAttributionValidation:
    def setup_method(self) -> None:
        self.validator = AttributionValidator()

    def test_module_attribution_validation_valid(self) -> None:
        valid_attribution = """ATTRIBUTION NOTICE
==================================================
This module contains code ported from or inspired by: IBM s3270/x3270
Source: https://github.com/rhacker/x3270
    Licensed under BSD-3-Clause

DESCRIPTION
----------------
TN3270 protocol implementation based on s3270

COMPATIBILITY
----------------
Compatible with s3270 command interface

ATTRIBUTION REQUIREMENTS
------------------------------
This attribution must be maintained when this code is modified or
redistributed. See THIRD_PARTY_NOTICES.md for complete license text.
Last updated: 2025-09-23"""

        result = self.validator.validate_module_attribution(valid_attribution)
        assert result["valid"] is True
        assert len(result["issues"]) == 0
        assert result["score"] == 10

    def test_module_attribution_validation_invalid(self) -> None:
        invalid_attribution = (
            "This is just some text without proper formatting.\n"
            "No sections, no license info, no description."
        )
        result = self.validator.validate_module_attribution(invalid_attribution)
        assert result["valid"] is False
        assert len(result["issues"]) > 0
        assert result["score"] < 10

    def test_function_attribution_validation_valid(self) -> None:
        valid_attribution = '''    """
    Ported from IBM s3270/x3270 (https://github.com/rhacker/x3270)

    TN3270 protocol handling functionality

    Licensed under BSD-3-Clause

    Compatibility: Maintains compatibility with original implementation
    """'''
        result = self.validator.validate_function_attribution(valid_attribution)
        assert result["valid"] is True
        assert len(result["issues"]) == 0
        assert result["score"] == 10

    def test_function_attribution_validation_invalid(self) -> None:
        invalid_attribution = "Just plain text without docstring format"
        result = self.validator.validate_function_attribution(invalid_attribution)
        assert result["valid"] is False
        assert len(result["issues"]) > 0

    def test_license_compatibility_validation(self) -> None:
        assert self.validator.validate_license_compatibility("MIT License") is True

    def test_malformed_module_attributions(self) -> None:
        malformed_cases = [
            # Missing license line
            """ATTRIBUTION NOTICE
            ==================================================
            This module contains code ported from or inspired by: Test Project
            Source: https://example.com

            DESCRIPTION
            ----------------
            Test description

            ATTRIBUTION REQUIREMENTS
            ------------------------------
            This attribution must be maintained when this code is modified or
            redistributed. See THIRD_PARTY_NOTICES.md for complete license text.
            Last updated: 2025-09-23""",
            # Missing description content
            """ATTRIBUTION NOTICE
            ==================================================
            This module contains code ported from or inspired by: Test Project
            Source: https://example.com
                Licensed under MIT License

            DESCRIPTION
            ----------------

            ATTRIBUTION REQUIREMENTS
            ------------------------------
            This attribution must be maintained when this code is modified or
            redistributed. See THIRD_PARTY_NOTICES.md for complete license text.
            Last updated: 2025-09-23""",
            # Wrong content instead of DESCRIPTION section
            """ATTRIBUTION NOTICE
            ==================================================
            This module contains code ported from or inspired by: Test Project
            Source: https://example.com
                Licensed under MIT License

            Some random text instead of DESCRIPTION section

            ATTRIBUTION REQUIREMENTS
            ------------------------------
            This attribution must be maintained when this code is modified or
            redistributed. See THIRD_PARTY_NOTICES.md for complete license text.
            Last updated: 2025-09-23""",
        ]
        for i, case in enumerate(malformed_cases):
            result = self.validator.validate_module_attribution(case)
            assert result["valid"] is False, f"Test case {i+1} should be invalid"
            assert len(result["issues"]) > 0, f"Test case {i+1} should have issues"

    def test_function_attribution_edge_cases(self) -> None:
        edge_cases = [
            # Empty docstring
            '    """    """',
            # Missing source information
            '''    """
            Some description here

            Licensed under MIT License
            """''',
            # Missing license information
            '''    """
            Ported from some project (https://example.com)

            Some description
            """''',
            # Wrong format (not a docstring)
            """Ported from some project (https://example.com)

            Some description

            Licensed under MIT License""",
            # Multiple line docstring with missing elements
            '''    """
    Ported from some project

    Some description here
    """''',
        ]
        for i, case in enumerate(edge_cases):
            result = self.validator.validate_function_attribution(case)
            assert result["valid"] is False, f"Edge case {i+1} should be invalid"
            assert len(result["issues"]) > 0, f"Edge case {i+1} should have issues"

    def test_license_compatibility_edge_cases(self) -> None:
        assert self.validator.validate_license_compatibility("") is False
        assert self.validator.validate_license_compatibility(None) is False
        assert self.validator.validate_license_compatibility("   ") is False
        assert self.validator.validate_license_compatibility("mit license") is False
        assert self.validator.validate_license_compatibility("MIT License") is True
        assert self.validator.validate_license_compatibility("  MIT License  ") is True

    def test_rfc_reference_edge_cases(self) -> None:
        issues = self.validator.validate_rfc_references([])
        assert len(issues) == 0

        issues = self.validator.validate_rfc_references(None)
        assert len(issues) == 0

        malformed_rfcs = [
            "RFC",
            "RFC ",
            "RFC 1576a",
            "rfc 1576",
            "RFC-1576",
            "1576",
            "RFC 1576 ",
            " RFC 1576",
        ]
        for rfc in malformed_rfcs:
            issues = self.validator.validate_rfc_references([rfc])
            assert len(issues) > 0, f"Should detect issue with: {rfc}"

    def test_url_format_edge_cases(self) -> None:
        assert self.validator.validate_url_format("") is False
        assert self.validator.validate_url_format(None) is False
        assert self.validator.validate_url_format("   ") is False

        malformed_urls = [
            "not-a-url",
            "://invalid-url",
            "ftp://example.com",
            "https://",
            "https://example",
            "https://example..com",
            "https://example.com:99999",
            "https://example .com",
        ]
        for url in malformed_urls:
            assert (
                self.validator.validate_url_format(url) is False
            ), f"Should reject malformed URL: {url}"

    def test_unicode_handling_in_attributions(self) -> None:
        unicode_cases = [
            # Unicode in source name
            """ATTRIBUTION NOTICE
            ==================================================
            This module contains code ported from or inspired by: 测试项目
            Source: https://测试.com
                Licensed under MIT License

            DESCRIPTION
            ----------------
            Unicode测试描述

            ATTRIBUTION REQUIREMENTS
            ------------------------------
            This attribution must be maintained when this code is modified or
            redistributed. See THIRD_PARTY_NOTICES.md for complete license text.
            Last updated: 2025-09-23""",
            # Unicode in description
            """ATTRIBUTION NOTICE
            ==================================================
            This module contains code ported from or inspired by: Test Project
            Source: https://example.com
                Licensed under MIT License

            DESCRIPTION
            ----------------
            Description with special chars: àáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ

            ATTRIBUTION REQUIREMENTS
            ------------------------------
            This attribution must be maintained when this code is modified or
            redistributed. See THIRD_PARTY_NOTICES.md for complete license text.
            Last updated: 2025-09-23""",
            # Unicode in compatibility notes
            """ATTRIBUTION NOTICE
            ==================================================
            This module contains code ported from or inspired by: Test Project
            Source: https://example.com
                Licensed under MIT License

            DESCRIPTION
            ----------------
            Test description

            COMPATIBILITY
            ----------------
            Compatible with spécial characters: àáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ

            ATTRIBUTION REQUIREMENTS
            ------------------------------
            This attribution must be maintained when this code is modified or
            redistributed. See THIRD_PARTY_NOTICES.md for complete license text.
            Last updated: 2025-09-23""",
        ]
        for case in unicode_cases:
            result = self.validator.validate_module_attribution(case)
            assert isinstance(result, dict)
            assert "valid" in result
            assert "issues" in result

    def test_very_long_attribution_content(self) -> None:
        long_description = "A" * 10000
        long_attribution = f"""ATTRIBUTION NOTICE
        ==================================================
        This module contains code ported from or inspired by: Test Project
        Source: https://example.com
            Licensed under MIT License

        DESCRIPTION
        ----------------
        {long_description}

        ATTRIBUTION REQUIREMENTS
        ------------------------------
        This attribution must be maintained when this code is modified or
        redistributed. See THIRD_PARTY_NOTICES.md for complete license text.
        Last updated: 2025-09-23"""
        result = self.validator.validate_module_attribution(long_attribution)
        assert isinstance(result, dict)
        assert "valid" in result

    def test_attribution_with_extra_whitespace(self) -> None:
        whitespace_cases = [
            # Extra spaces in sections
            """ATTRIBUTION NOTICE
            ==================================================
            This module contains code ported from or inspired by: Test Project
            Source: https://example.com
                Licensed under MIT License

            DESCRIPTION
            ----------------

            Extra space above

            ATTRIBUTION REQUIREMENTS
            ------------------------------
            This attribution must be maintained when this code is modified or
            redistributed. See THIRD_PARTY_NOTICES.md for complete license text.
            Last updated: 2025-09-23""",
            # Tabs instead of spaces
            """ATTRIBUTION NOTICE
            ==================================================
            This module contains code ported from or inspired by: Test Project
            Source: https://example.com
		Licensed under MIT License

            DESCRIPTION
            ----------------
            Test description

            ATTRIBUTION REQUIREMENTS
            ------------------------------
            This attribution must be maintained when this code is modified or
            redistributed. See THIRD_PARTY_NOTICES.md for complete license text.
            Last updated: 2025-09-23""",
            # Mixed whitespace
            """ATTRIBUTION NOTICE
            ==================================================
            This module contains code ported from or inspired by: Test Project
            Source: https://example.com
 		Licensed under MIT License

            DESCRIPTION
            ----------------
            Test description

            ATTRIBUTION REQUIREMENTS
            ------------------------------
            This attribution must be maintained when this code is modified or
            redistributed. See THIRD_PARTY_NOTICES.md for complete license text.
            Last updated: 2025-09-23""",
        ]
        for case in whitespace_cases:
            result = self.validator.validate_module_attribution(case)
            assert isinstance(result, dict)
            assert "valid" in result


class TestAttributionIntegrationScenarios:
    def setup_method(self) -> None:
        self.validator = AttributionValidator()
        self.templates = AttributionTemplates()

    def test_real_world_s3270_attribution_scenario(self) -> None:
        s3270_attribution = self.templates.module_attribution(
            source_name="IBM s3270/x3270 Terminal Emulator",
            source_url="https://github.com/rhacker/x3270",
            license_name="BSD-3-Clause",
            description=(
                "TN3270E protocol implementation with printer session support, "
                "ported from s3270 for enhanced compatibility"
            ),
            compatibility_notes=(
                "Maintains full compatibility with s3270 command interface and protocol handling"
            ),
            modification_notes=(
                "Adapted for async Python implementation with enhanced error handling"
            ),
            integration_points=[
                "Protocol layer",
                "Session management",
                "Data stream processing",
            ],
            rfc_references=["RFC 1576", "RFC 2355"],
        )
        result = self.validator.validate_module_attribution(s3270_attribution)
        assert result["valid"] is True
        assert result["score"] == 10
        assert "IBM s3270/x3270" in s3270_attribution
        assert "BSD-3-Clause" in s3270_attribution
        assert "RFC 1576" in s3270_attribution
        assert "RFC 2355" in s3270_attribution
        assert "Protocol layer" in s3270_attribution
        assert "async Python" in s3270_attribution

    def test_real_world_python_stdlib_scenario(self) -> None:
        asyncio_attribution = python_standard_library_attribution(
            module_name="asyncio",
            usage_description=(
                "asynchronous I/O operations and event loop management in TN3270 protocol handler"
            ),
        )
        result = self.validator.validate_function_attribution(asyncio_attribution)
        assert result["valid"] is True
        assert result["score"] == 10
        assert "Python Standard Library" in asyncio_attribution
        assert "asyncio" in asyncio_attribution
        assert "PSFL" in asyncio_attribution

    def test_mixed_attribution_scenario(self) -> None:
        module_attribution = self.templates.module_attribution(
            source_name="IBM s3270/x3270",
            source_url="https://github.com/rhacker/x3270",
            license_name="BSD-3-Clause",
            description="Core TN3270 protocol implementation",
            compatibility_notes="Compatible with s3270",
        )
        function_attribution = python_standard_library_attribution(
            module_name="socket",
            usage_description="network socket operations for TN3270 connections",
        )
        module_result = self.validator.validate_module_attribution(module_attribution)
        function_result = self.validator.validate_function_attribution(
            function_attribution
        )
        assert module_result["valid"] is True
        assert function_result["valid"] is True

    def test_third_party_notice_integration(self) -> None:
        license_text = """MIT License

Copyright (c) 2024, Test Author

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the \"Software\"), to deal
in the Software without restriction, including without limitation the rights
 to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""

        notice = self.templates.generate_third_party_notice(
            source_name="Test EBCDIC Library",
            source_url="https://github.com/test/ebcdic",
            license_name="MIT License",
            license_text=license_text,
            description="Enhanced EBCDIC encoding library for 3270 terminal support",
            ported_components=["emulation/ebcdic.py", "protocol/data_stream.py"],
            integration_layer="Emulation",
            modifications=(
                "Adapted for async compatibility and enhanced character set support"
            ),
            compatibility="Maintains compatibility with standard EBCDIC encoding",
            optional_dependency=True,
        )
        assert "## Test EBCDIC Library" in notice
        assert "**Project**:" in notice
        assert "**Website**:" in notice
        assert "**License**:" in notice
        assert "**Dependency Type**: Optional" in notice
        assert "### Attribution" in notice
        assert "#### Usage in Pure3270" in notice
        assert "- **emulation/ebcdic.py**" in notice
        assert "- **protocol/data_stream.py**" in notice
        assert "- **Integration Layer**: Emulation" in notice
        assert "### License Text" in notice
        assert "```" in notice
        assert license_text.strip() in notice

    def test_license_compatibility_matrix(self) -> None:
        compatible_licenses = [
            "MIT License",
            "BSD-2-Clause",
            "BSD-3-Clause",
            "Apache License 2.0",
            "ISC License",
            "Python Software Foundation License (PSFL)",
        ]
        for license_name in compatible_licenses:
            assert self.validator.validate_license_compatibility(license_name) is True

        incompatible_licenses = [
            "GPL-2.0",
            "GPL-3.0",
            "LGPL-2.1",
            "LGPL-3.0",
            "Proprietary",
            "Commercial License",
            "Custom License",
        ]
        for license_name in incompatible_licenses:
            assert self.validator.validate_license_compatibility(license_name) is False


class TestAttributionMaintenanceScenarios:
    def setup_method(self) -> None:
        self.validator = AttributionValidator()
        self.templates = AttributionTemplates()

    def test_outdated_attribution_detection(self) -> None:
        old_date = "2020-01-01"
        old_attribution = f"""ATTRIBUTION NOTICE
        ==================================================
        This module contains code ported from or inspired by: Test Project
        Source: https://example.com
            Licensed under MIT License

        DESCRIPTION
        ----------------
        Test description

        ATTRIBUTION REQUIREMENTS
        ------------------------------
        This attribution must be maintained when this code is modified or
        redistributed. See THIRD_PARTY_NOTICES.md for complete license text.
        Last updated: {old_date}"""
        result = self.validator.validate_module_attribution(old_attribution)
        assert result["valid"] is True

    def test_attribution_format_evolution(self) -> None:
        current_format_elements = [
            "ATTRIBUTION NOTICE",
            "=" * 50,
            "This module contains code ported from or inspired by:",
            "Source:",
            "Licensed under",
            "DESCRIPTION",
            "-" * 20,
            "ATTRIBUTION REQUIREMENTS",
            "-" * 30,
            "This attribution must be maintained when this code is modified or",
            "redistributed. See THIRD_PARTY_NOTICES.md for complete license text.",
            "Last updated:",
        ]
        current_attribution = self.templates.module_attribution(
            source_name="Test Project",
            source_url="https://example.com",
            license_name="MIT License",
            description="Test description",
        )
        for element in current_format_elements:
            assert element in current_attribution, f"Missing format element: {element}"

    def test_attribution_consistency_check(self) -> None:
        attr1 = self.templates.function_attribution(
            source_name="Test Project",
            source_url="https://example.com",
            license_name="MIT License",
            description="Function 1",
            function_name="func1",
        )
        attr2 = self.templates.function_attribution(
            source_name="Test Project",
            source_url="https://example.com",
            license_name="MIT License",
            description="Function 2",
            function_name="func2",
        )
        result1 = self.validator.validate_function_attribution(attr1)
        result2 = self.validator.validate_function_attribution(attr2)
        assert result1["valid"] is True
        assert result2["valid"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
