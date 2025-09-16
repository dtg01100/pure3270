#!/bin/bash
# Script to run the real system test with common configurations

echo "=== Pure3270 Real System Test ==="
echo "Choose a test configuration:"
echo "1) Connect to a standard TN3270 system (port 23) - Direct pure3270"
echo "2) Connect to a secure TN3270 system (port 992, SSL) - Direct pure3270"
echo "3) Custom connection - Direct pure3270"
echo "4) Connect using .env file credentials - Direct pure3270"
echo "5) Connect to a standard TN3270 system (port 23) - p3270 with patching"
echo "6) Connect to a secure TN3270 system (port 992, SSL) - p3270 with patching"
echo "7) Custom connection - p3270 with patching"
echo "8) Connect using .env file credentials - p3270 with patching"
echo ""

read -p "Enter your choice (1-8): " choice

# Check if python-dotenv is installed, if not install it
if ! python -c "import dotenv" &> /dev/null; then
    echo "Installing python-dotenv..."
    pip install python-dotenv
fi

case $choice in
    1)
        read -p "Enter hostname: " host
        read -p "Username (optional): " user
        read -s -p "Password (optional): " password
        echo ""
        if [ -n "$user" ] && [ -n "$password" ]; then
            python test_real_system.py --host "$host" --user "$user" --password "$password"
        else
            python test_real_system.py --host "$host"
        fi
        ;;
    2)
        read -p "Enter hostname: " host
        read -p "Username (optional): " user
        read -s -p "Password (optional): " password
        echo ""
        if [ -n "$user" ] && [ -n "$password" ]; then
            python test_real_system.py --host "$host" --port 992 --ssl --user "$user" --password "$password"
        else
            python test_real_system.py --host "$host" --port 992 --ssl
        fi
        ;;
    3)
        read -p "Enter hostname: " host
        read -p "Port (default 23): " port
        read -p "Use SSL? (y/N): " ssl
        read -p "Username (optional): " user
        read -s -p "Password (optional): " password
        echo ""

        # Set defaults
        port=${port:-23}
        ssl_flag=""
        if [[ "$ssl" =~ ^[Yy]$ ]]; then
            ssl_flag="--ssl"
        fi

        if [ -n "$user" ] && [ -n "$password" ]; then
            python test_real_system.py --host "$host" --port "$port" $ssl_flag --user "$user" --password "$password"
        else
            python test_real_system.py --host "$host" --port "$port" $ssl_flag
        fi
        ;;
    4)
        # Use .env file credentials
        echo "Connecting using credentials from .env file..."
        python test_real_system.py
        ;;
    5)
        read -p "Enter hostname: " host
        read -p "Username (optional): " user
        read -s -p "Password (optional): " password
        echo ""
        if [ -n "$user" ] && [ -n "$password" ]; then
            python test_p3270_patching.py --host "$host" --user "$user" --password "$password"
        else
            python test_p3270_patching.py --host "$host"
        fi
        ;;
    6)
        read -p "Enter hostname: " host
        read -p "Username (optional): " user
        read -s -p "Password (optional): " password
        echo ""
        if [ -n "$user" ] && [ -n "$password" ]; then
            python test_p3270_patching.py --host "$host" --port 992 --ssl --user "$user" --password "$password"
        else
            python test_p3270_patching.py --host "$host" --port 992 --ssl
        fi
        ;;
    7)
        read -p "Enter hostname: " host
        read -p "Port (default 23): " port
        read -p "Use SSL? (y/N): " ssl
        read -p "Username (optional): " user
        read -s -p "Password (optional): " password
        echo ""

        # Set defaults
        port=${port:-23}
        ssl_flag=""
        if [[ "$ssl" =~ ^[Yy]$ ]]; then
            ssl_flag="--ssl"
        fi

        if [ -n "$user" ] && [ -n "$password" ]; then
            python test_p3270_patching.py --host "$host" --port "$port" $ssl_flag --user "$user" --password "$password"
        else
            python test_p3270_patching.py --host "$host" --port "$port" $ssl_flag
        fi
        ;;
    8)
        # Use .env file credentials
        echo "Connecting using credentials from .env file..."
        python test_p3270_patching.py
        ;;
    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac
