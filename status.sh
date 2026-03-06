#!/bin/bash

# Change to the directory where the script is located
cd "$(dirname "$0")"

echo "=== Price Tracker Status ==="

# Check monitor service
MONITOR_PID=$(pgrep -f "monitor.py --twice-daily-est")
if [ -n "$MONITOR_PID" ]; then
    echo "✅ Monitor service: RUNNING (PID: $MONITOR_PID)"
else
    echo "❌ Monitor service: STOPPED"
fi

# Check dashboard service
DASHBOARD_PID=$(pgrep -f "dashboard.py")
if [ -n "$DASHBOARD_PID" ]; then
    echo "✅ Dashboard service: RUNNING (PID: $DASHBOARD_PID)"
    # Check if port is listening
    if lsof -i :5002 > /dev/null 2>&1; then
        echo "✅ Dashboard port (5002): LISTENING"
        echo "🌐 Access at: http://localhost:5002"
    else
        echo "⚠️  Dashboard port (5002): NOT RESPONDING"
    fi
else
    echo "❌ Dashboard service: STOPPED"
fi

echo ""
echo "Log files:"
echo "- Monitor: $(pwd)/monitor.log"
echo "- Dashboard: $(pwd)/dashboard.log"
echo "- Errors: $(pwd)/monitor.error.log"