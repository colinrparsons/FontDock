#!/bin/bash

# FontDock Server Startup Script
# This script starts the FontDock server with proper logging

cd "$(dirname "$0")"
cd ..

echo "========================================="
echo "Starting FontDock Server"
echo "========================================="
echo ""

# Activate virtual environment
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
elif [ -d "../venv" ]; then
    echo "Activating virtual environment..."
    source ../venv/bin/activate
else
    echo "WARNING: No virtual environment found!"
    echo "Please create one with: python3 -m venv venv"
    echo ""
fi

cd fontdock

echo "Server URL: http://localhost:9998"
echo "Web UI: http://localhost:9998/ui/login"
echo ""
echo "Press Ctrl+C to stop the server"
echo "========================================="
echo ""

# Start the server with uvicorn and show all logs
python -m uvicorn app.main:app --host 0.0.0.0 --port 9998 --reload --log-level debug
