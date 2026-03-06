#!/bin/bash

# Change to the directory where the script is located
cd "$(dirname "$0")"

# Stop monitor service
if [ -f monitor.pid ]; then
    MONITOR_PID=$(cat monitor.pid)
    if ps -p $MONITOR_PID > /dev/null 2>&1; then
        kill $MONITOR_PID
        echo "Monitor service stopped (PID: $MONITOR_PID)"
    else
        echo "Monitor service not running"
    fi
    rm -f monitor.pid
else
    pkill -f "monitor.py --twice-daily-est" 2>/dev/null
    echo "Monitor service stopped"
fi

# Stop dashboard service
if [ -f dashboard.pid ]; then
    DASHBOARD_PID=$(cat dashboard.pid)
    if ps -p $DASHBOARD_PID > /dev/null 2>&1; then
        kill $DASHBOARD_PID
        echo "Dashboard service stopped (PID: $DASHBOARD_PID)"
    else
        echo "Dashboard service not running"
    fi
    rm -f dashboard.pid
else
    pkill -f "dashboard.py" 2>/dev/null
    echo "Dashboard service stopped"
fi

echo "All services stopped."