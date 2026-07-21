---
name: scraping
description: >
  Web scraping with anti-bot bypass, stealth browsing, and structured
  data extraction. Handle JavaScript-rendered pages, CAPTCHAs, and
  bot protection. Use when the user needs to scrape websites, extract
  structured data, bypass bot detection, or crawl large sites.
---

# Web Scraping Skill

Advanced web scraping with anti-bot capabilities.

## Quick Start

```python
from skills.scraping.crawler import scrape_url, crawl_site

# Scrape a single page
data = scrape_url("https://example.com/product", mode="hybrid")

# Crawl an entire site
pages = crawl_site("https://example.com", max_pages=100)
```

## Crawl Modes

| Mode | Speed | JS Support | Bot Bypass |
|------|-------|------------|------------|
| `fast` | ⚡⚡⚡ | No | No |
| `hybrid` | ⚡⚡ | Yes | Basic |
| `stealth` | ⚡ | Yes | Advanced |

## Features

### Anti-Bot
- User-Agent rotation
- Proxy support (SOCKS5/HTTP)
- Cookie persistence
- Header randomization
- Browser fingerprinting

### Content Extraction
- HTML to Markdown
- Table extraction
- Code block detection
- Image metadata
- JSON-LD / OpenGraph

### JavaScript Rendering
- Playwright integration
- SPA support
- Dynamic content loading
- Infinite scroll handling

## Extraction Output

```json
{
  "url": "https://example.com",
  "title": "Page Title",
  "content": "Clean markdown content...",
  "tables": [...],
  "images": [...],
  "metadata": {
    "description": "...",
    "keywords": [...],
    "og:image": "..."
  }
}
```

## Anti-Detection

```python
from skills.scraping.stealth import StealthConfig

config = StealthConfig(
    use_proxy=True,
    proxy_url="socks5://user:pass@host:port",
    rotate_ua=True,
    headless=False,  # Visible browser
    fingerprint="chrome-windows"
)

data = scrape_url("https://protected-site.com", config=config)
```

## Ethical Scraping

- Respect `robots.txt`
- Rate limit requests (1-2/sec default)
- Identify with proper User-Agent
- No credential harvesting
- Cache results to reduce load

## Dependencies

```bash
pip install httpx beautifulsoup4 selectolax trafilatura
pip install playwright  # For JS rendering
python -m playwright install chromium
```
