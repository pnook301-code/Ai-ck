---
name: mcp-integration
description: >
  Model Context Protocol (MCP) server and client integration.
  Connect to MCP servers, expose tools, resources, and prompts.
  Use when the user needs to set up MCP servers, connect to external
  tools via MCP, create MCP-compatible APIs, or integrate with the
  MCP ecosystem.
---

# MCP Integration

Model Context Protocol server and client for CK-NEXUS.

## Quick Start

```python
from skills.mcp_integration.server import MCPServer
from skills.mcp_integration.client import MCPClient

# Create MCP server
server = MCPServer("ck-nexus")
server.add_tool("search", search_handler)
server.add_resource("memory", memory_resource)

# Connect to MCP server
client = MCPClient("http://localhost:8080")
tools = client.list_tools()
result = client.call_tool("search", {"query": "hello"})
```

## MCP Protocol (2026-07-28)

### Core Concepts

- **Stateless**: No sticky sessions needed
- **HTTP-based**: Standard REST + SSE
- **Header routing**: `Mcp-Method` and `Mcp-Name`
- **Caching**: `ttlMs` and `cacheScope` in responses

### Primitives

| Primitive | Purpose |
|-----------|---------|
| Tools | Actions the agent can call |
| Resources | Data the agent can read |
| Prompts | Pre-built conversation templates |
| Skills | Multi-step workflows (extension) |

### MCP Apps

Server-rendered UI widgets in sandboxed iframes:
- Forms and pickers
- Charts and dashboards
- Live data displays

## Server Setup

```python
server = MCPServer(
    name="ck-nexus",
    version="0.1.0",
    transport="streamable-http",  # or "stdio"
    host="127.0.0.1",
    port=8080
)

# Add tools
@server.tool("chat")
async def chat_tool(query: str) -> str:
    return await engine.chat(query)

# Add resources
@server.resource("memory")
async def memory_resource() -> dict:
    return engine.memory.get_stats()

server.run()
```

## Client Usage

```python
client = MCPClient("http://localhost:8080")

# Discover tools
tools = await client.list_tools()

# Call a tool
result = await client.call_tool("chat", {
    "query": "Hello"
})

# Read a resource
data = await client.read_resource("memory")
```

## Skills Extension (Experimental)

Serve skills through MCP:

```python
@server.resource("skill://index.json")
async def skill_index():
    return {
        "skills": [
            {"name": "web-search", "uri": "skill://web-search/SKILL.md"},
            {"name": "skill-finder", "uri": "skill://skill-finder/SKILL.md"}
        ]
    }

@server.resource("skill://web-search/SKILL.md")
async def web_search_skill():
    return open("skills/web-search/SKILL.md").read()
```

## Security

- OAuth2 for authentication
- Scoped access tokens
- Rate limiting per client
- Input validation on all tools
