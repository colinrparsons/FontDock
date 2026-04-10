#!/bin/bash
# Start the Brain MCP Server
# This connects to the brain at 192.168.0.49:8000

cd "$(dirname "$0")"

# Check if brain is reachable
echo "Checking brain server at 192.168.0.49:8000..."
if curl -s http://192.168.0.49:8000/health > /dev/null 2>&1; then
    echo "Brain server is online"
else
    echo "Warning: Brain server may not be reachable at 192.168.0.49:8000"
    echo "Continuing anyway..."
fi

# Run the MCP server
python3 brain_mcp_server.py
