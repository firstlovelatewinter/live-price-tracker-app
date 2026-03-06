#!/bin/bash
set -e

# Change to the directory where the script is located
cd "$(dirname "$0")"

# Source the environment variables
if [ -f .env ]; then
  export $(cat .env | sed 's/#.*//g' | xargs)
fi

# Activate the virtual environment
source venv/bin/activate

# Start the monitor service in the background
nohup python3 monitor.py --twice-daily-est > monitor.log 2>&1 &

# Start the dashboard service in the background
nohup python3 dashboard.py > dashboard.log 2>&1 &

# Save the PIDs so we can stop them later
echo $! > dashboard.pid
echo "$(pgrep -f "monitor.py --twice-daily-est")" > monitor.pid

echo "Price tracker services started!"
echo "Monitor PID: $(cat monitor.pid)"
echo "Dashboard PID: $(cat dashboard.pid)"
echo "Dashboard available at: http://localhost:5002"