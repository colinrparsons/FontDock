#!/usr/bin/env python3
"""
Brain MCP Server - Windsurf Integration
Runs on Windsurf machine (192.168.0.91), connects to Brain (192.168.0.32:8000)
"""

import asyncio
import json
import sys
import os
from typing import Any
import httpx

# Read brain API URL from environment, default to brain server
BRAIN_API = os.environ.get("BRAIN_API", "http://192.168.0.49:8000")

class BrainMCPServer:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        print(f"Brain MCP Server connected to: {BRAIN_API}", file=sys.stderr)
    
    async def handle_request(self, request: dict) -> dict:
        method = request.get("method")
        
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {},
                        "resources": {}
                    },
                    "serverInfo": {
                        "name": "brain-mcp",
                        "version": "1.0.0"
                    }
                }
            }
        
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "tools": [
                        {
                            "name": "save_memory",
                            "description": "Save a memory to Colin's brain",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": {"type": "string", "description": "The memory text to save"},
                                    "project": {"type": "string", "description": "Project/category"},
                                    "type": {"type": "string", "description": "Memory type (knowledge, note, strategy, etc)"}
                                },
                                "required": ["text"]
                            }
                        },
                        {
                            "name": "search_memories",
                            "description": "Search memories semantically using natural language",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {"type": "string", "description": "Search query (e.g., 'trading strategies', 'dashboard setup')"},
                                    "limit": {"type": "integer", "description": "Max results to return", "default": 5}
                                },
                                "required": ["query"]
                            }
                        },
                        {
                            "name": "get_recent_memories",
                            "description": "Get most recent memories",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "limit": {"type": "integer", "description": "Number to retrieve", "default": 10}
                                }
                            }
                        }
                    ]
                }
            }
        
        elif method == "tools/call":
            params = request.get("params", {})
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if tool_name == "save_memory":
                result = await self.save_memory(arguments)
            elif tool_name == "search_memories":
                result = await self.search_memories(arguments)
            elif tool_name == "get_recent_memories":
                result = await self.get_recent_memories(arguments)
            else:
                result = {"error": f"Unknown tool: {tool_name}"}
            
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
                }
            }
        
        elif method == "resources/list":
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "resources": [
                        {
                            "uri": "brain://dashboard",
                            "name": "Brain Dashboard",
                            "description": f"Web dashboard at {BRAIN_API}/",
                            "mimeType": "text/html"
                        },
                        {
                            "uri": "brain://stats",
                            "name": "Brain Stats",
                            "description": "Memory statistics"
                        }
                    ]
                }
            }
        
        return {"jsonrpc": "2.0", "id": request.get("id"), "result": {}}
    
    async def save_memory(self, args: dict) -> dict:
        try:
            response = await self.client.post(
                f"{BRAIN_API}/save_memory",
                json={
                    "text": args.get("text"),
                    "project": args.get("project", "windsurf"),
                    "type": args.get("type", "knowledge")
                }
            )
            return response.json()
        except Exception as e:
            return {"error": str(e), "brain_api": BRAIN_API}
    
    async def search_memories(self, args: dict) -> dict:
        try:
            response = await self.client.post(
                f"{BRAIN_API}/search_memory",
                json={
                    "query": args.get("query"),
                    "limit": args.get("limit", 5)
                }
            )
            return response.json()
        except Exception as e:
            return {"error": str(e), "brain_api": BRAIN_API}
    
    async def get_recent_memories(self, args: dict) -> dict:
        try:
            limit = args.get("limit", 10)
            response = await self.client.get(f"{BRAIN_API}/get_memories?limit={limit}")
            return response.json()
        except Exception as e:
            return {"error": str(e), "brain_api": BRAIN_API}
    
    async def run(self):
        while True:
            try:
                line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
                if not line:
                    break
                
                request = json.loads(line.strip())
                response = await self.handle_request(request)
                
                print(json.dumps(response), flush=True)
            except json.JSONDecodeError:
                continue
            except Exception as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32603, "message": str(e)}
                }
                print(json.dumps(error_response), flush=True)

if __name__ == "__main__":
    server = BrainMCPServer()
    asyncio.run(server.run())
