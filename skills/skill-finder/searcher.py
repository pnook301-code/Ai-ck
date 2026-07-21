#!/usr/bin/env python3
"""
Skill Finder - Search and discover agent skills
Searches CK-NEXUS local + remote registries
"""

import json
import os
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import httpx
except ImportError:
    httpx = None


class SkillSearcher:
    """Search agent skills across local and remote sources."""
    
    def __init__(self, skills_dir=None, config=None):
        self.skills_dir = skills_dir or Path.home() / ".ck-nexus" / "skills"
        self.config = config or {}
        self.cache_dir = Path.home() / ".ck-nexus" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def search(self, query, limit=10, sources=None):
        """Search skills across all sources."""
        sources = sources or ["local", "clawhub", "skillnet"]
        all_results = []
        
        with ThreadPoolExecutor(max_workers=len(sources)) as executor:
            futures = {
                executor.submit(self._search_source, source, query, limit): source
                for source in sources
            }
            for future in as_completed(futures):
                try:
                    results = future.result()
                    all_results.extend(results)
                except Exception as e:
                    print(f"Source {futures[future]} failed: {e}")
        
        return self._rank_results(all_results, query)[:limit]
    
    def _search_source(self, source, query, limit):
        """Search a specific source."""
        if source == "local":
            return self._search_local(query, limit)
        elif source == "clawhub":
            return self._search_clawhub(query, limit)
        elif source == "skillnet":
            return self._search_skillnet(query, limit)
        return []
    
    def _search_local(self, query, limit):
        """Search local skill files."""
        results = []
        if not self.skills_dir.exists():
            return results
        
        query_lower = query.lower()
        for skill_dir in self.skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                continue
            
            try:
                content = skill_file.read_text()
                score = self._score_skill(query_lower, skill_dir.name, content)
                if score > 0:
                    meta = self._parse_frontmatter(content)
                    results.append({
                        "name": meta.get("name", skill_dir.name),
                        "description": meta.get("description", ""),
                        "path": str(skill_dir),
                        "source": "local",
                        "score": score
                    })
            except Exception:
                continue
        
        return sorted(results, key=lambda x: -x["score"])[:limit]
    
    def _search_clawhub(self, query, limit):
        """Search ClawHub registry (free API)."""
        results = []
        if not httpx:
            return results
        
        try:
            url = f"https://clawhub.ai/api/search?q={query}&limit={limit}"
            with httpx.Client(timeout=10) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("skills", []):
                        results.append({
                            "name": item.get("name", ""),
                            "description": item.get("description", ""),
                            "url": item.get("url", ""),
                            "source": "clawhub",
                            "score": item.get("relevance", 0.5)
                        })
        except Exception as e:
            print(f"ClawHub error: {e}")
        
        return results
    
    def _search_skillnet(self, query, limit):
        """Search SkillNet API."""
        results = []
        if not httpx:
            return results
        
        try:
            url = f"http://api-skillnet.openkg.cn/v1/search?q={query}&mode=vector&limit={limit}"
            with httpx.Client(timeout=10) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("results", []):
                        results.append({
                            "name": item.get("name", ""),
                            "description": item.get("description", ""),
                            "url": item.get("repo_url", ""),
                            "source": "skillnet",
                            "score": item.get("score", 0.5)
                        })
        except Exception as e:
            print(f"SkillNet error: {e}")
        
        return results
    
    def _score_skill(self, query, name, content):
        """Score a skill based on relevance to query."""
        score = 0
        name_lower = name.lower()
        content_lower = content.lower()
        
        if query in name_lower:
            score += 10
        
        for word in query.split():
            if word in name_lower:
                score += 5
            if word in content_lower:
                score += 1
        
        if "description:" in content:
            desc_start = content.find("description:")
            desc_section = content[desc_start:desc_start+200].lower()
            if query in desc_section:
                score += 3
        
        return score
    
    def _parse_frontmatter(self, content):
        """Parse YAML frontmatter from SKILL.md."""
        meta = {}
        if content.startswith("---"):
            end = content.find("---", 3)
            if end != -1:
                frontmatter = content[3:end]
                for line in frontmatter.strip().split("\n"):
                    if ":" in line:
                        key, val = line.split(":", 1)
                        meta[key.strip()] = val.strip().strip('"')
        return meta
    
    def _rank_results(self, results, query):
        """Rank and deduplicate results."""
        seen = set()
        unique = []
        for r in results:
            key = r.get("name", r.get("url", ""))
            if key not in seen:
                seen.add(key)
                unique.append(r)
        return sorted(unique, key=lambda x: -x.get("score", 0))
    
    def install(self, skill_name, target_dir=None):
        """Install a skill from local or remote."""
        target = target_dir or self.skills_dir
        
        local_result = self._search_local(skill_name, 1)
        if local_result:
            return {"status": "already_installed", "path": local_result[0]["path"]}
        
        remote = self._search_clawhub(skill_name, 1)
        if remote:
            return {"status": "found_remote", "skill": remote[0]}
        
        return {"status": "not_found", "name": skill_name}
    
    def audit(self, skill_path):
        """Audit a skill for security issues."""
        issues = []
        skill_dir = Path(skill_path)
        
        if not skill_dir.exists():
            return {"error": "Path not found"}
        
        for f in skill_dir.rglob("*"):
            if f.is_file():
                try:
                    content = f.read_text()
                    
                    if "subprocess" in content or "os.system" in content:
                        issues.append({"file": str(f), "issue": "Uses subprocess/system calls", "severity": "high"})
                    
                    if "eval(" in content or "exec(" in content:
                        issues.append({"file": str(f), "issue": "Uses eval/exec", "severity": "high"})
                    
                    if "import requests" in content and "verify=False" in content:
                        issues.append({"file": str(f), "issue": "Disables SSL verification", "severity": "medium"})
                    
                    if "password" in content.lower() or "secret" in content.lower():
                        issues.append({"file": str(f), "issue": "Contains sensitive keywords", "severity": "low"})
                
                except Exception:
                    continue
        
        return {
            "path": str(skill_path),
            "issues": issues,
            "grade": "A" if not issues else ("B" if len(issues) < 3 else ("C" if len(issues) < 5 else "F"))
        }


def search_skills(query, limit=10, sources=None):
    """Convenience function to search skills."""
    searcher = SkillSearcher()
    return searcher.search(query, limit, sources)


def install_skill(name, target_dir=None):
    """Convenience function to install a skill."""
    searcher = SkillSearcher()
    return searcher.install(name, target_dir)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: searcher.py <search|install|audit> [query|name|path]")
        sys.exit(1)
    
    action = sys.argv[1]
    arg = sys.argv[2] if len(sys.argv) > 2 else ""
    
    if action == "search":
        results = search_skills(arg)
        print(json.dumps(results, indent=2, ensure_ascii=False))
    elif action == "install":
        result = install_skill(arg)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif action == "audit":
        searcher = SkillSearcher()
        result = searcher.audit(arg)
        print(json.dumps(result, indent=2, ensure_ascii=False))
