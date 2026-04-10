#!/bin/bash
# Restart FontDock server script

cd "$(dirname "$0")/.."

# Create logs directory if it doesn't exist
mkdir -p logs

echo "Stopping any existing server..."
pkill -9 -f "uvicorn" 2>/dev/null
sleep 2

echo "Starting server..."
nohup python run.py > logs/server.log 2>&1 &
sleep 3

echo "Checking status..."
if curl -s http://localhost:9998/health > /dev/null 2>&1; then
    echo "Server is running on http://localhost:9998"
else
    echo "Server may still be starting..."
fi
