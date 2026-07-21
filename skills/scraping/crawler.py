#!/usr/bin/env python3
"""
Web Scraper - Advanced crawling with anti-bot capabilities
Supports: fast, hybrid, stealth modes
"""

import json
import random
import time
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

try:
    import httpx
except ImportError:
    httpx = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]


class StealthConfig:
    """Configuration for stealth scraping."""
    
    def __init__(
        self,
        use_proxy: bool = False,
        proxy_url: str = None,
        rotate_ua: bool = True,
        headless: bool = True,
        delay: float = 1.0
    ):
        self.use_proxy = use_proxy
        self.proxy_url = proxy_url
        self.rotate_ua = rotate_ua
        self.headless = headless
        self.delay = delay
    
    def get_proxy(self):
        if self.use_proxy and self.proxy_url:
            return self.proxy_url
        return None


class WebScraper:
    """Advanced web scraper with anti-bot capabilities."""
    
    def __init__(self, config: StealthConfig = None):
        self.config = config or StealthConfig()
        self.visited = set()
        self.delay = self.config.delay
    
    def scrape(self, url: str, mode: str = "fast") -> Dict:
        """Scrape a single URL."""
        if mode == "fast":
            return self._scrape_fast(url)
        elif mode == "hybrid":
            return self._scrape_hybrid(url)
        elif mode == "stealth":
            return self._scrape_stealth(url)
        else:
            return {"error": f"Unknown mode: {mode}"}
    
    def _scrape_fast(self, url: str) -> Dict:
        """Fast HTTP-only scraping."""
        if not httpx:
            return {"error": "httpx not installed"}
        
        try:
            headers = self._get_headers()
            proxy = self.config.get_proxy()
            
            with httpx.Client(
                timeout=15,
                proxy=proxy,
                follow_redirects=True
            ) as client:
                resp = client.get(url, headers=headers)
                
                if resp.status_code == 200:
                    return {
                        "url": url,
                        "status": resp.status_code,
                        "content": self._extract_content(resp.text),
                        "title": self._extract_title(resp.text),
                        "mode": "fast"
                    }
                else:
                    return {"url": url, "status": resp.status_code, "error": f"HTTP {resp.status_code}"}
        
        except Exception as e:
            return {"url": url, "error": str(e)}
    
    def _scrape_hybrid(self, url: str) -> Dict:
        """Hybrid scraping with fallback."""
        result = self._scrape_fast(url)
        
        if result.get("error") or len(result.get("content", "")) < 100:
            result = self._scrape_with_js(url)
        
        return result
    
    def _scrape_with_js(self, url: str) -> Dict:
        """JavaScript-rendered scraping using Playwright."""
        try:
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.config.headless)
                page = browser.new_page()
                page.set_extra_http_headers(self._get_headers())
                
                page.goto(url, wait_until="networkidle")
                content = page.content()
                title = page.title()
                browser.close()
                
                return {
                    "url": url,
                    "status": 200,
                    "content": self._extract_content(content),
                    "title": title,
                    "mode": "hybrid-js"
                }
        
        except ImportError:
            return {"url": url, "error": "playwright not installed"}
        except Exception as e:
            return {"url": url, "error": str(e)}
    
    def _scrape_stealth(self, url: str) -> Dict:
        """Stealth scraping with anti-detection."""
        time.sleep(self.delay * random.uniform(0.5, 1.5))
        
        result = self._scrape_hybrid(url)
        result["mode"] = "stealth"
        
        return result
    
    def crawl(self, start_url: str, max_pages: int = 100, depth: int = 2) -> List[Dict]:
        """Crawl multiple pages from a starting URL."""
        results = []
        queue = [(start_url, 0)]
        self.visited = set()
        
        while queue and len(results) < max_pages:
            url, current_depth = queue.pop(0)
            
            if url in self.visited or current_depth > depth:
                continue
            
            self.visited.add(url)
            result = self.scrape(url, mode="fast")
            results.append(result)
            
            if result.get("content") and current_depth < depth:
                links = self._extract_links(result["content"], url)
                for link in links[:10]:
                    if link not in self.visited:
                        queue.append((link, current_depth + 1))
            
            time.sleep(self.delay)
        
        return results
    
    def _get_headers(self) -> Dict:
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }
        
        if self.config.rotate_ua:
            headers["User-Agent"] = random.choice(USER_AGENTS)
        else:
            headers["User-Agent"] = USER_AGENTS[0]
        
        return headers
    
    def _extract_content(self, html: str) -> str:
        if BeautifulSoup:
            soup = BeautifulSoup(html, 'html.parser')
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                tag.decompose()
            return soup.get_text(separator='\n', strip=True)
        return html
    
    def _extract_title(self, html: str) -> str:
        if BeautifulSoup:
            soup = BeautifulSoup(html, 'html.parser')
            title = soup.find('title')
            return title.get_text(strip=True) if title else ""
        return ""
    
    def _extract_links(self, content: str, base_url: str) -> List[str]:
        links = []
        if BeautifulSoup:
            soup = BeautifulSoup(content, 'html.parser')
            for a in soup.find_all('a', href=True):
                href = a['href']
                full_url = urljoin(base_url, href)
                if urlparse(full_url).netloc == urlparse(base_url).netloc:
                    links.append(full_url)
        return links


def scrape_url(url: str, mode: str = "fast", config: StealthConfig = None) -> Dict:
    """Convenience function to scrape a URL."""
    scraper = WebScraper(config)
    return scraper.scrape(url, mode)


def crawl_site(start_url: str, max_pages: int = 100, depth: int = 2) -> List[Dict]:
    """Convenience function to crawl a site."""
    scraper = WebScraper()
    return scraper.crawl(start_url, max_pages, depth)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: crawler.py <url> [mode]")
        sys.exit(1)
    
    url = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "fast"
    
    result = scrape_url(url, mode)
    print(json.dumps(result, indent=2, ensure_ascii=False))
