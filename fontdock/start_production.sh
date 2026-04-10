#!/bin/bash

# FontDock Production Start Script
# Use this to test production settings locally

export SERVER_HOST=0.0.0.0
export SERVER_PORT=8000
export RELOAD=false

echo "Starting FontDock server in production mode..."
echo "Server will be accessible at:"
echo "  http://localhost:8000"
echo "  http://$(hostname -I | awk '{print $1}' 2>/dev/null || echo 'YOUR_IP'):8000"
echo ""
echo "Press Ctrl+C to stop"
echo ""

python3 run.py
