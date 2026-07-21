#!/usr/bin/env python3
"""
Web Search Engine - Multi-engine search for CK-NEXUS
Supports: DuckDuckGo, Brave, Bing, SearXNG
"""

import json
import hashlib
import time
from urllib.parse import quote_plus
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import httpx
except ImportError:
    httpx = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None


class SearchEngine:
    """Base class for search engines."""
    
    def __init__(self, name, api_key=None):
        self.name = name
        self.api_key = api_key
        self.timeout = 15
    
    def search(self, query, max_results=10):
        raise NotImplementedError


class DuckDuckGoEngine(SearchEngine):
    """DuckDuckGo search - no API key required."""
    
    def __init__(self):
        super().__init__("duckduckgo")
    
    def search(self, query, max_results=10):
        results = []
        try:
            url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            if httpx:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.get(url, headers=headers)
                    if resp.status_code == 200:
                        results = self._parse_html(resp.text, max_results)
        except Exception as e:
            print(f"DuckDuckGo error: {e}")
        
        return results
    
    def _parse_html(self, html, max_results):
        results = []
        if not BeautifulSoup:
            return results
        
        soup = BeautifulSoup(html, 'html.parser')
        for result in soup.select('.result')[:max_results]:
            title_el = result.select_one('.result__a')
            snippet_el = result.select_one('.result__snippet')
            url_el = result.select_one('.result__url')
            
            if title_el:
                results.append({
                    "title": title_el.get_text(strip=True),
                    "url": url_el.get_text(strip=True) if url_el else "",
                    "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                    "engine": "duckduckgo"
                })
        
        return results


class BraveEngine(SearchEngine):
    """Brave Search - optional API key."""
    
    def __init__(self, api_key=None):
        super().__init__("brave", api_key)
    
    def search(self, query, max_results=10):
        results = []
        if not self.api_key:
            return results
        
        try:
            url = f"https://api.search.brave.com/res/v1/web/search?q={quote_plus(query)}&count={max_results}"
            headers = {
                "Accept": "application/json",
                "X-Subscription-Token": self.api_key
            }
            
            if httpx:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.get(url, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        for item in data.get("web", {}).get("results", []):
                            results.append({
                                "title": item.get("title", ""),
                                "url": item.get("url", ""),
                                "snippet": item.get("description", ""),
                                "engine": "brave"
                            })
        except Exception as e:
            print(f"Brave error: {e}")
        
        return results


class BingEngine(SearchEngine):
    """Bing Search - optional API key."""
    
    def __init__(self, api_key=None):
        super().__init__("bing", api_key)
    
    def search(self, query, max_results=10):
        results = []
        if not self.api_key:
            return results
        
        try:
            url = f"https://api.bing.microsoft.com/v7.0/search?q={quote_plus(query)}&count={max_results}"
            headers = {"Ocp-Apim-Subscription-Key": self.api_key}
            
            if httpx:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.get(url, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        for item in data.get("webPages", {}).get("value", []):
                            results.append({
                                "title": item.get("name", ""),
                                "url": item.get("url", ""),
                                "snippet": item.get("snippet", ""),
                                "engine": "bing"
                            })
        except Exception as e:
            print(f"Bing error: {e}")
        
        return results


class WebSearcher:
    """Multi-engine web searcher with result fusion."""
    
    def __init__(self, config=None):
        self.config = config or {}
        self.engines = self._init_engines()
        self.cache = {}
        self.cache_ttl = self.config.get("cache_ttl", 3600)
    
    def _init_engines(self):
        engines = [DuckDuckGoEngine()]
        
        brave_key = self.config.get("brave_api_key")
        if brave_key:
            engines.append(BraveEngine(brave_key))
        
        bing_key = self.config.get("bing_api_key")
        if bing_key:
            engines.append(BingEngine(bing_key))
        
        return engines
    
    def search(self, query, max_results=10):
        """Search across all engines and fuse results."""
        cache_key = hashlib.md5(f"{query}:{max_results}".encode()).hexdigest()
        
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if time.time() - cached["time"] < self.cache_ttl:
                return cached["results"]
        
        all_results = []
        with ThreadPoolExecutor(max_workers=len(self.engines)) as executor:
            futures = {
                executor.submit(engine.search, query, max_results): engine.name
                for engine in self.engines
            }
            for future in as_completed(futures):
                try:
                    results = future.result()
                    all_results.extend(results)
                except Exception as e:
                    print(f"Engine {futures[future]} failed: {e}")
        
        fused = self._fuse_results(all_results, max_results)
        
        self.cache[cache_key] = {
            "results": fused,
            "time": time.time()
        }
        
        return fused
    
    def _fuse_results(self, results, max_results):
        """Deduplicate and rank results using RRF."""
        seen = {}
        for r in results:
            url = r.get("url", "")
            if url not in seen:
                seen[url] = {**r, "engines": [r["engine"]], "score": 0}
            else:
                if r["engine"] not in seen[url]["engines"]:
                    seen[url]["engines"].append(r["engine"])
        
        for url, r in seen.items():
            r["score"] = len(r["engines"])
        
        ranked = sorted(seen.values(), key=lambda x: -x["score"])
        return ranked[:max_results]


def web_search(query, max_results=10, config=None):
    """Convenience function for web search."""
    searcher = WebSearcher(config)
    return searcher.search(query, max_results)


def web_fetch(url, timeout=15):
    """Fetch and extract content from a URL."""
    try:
        if httpx:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    return {
                        "url": url,
                        "status": resp.status_code,
                        "content": _extract_content(resp.text),
                        "content_type": resp.headers.get("content-type", "")
                    }
    except Exception as e:
        return {"url": url, "error": str(e)}
    
    return {"url": url, "error": "httpx not installed"}


def _extract_content(html):
    """Extract clean text from HTML."""
    if BeautifulSoup:
        soup = BeautifulSoup(html, 'html.parser')
        for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
            tag.decompose()
        return soup.get_text(separator='\n', strip=True)
    return html


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: engine.py <search|fetch> <query|url>")
        sys.exit(1)
    
    action = sys.argv[1]
    query = sys.argv[2]
    
    if action == "search":
        results = web_search(query)
        print(json.dumps(results, indent=2, ensure_ascii=False))
    elif action == "fetch":
        result = web_fetch(query)
        print(json.dumps(result, indent=2, ensure_ascii=False))
