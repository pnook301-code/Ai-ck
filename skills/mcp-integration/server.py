#!/usr/bin/env python3
"""
MCP Integration - Model Context Protocol server and client
For CK-NEXUS agent system
"""

import json
import asyncio
from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass, field


@dataclass
class MCPTool:
    """MCP Tool definition."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable = field(repr=False)


@dataclass
class MCPResource:
    """MCP Resource definition."""
    uri: str
    name: str
    description: str
    mime_type: str = "text/plain"
    handler: Callable = field(repr=False)


class MCPServer:
    """MCP Server implementation for CK-NEXUS."""
    
    def __init__(self, name: str, version: str = "0.1.0"):
        self.name = name
        self.version = version
        self.tools: Dict[str, MCPTool] = {}
        self.resources: Dict[str, MCPResource] = {}
        self.prompts: Dict[str, Dict] = {}
    
    def tool(self, name: str, description: str = "", schema: Dict = None):
        """Decorator to register a tool."""
        def decorator(func):
            self.tools[name] = MCPTool(
                name=name,
                description=description or func.__doc__ or "",
                input_schema=schema or {},
                handler=func
            )
            return func
        return decorator
    
    def add_tool(self, name: str, handler: Callable, description: str = "", schema: Dict = None):
        """Add a tool programmatically."""
        self.tools[name] = MCPTool(
            name=name,
            description=description,
            input_schema=schema or {},
            handler=handler
        )
    
    def resource(self, uri: str, name: str = "", description: str = "", mime_type: str = "text/plain"):
        """Decorator to register a resource."""
        def decorator(func):
            self.resources[uri] = MCPResource(
                uri=uri,
                name=name or uri,
                description=description or "",
                mime_type=mime_type,
                handler=func
            )
            return func
        return decorator
    
    def add_resource(self, uri: str, handler: Callable, name: str = "", description: str = ""):
        """Add a resource programmatically."""
        self.resources[uri] = MCPResource(
            uri=uri,
            name=name or uri,
            description=description,
            handler=handler
        )
    
    def list_tools(self) -> List[Dict]:
        """List all registered tools."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "inputSchema": t.input_schema
            }
            for t in self.tools.values()
        ]
    
    def list_resources(self) -> List[Dict]:
        """List all registered resources."""
        return [
            {
                "uri": r.uri,
                "name": r.name,
                "description": r.description,
                "mimeType": r.mime_type
            }
            for r in self.resources.values()
        ]
    
    async def call_tool(self, name: str, arguments: Dict) -> Any:
        """Call a registered tool."""
        if name not in self.tools:
            raise ValueError(f"Tool '{name}' not found")
        
        tool = self.tools[name]
        result = tool.handler(**arguments)
        
        if asyncio.iscoroutine(result):
            return await result
        return result
    
    async def read_resource(self, uri: str) -> Any:
        """Read a registered resource."""
        if uri not in self.resources:
            raise ValueError(f"Resource '{uri}' not found")
        
        resource = self.resources[uri]
        result = resource.handler()
        
        if asyncio.iscoroutine(result):
            return await result
        return result
    
    def to_dict(self) -> Dict:
        """Export server definition."""
        return {
            "name": self.name,
            "version": self.version,
            "tools": self.list_tools(),
            "resources": self.list_resources(),
            "prompts": list(self.prompts.keys())
        }


class MCPClient:
    """MCP Client for connecting to MCP servers."""
    
    def __init__(self, server_url: str = None):
        self.server_url = server_url
        self.tools = []
        self.resources = []
    
    async def connect(self):
        """Connect to MCP server and discover capabilities."""
        if not self.server_url:
            return
        
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.server_url}/tools")
                if resp.status_code == 200:
                    self.tools = resp.json().get("tools", [])
                
                resp = await client.get(f"{self.server_url}/resources")
                if resp.status_code == 200:
                    self.resources = resp.json().get("resources", [])
        except Exception as e:
            print(f"Connection error: {e}")
    
    async def list_tools(self) -> List[Dict]:
        """List available tools."""
        return self.tools
    
    async def call_tool(self, name: str, arguments: Dict) -> Any:
        """Call a tool on the server."""
        if not self.server_url:
            raise ValueError("Not connected to server")
        
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.server_url}/tools/{name}",
                json=arguments
            )
            if resp.status_code == 200:
                return resp.json()
            else:
                raise ValueError(f"Tool call failed: {resp.text}")
    
    async def read_resource(self, uri: str) -> Any:
        """Read a resource from the server."""
        if not self.server_url:
            raise ValueError("Not connected to server")
        
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.server_url}/resources/{uri}")
            if resp.status_code == 200:
                return resp.json()
            else:
                raise ValueError(f"Resource read failed: {resp.text}")


def create_server(name: str = "ck-nexus", version: str = "0.1.0") -> MCPServer:
    """Create a new MCP server instance."""
    return MCPServer(name, version)


if __name__ == "__main__":
    server = create_server()
    
    @server.tool("hello", "Say hello to someone")
    def hello(name: str) -> str:
        return f"Hello, {name}!"
    
    @server.resource("status", "System Status")
    def status():
        return {"status": "online", "version": "0.1.0"}
    
    print(json.dumps(server.to_dict(), indent=2))
