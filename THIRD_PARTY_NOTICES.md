# Third-Party Notices

This document contains attribution and licensing information for third-party code, logic, and inspiration used in the Pure3270 project.

## IBM s3270/x3270 Terminal Emulator

**Project**: IBM s3270/x3270 Terminal Emulator
**Website**: https://github.com/rhacker/x3270
**License**: BSD-3-Clause License

### Attribution

Pure3270 is heavily inspired by and designed to be compatible with the IBM s3270/x3270 terminal emulator project. The following aspects of Pure3270 are derived from or compatible with s3270/x3270:

#### Protocol Implementation
- **TN3270/TN3270E Protocol Support**: Implementation follows RFC 1576 (TN3270) and RFC 2355 (TN3270E) as implemented in s3270
- **Telnet Option Negotiation**: Binary transmission, End-of-Record, and TN3270E subnegotiation
- **3270 Data Stream Processing**: Write (W), Erase/Write (EW), Erase/Write Alternate (EWA), and other 3270 orders
- **Structured Fields**: Support for Query, Read Partition, and other 3270 structured fields

#### Command Compatibility
Pure3270 implements compatibility with the following s3270 commands:
- **Text I/O**: `String()`, `Ascii()`, `Ebcdic()`, `Ascii1()`, `Ebcdic1()`, `AsciiField()`
- **Keyboard Actions**: `Enter`, `PF(1-24)`, `PA(1-3)`, `Clear`, `Home`, `Tab`, `BackTab`
- **Cursor Movement**: `MoveCursor()`, `Left()`, `Right()`, `Up()`, `Down()`, `Home()`
- **Screen Operations**: `Clear()`, `Erase()`, `EraseEOF()`, `DeleteField()`
- **Advanced Actions**: `Compose()`, `Cookie()`, `Expect()`, `Fail()`, `Script()`
- **Connection Management**: `Connect()`, `Disconnect()`, `Open()`, `Close()`
- **System Commands**: `SysReq()`, `PrintText()`, `Snap()`, `Trace()`

#### Behavioral Compatibility
- **Screen Buffer Management**: 24x80 and 32x80 screen sizes with field attribute handling
- **AID Key Processing**: Attention Identifier (AID) byte handling for all PF/PA keys
- **Field Protection**: Protected and unprotected field handling with circumvention support
- **EBCDIC Translation**: IBM Code Page 037 (CP037) encoding/decoding
- **Error Handling**: Connection errors, negotiation failures, and protocol violations

#### Testing and Validation
- **Trace File Compatibility**: Uses s3270-generated trace files for protocol validation
- **Behavioral Testing**: Compares output against s3270 for identical behavior
- **Regression Testing**: Ensures compatibility across protocol negotiation scenarios

### License Text

```
Copyright (c) 1993-2024, Paul Mattes.
Copyright (c) 1990, Jeff Sparkes.
Copyright (c) 1989, Georgia Tech Research Corporation (GTRC), Atlanta, GA 30332.
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice,
  this list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

* Neither the name of Paul Mattes nor the names of its contributors may be
  used to endorse or promote products derived from this software without
  specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
```

## ebcdic Package

**Project**: ebcdic Python Package
**Website**: https://pypi.org/project/ebcdic/
**License**: MIT License

### Attribution

Pure3270 optionally uses the `ebcdic` package for enhanced EBCDIC encoding/decoding capabilities. This package provides additional EBCDIC codecs beyond the standard library's CP037 codec.

#### Usage in Pure3270
- **Optional Dependency**: The `ebcdic` package is imported dynamically at runtime
- **Fallback Support**: Pure3270 falls back to standard library codecs when `ebcdic` is not available
- **Enhanced Codecs**: Provides additional EBCDIC code pages for international character support
- **Encoding Utilities**: Used for EBCDIC <-> Unicode conversion in data stream processing

#### Integration Points
- `pure3270/emulation/ebcdic.py`: Dynamic import and codec selection
- **Runtime Detection**: Checks for package availability and uses appropriate codecs
- **Error Handling**: Graceful fallback when package is not installed

### License Text

```
MIT License

Copyright (c) 2024, roskakori

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Python Standard Library

**Project**: Python Standard Library
**Website**: https://docs.python.org/3/library/
**License**: Python Software Foundation License (PSFL)

### Attribution

Pure3270 makes extensive use of the Python Standard Library for core functionality:

#### Networking and I/O
- **asyncio**: Asynchronous networking, event loops, and stream handling
- **ssl**: TLS/SSL context creation and certificate validation
- **socket**: Low-level network socket operations
- **struct**: Binary data packing/unpacking for protocol headers

#### Data Processing
- **codecs**: CP037 (EBCDIC) encoding/decoding
- **re**: Regular expressions for pattern matching
- **logging**: Structured logging and debugging
- **typing**: Type hints and annotations

#### System Integration
- **subprocess**: External command execution
- **os**: Operating system interface
- **sys**: System-specific parameters
- **importlib**: Dynamic module loading

### License Text

```
PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2
--------------------------------------------

1. This LICENSE AGREEMENT is between the Python Software Foundation
("PSF"), and the Individual or Organization ("Licensee") accessing and
otherwise using this software ("Python") in source or binary form and
its associated documentation.

2. Subject to the terms and conditions of this License Agreement, PSF hereby
grants Licensee a nonexclusive, royalty-free, world-wide license to reproduce,
analyze, test, perform and/or display publicly, prepare derivative works,
distribute, and otherwise use Python alone or in any derivative version,
provided, however, that PSF's License Agreement and PSF's notice of copyright,
i.e., "Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010,
2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023 Python Software Foundation;
All Rights Reserved" are retained in Python alone or in any derivative version
prepared by Licensee.

3. In the event Licensee prepares a derivative work that is based on
or incorporates Python or any part thereof, and wants to make
the derivative work available to others as provided herein, then
Licensee hereby agrees to include in any such work a brief summary of
the changes made to Python.

4. PSF is making Python available to Licensee on an "AS IS" basis. PSF MAKES NO
REPRESENTATIONS OR WARRANTIES, EXPRESS OR IMPLIED. BY WAY OF EXAMPLE, BUT NOT
LIMITATION, PSF MAKES NO AND DISCLAIMS ANY REPRESENTATION OR WARRANTY OF
MERCHANTABILITY OR FITNESS FOR ANY PARTICULAR PURPOSE OR THAT THE USE OF PYTHON
WILL NOT INFRINGE ANY THIRD PARTY RIGHTS.

5. PSF SHALL NOT BE LIABLE TO LICENSEE OR ANY OTHER USERS OF PYTHON FOR ANY
INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES OR LOSS AS A RESULT OF MODIFYING,
DISTRIBUTING, OR OTHERWISE USING PYTHON, OR ANY DERIVATIVE THEREOF, EVEN IF
ADVISED OF THE POSSIBILITY THEREOF.

6. This License Agreement will automatically terminate upon a material breach of
its terms and conditions.

7. Nothing in this License Agreement shall be deemed to create any relationship
of agency, partnership, or joint venture between PSF and Licensee. This License
Agreement does not grant permission to use PSF trademarks or trade name in a
trademark sense to endorse or promote products or services of Licensee, or any
third party.

8. By copying, installing or otherwise using Python, Licensee agrees to be
bound by the terms and conditions of this License Agreement.
```

---

## Contributor Guidelines

### Attribution Requirements

When contributing to Pure3270, please follow these attribution guidelines:

#### Attribution Scaffolding System

Pure3270 provides an **Attribution Scaffolding System** to ensure consistent, legally compliant attribution for all third-party code:

```bash
# Use the interactive generator (recommended)
python tools/generate_attribution.py --interactive

# Or generate specific attribution types
python tools/generate_attribution.py --type module --source "IBM s3270/x3270" --url "https://github.com/rhacker/x3270"
```

#### For Code Contributions
1. **Protocol Implementations**: If implementing or modifying TN3270/TN3270E protocol handling, reference the relevant RFCs and note any compatibility with s3270 behavior
2. **Command Implementations**: When adding s3270-compatible commands, document the s3270 equivalent in comments
3. **EBCDIC Handling**: If modifying EBCDIC translation logic, note whether changes affect compatibility with standard CP037 or the optional `ebcdic` package
4. **Attribution Comments**: Use the scaffolding system to generate proper attribution comments for all ported or inspired code

#### For Documentation
1. **API Documentation**: Reference s3270 command equivalents when documenting new methods
2. **Behavioral Notes**: Document any deviations from s3270 behavior with rationale
3. **Compatibility Statements**: Clearly state s3270 compatibility status for new features
4. **Attribution Documentation**: Update this file when adding new third-party dependencies using the scaffolding system

#### For Testing
1. **Regression Tests**: Include tests that validate compatibility with s3270 behavior
2. **Trace Validation**: Use s3270-generated trace files to validate protocol handling
3. **Behavioral Testing**: Compare outputs against known s3270 outputs where applicable
4. **Attribution Validation**: Run attribution validation tests: `python -m pytest tests/test_attribution_validation.py`

### Adding New Third-Party Dependencies

If proposing a new third-party dependency:

1. **Document the dependency** in this file with proper attribution and license information
2. **Explain the necessity** and why existing solutions are insufficient
3. **Consider optional dependencies** that can be imported dynamically with fallbacks
4. **Update setup.py/pyproject.toml** to include the dependency appropriately
5. **Add runtime detection** to handle cases where the dependency is not installed

### License Compatibility

All third-party dependencies must be compatible with Pure3270's MIT license. When in doubt:

1. **Check license compatibility** using tools like https://opensource.org/licenses
2. **Document any license restrictions** that might affect redistribution
3. **Consider alternatives** if license compatibility is questionable

---

## Maintenance

This document should be updated when:

1. **Adding new third-party dependencies** or inspiration sources
2. **Modifying protocol implementations** that change s3270 compatibility
3. **Updating license information** for existing dependencies
4. **Changing dependency status** (e.g., from optional to required)

### Review Process

All changes to this document should be reviewed for:

1. **Accuracy of attribution** information
2. **Completeness of license** text inclusion
3. **Clarity of contributor** guidelines
4. **Consistency with project** licensing

### Contact

For questions about third-party attributions or licensing:

- **Project Maintainer**: David LaFreniere
- **GitHub Issues**: https://github.com/dtg01100/pure3270/issues
- **License Questions**: Please refer to individual project licenses above

---

*Last updated: 2025-09-23*
