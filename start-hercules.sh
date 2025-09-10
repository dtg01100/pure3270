#!/bin/bash
# Start Hercules with proper configuration

echo "Starting Hercules TN3270 server..."
echo "Configuration: /etc/hercules/hercules.cnf"

# Start Hercules in the background
hercules -f /etc/hercules/hercules.cnf &

# Wait for initialization
sleep 5

# Keep container running
tail -f /dev/null