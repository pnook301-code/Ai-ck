---
name: web-search
description: >
  Multi-engine web search and content extraction for AI agents.
  Search across Google, Bing, DuckDuckGo, Brave, SearXNG and more.
  Fetch and extract clean markdown from any URL. Use when the user needs
  to find information from the web, search multiple engines, extract
  content from websites, or gather real-time data from the internet.
---

# Web Search Skill

Multi-engine web search + content extraction for CK-NEXUS agents.

## Quick Start

```python
from skills.web_search.engine import web_search, web_fetch

# Search across multiple engines
results = web_search("AI agent frameworks", max_results=5)

# Fetch and extract a single URL
content = web_fetch("https://example.com/article")
```

## Search Engines

| Engine | API Key | Notes |
|--------|---------|-------|
| DuckDuckGo | None | Default, keyless |
| Brave Search | Optional | Higher quality |
| Bing | Optional | Microsoft API |
| SearXNG | Self-hosted | Most flexible |
| Google | Required | Best results |

## Features

- **Parallel search**: All engines fire simultaneously
- **Result fusion**: Dedup + RRF (Reciprocal Rank Fusion)
- **Content extraction**: Clean markdown from any URL
- **Caching**: HTTP cache with TTL support
- **Rate limiting**: Built-in per-engine limits

## Configuration

Set in `config.json`:
```json
{
  "web_search": {
    "engines": ["duckduckgo", "brave", "bing"],
    "max_results": 10,
    "timeout": 15,
    "cache_ttl": 3600
  }
}
```

## CLI Usage

```bash
python3 skills/web-search/engine.py search "query"
python3 skills/web-search/engine.py fetch "https://example.com"
```

## Output Format

```json
{
  "query": "AI frameworks",
  "results": [
    {
      "title": "Result Title",
      "url": "https://...",
      "snippet": "Brief description...",
      "engine": "duckduckgo",
      "score": 0.95
    }
  ],
  "total": 5,
  "engines_used": ["duckduckgo", "brave"]
}
```
