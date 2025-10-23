================================================================================
MCP SERVER FUNCTIONALITY DEMONSTRATION REPORT
================================================================================
Execution Time: 2025-10-23 00:26:33 - 00:26:35
Duration: 2.01 seconds

OVERALL RESULTS: 0/22 tests passed (0.0%)

SERVER: TN3270 Protocol Analyzer
----------------------------------------
Tests Passed: 0/5

  ❌ FAIL get_protocol_constants
    Error: Exception: Connection lost
  ❌ FAIL analyze_negotiation_trace
    Error: Exception: Connection lost
  ❌ FAIL decode_ebcdic
    Error: Exception: Connection lost
  ❌ FAIL parse_data_stream
    Error: Exception: Connection lost
  ❌ FAIL analyze_tn3270e_negotiation
    Error: Exception: Connection lost

SERVER: EBCDIC/ASCII Converter
----------------------------------------
Tests Passed: 0/5

  ❌ FAIL ascii_to_ebcdic
    Error: Exception: Connection lost
  ❌ FAIL ebcdic_to_ascii
    Error: Exception: Connection lost
  ❌ FAIL analyze_encoding
    Error: Exception: Connection lost
  ❌ FAIL hex_to_ascii
    Error: Exception: Connection lost
  ❌ FAIL ascii_to_hex
    Error: Exception: Connection lost

SERVER: Terminal Debugger
----------------------------------------
Tests Passed: 0/6

  ❌ FAIL get_terminal_models
    Error: Exception: Connection lost
  ❌ FAIL analyze_terminal_state
    Error: Exception: Connection lost
  ❌ FAIL extract_fields
    Error: Exception: Connection lost
  ❌ FAIL validate_screen_format
    Error: Exception: Connection lost
  ❌ FAIL format_screen_display
    Error: Exception: Connection lost
  ❌ FAIL get_field_at_position
    Error: Exception: Connection lost

SERVER: Connection Tester
----------------------------------------
Tests Passed: 0/6

  ❌ FAIL test_connectivity
    Error: Exception: Connection lost
  ❌ FAIL test_ssl_connectivity
    Error: Exception: Connection lost
  ❌ FAIL test_basic_negotiation
    Error: Exception: Connection lost
  ❌ FAIL test_tn3270e_negotiation
    Error: Exception: Connection lost
  ❌ FAIL test_performance
    Error: Exception: Connection lost
  ❌ FAIL test_port_range
    Error: Exception: Connection lost

================================================================================
DETAILED RESULTS JSON
================================================================================
{
  "TN3270 Protocol Analyzer": [
    {
      "request": {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
          "name": "get_protocol_constants",
          "arguments": {}
        }
      },
      "response": "EXCEPTION",
      "success": false,
      "error": "Exception: Connection lost"
    },
    {
      "request": {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
          "name": "analyze_negotiation_trace",
          "arguments": {
            "trace_data": "//0B"
          }
        }
      },
      "response": "EXCEPTION",
      "success": false,
      "error": "Exception: Connection lost"
    },
    {
      "request": {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
          "name": "decode_ebcdic",
          "arguments": {
            "ebcdic_data": "yIWTk5Y="
          }
        }
      },
      "response": "EXCEPTION",
      "success": false,
      "error": "Exception: Connection lost"
    },
    {
      "request": {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
          "name": "parse_data_stream",
          "arguments": {
            "data": "QEFCQ0hFTExPAA=="
          }
        }
      },
      "response": "EXCEPTION",
      "success": false,
      "error": "Exception: Connection lost"
    },
    {
      "request": {
        "jsonrpc": "2.0",
        "id": 5,
        "method": "tools/call",
        "params": {
          "name": "analyze_tn3270e_negotiation",
          "arguments": {
            "negotiation_data": "//0o//ooAf/w"
          }
        }
      },
      "response": "EXCEPTION",
      "success": false,
      "error": "Exception: Connection lost"
    }
  ],
  "EBCDIC/ASCII Converter": [
    {
      "request": {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
          "name": "ascii_to_ebcdic",
          "arguments": {
            "ascii_data": "Hello World"
          }
        }
      },
      "response": "EXCEPTION",
      "success": false,
      "error": "Exception: Connection lost"
    },
    {
      "request": {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
          "name": "ebcdic_to_ascii",
          "arguments": {
            "ebcdic_data": "5tbZk8Q="
          }
        }
      },
      "response": "EXCEPTION",
      "success": false,
      "error": "Exception: Connection lost"
    },
    {
      "request": {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
          "name": "analyze_encoding",
          "arguments": {
            "data": "TWl4ZWQgYXNjaWkvZGF0YQAB"
          }
        }
      },
      "response": "EXCEPTION",
      "success": false,
      "error": "Exception: Connection lost"
    },
    {
      "request": {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
          "name": "hex_to_ascii",
          "arguments": {
            "hex_data": "C8E2E3E240"
          }
        }
      },
      "response": "EXCEPTION",
      "success": false,
      "error": "Exception: Connection lost"
    },
    {
      "request": {
        "jsonrpc": "2.0",
        "id": 5,
        "method": "tools/call",
        "params": {
          "name": "ascii_to_hex",
          "arguments": {
            "ascii_data": "PURE3270"
          }
        }
      },
      "response": "EXCEPTION",
      "success": false,
      "error": "Exception: Connection lost"
    }
  ],
  "Terminal Debugger": [
    {
      "request": {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
          "name": "get_terminal_models",
          "arguments": {}
        }
      },
      "response": "EXCEPTION",
      "success": false,
      "error": "Exception: Connection lost"
    },
    {
      "request": {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
          "name": "analyze_terminal_state",
          "arguments": {
            "screen_buffer": "SGVsbG8gVE4zMjcwAAAA",
            "attribute_buffer": "AAAAAAAAAAAAAAAA",
            "cursor_row": 0,
            "cursor_col": 5,
            "connected": true,
            "tn3270_mode": true,
            "tn3270e_mode": false
          }
        }
      },
      "response": "EXCEPTION",
      "success": false,
      "error": "Exception: Connection lost"
    },
    {
      "request": {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
          "name": "extract_fields",
          "arguments": {
            "screen_buffer": "SGVsbG8gVE4zMjcwAAAA",
            "attribute_buffer": "AAAAAAAAAAAAAAAA"
          }
        }
      },
      "response": "EXCEPTION",
      "success": false,
      "error": "Exception: Connection lost"
    },
    {
      "request": {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
          "name": "validate_screen_format",
          "arguments": {
            "screen_data": "Line 1\nLine 2\nLine 3",
            "rows": 3,
            "cols": 6
          }
        }
      },
      "response": "EXCEPTION",
      "success": false,
      "error": "Exception: Connection lost"
    },
    {
      "request": {
        "jsonrpc": "2.0",
        "id": 5,
        "method": "tools/call",
        "params": {
          "name": "format_screen_display",
          "arguments": {
            "screen_data": "Line 1\nLine 2\nLine 3",
            "rows": 3,
            "cols": 6
          }
        }
      },
      "response": "EXCEPTION",
      "success": false,
      "error": "Exception: Connection lost"
    },
    {
      "request": {
        "jsonrpc": "2.0",
        "id": 6,
        "method": "tools/call",
        "params": {
          "name": "get_field_at_position",
          "arguments": {
            "screen_buffer": "SGVsbG8gVE4zMjcwAAAA",
            "attribute_buffer": "AAAAAAAAAAAAAAAA",
            "row": 0,
            "col": 0
          }
        }
      },
      "response": "EXCEPTION",
      "success": false,
      "error": "Exception: Connection lost"
    }
  ],
  "Connection Tester": [
    {
      "request": {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
          "name": "test_connectivity",
          "arguments": {
            "host": "127.0.0.1",
            "port": 80,
            "timeout": 2.0
          }
        }
      },
      "response": "EXCEPTION",
      "success": false,
      "error": "Exception: Connection lost"
    },
    {
      "request": {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
          "name": "test_ssl_connectivity",
          "arguments": {
            "host": "127.0.0.1",
            "port": 443,
            "timeout": 2.0
          }
        }
      },
      "response": "EXCEPTION",
      "success": false,
      "error": "Exception: Connection lost"
    },
    {
      "request": {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
          "name": "test_basic_negotiation",
          "arguments": {
            "host": "127.0.0.1",
            "port": 23,
            "timeout": 1.0
          }
        }
      },
      "response": "EXCEPTION",
      "success": false,
      "error": "Exception: Connection lost"
    },
    {
      "request": {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
          "name": "test_tn3270e_negotiation",
          "arguments": {
            "host": "127.0.0.1",
            "port": 23,
            "timeout": 1.0
          }
        }
      },
      "response": "EXCEPTION",
      "success": false,
      "error": "Exception: Connection lost"
    },
    {
      "request": {
        "jsonrpc": "2.0",
        "id": 5,
        "method": "tools/call",
        "params": {
          "name": "test_performance",
          "arguments": {
            "host": "127.0.0.1",
            "port": 80,
            "count": 2,
            "timeout": 1.0
          }
        }
      },
      "response": "EXCEPTION",
      "success": false,
      "error": "Exception: Connection lost"
    },
    {
      "request": {
        "jsonrpc": "2.0",
        "id": 6,
        "method": "tools/call",
        "params": {
          "name": "test_port_range",
          "arguments": {
            "host": "127.0.0.1",
            "start_port": 80,
            "end_port": 82,
            "timeout": 1.0
          }
        }
      },
      "response": "EXCEPTION",
      "success": false,
      "error": "Exception: Connection lost"
    }
  ]
}
