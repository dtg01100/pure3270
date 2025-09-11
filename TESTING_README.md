# Real System Test Scripts

These scripts are for testing connections to real TN3270 systems and are not tracked by git.

## Files

1. `test_real_system.py` - Python script to connect to TN3270 systems using direct pure3270
2. `test_p3270_patching.py` - Python script to connect to TN3270 systems using p3270 with pure3270 patching
3. `run_test.sh` - Interactive shell script to configure and run tests

## Usage

### Direct Python Script Usage

```bash
# Direct pure3270 approach
python test_real_system.py [--host <hostname>] [--port <port>] [--ssl] [--user <username>] [--password <password>] [--debug]

# p3270 with patching approach
python test_p3270_patching.py [--host <hostname>] [--port <port>] [--ssl] [--user <username>] [--password <password>] [--debug]
```

Examples:
```bash
# Connect to a standard TN3270 system
python test_real_system.py --host mainframe.example.com

# Connect to a secure TN3270 system
python test_real_system.py --host mainframe.example.com --port 992 --ssl

# Connect with login credentials
python test_real_system.py --host mainframe.example.com --user myuser --password mypass

# Use credentials from .env file
python test_real_system.py

# Using p3270 with patching
python test_p3270_patching.py --host mainframe.example.com
```

### Using Environment Variables

The scripts can load credentials from environment variables or a `.env` file:
- `TN3270_HOST` - Hostname to connect to
- `TN3270_USERNAME` - Username for login
- `TN3270_PASSWORD` - Password for login

### Interactive Shell Script

```bash
./run_test.sh
```

This will present a menu with common connection options:
1. Standard TN3270 connections - Direct pure3270
2. Secure TN3270 connections (SSL/TLS) - Direct pure3270
3. Custom connection configurations - Direct pure3270
4. Connect using .env file credentials - Direct pure3270
5. Standard TN3270 connections - p3270 with patching
6. Secure TN3270 connections (SSL/TLS) - p3270 with patching
7. Custom connection configurations - p3270 with patching
8. Connect using .env file credentials - p3270 with patching

## Installation

The test scripts require the `python-dotenv` package for loading environment variables from `.env` files:

```bash
pip install python-dotenv
```

Or install the testing dependencies:

```bash
pip install -e .[testing]
```

## Notes

- These scripts are for testing purposes only
- Passwords entered via command line may be visible in process lists
- For production use, consider using more secure credential handling
- The `.env` file is not tracked by git for security reasons