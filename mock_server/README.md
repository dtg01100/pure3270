# TN3270 Mock Server

This directory provides an asyncio-based TN3270/TN3270E mock server for offline protocol scenario testing. Use it to validate pure3270’s protocol handling without mainframe access.

## Usage

- The main server implementation is in `tn3270_mock_server.py`.
- Scenario scripts are in `scenarios/` and simulate various protocol interactions and edge cases.

## Scenarios

- `negotiation_success.py`: Simulates successful negotiation of device type and options.
- `negotiation_failure.py`: Simulates negotiation failure due to unsupported device type.
- `invalid_device_type.py`: Simulates client requesting an unknown device type.
- `structured_field.py`: Simulates structured field exchange.
- `printer_session.py`: Simulates printer device negotiation and data flow.
- `ssl_handshake.py`: Simulates secure session negotiation (mocked, not real SSL).
- `malformed_data.py`: Simulates client sending invalid or corrupted protocol bytes.

## Running a Scenario

```bash
python mock_server/scenarios/negotiation_success.py
```

Replace the script name with any scenario to run it. Each script starts the mock server, simulates the scenario, and stops the server.

## Integration

You can integrate these scenarios into your test suite for automated offline validation. Each scenario can be imported and run as an async test.

## Extending

Add new scenarios to `scenarios/` as needed. Ensure each script:
- Imports `TN3270MockServer`
- Defines an `async def run() -> None`
- Uses `asyncio.run(run())` for execution

## License
MIT
