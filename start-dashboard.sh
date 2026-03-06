#!/bin/bash
set -e

# Change to the directory where the script is located
cd "$(dirname "$0")"

# Activate the virtual environment
source venv/bin/activate

# Run the dashboard
python3 dashboard.py