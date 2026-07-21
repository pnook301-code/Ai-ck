---
name: skill-finder
description: >
  Search, discover, and install agent skills from multiple registries.
  Find the right SKILL.md for any task across 50,000+ community skills.
  Use when the user needs to find skills, install capabilities, search
  for agent tools, discover MCP servers, or explore the skill ecosystem.
---

# Skill Finder

Search and discover agent skills from CK-NEXUS and community registries.

## Quick Start

```python
from skills.skill_finder.searcher import search_skills, install_skill

# Search skills by natural language
results = search_skills("web scraping python", limit=10)

# Install a skill
install_skill("web-search", target="~/.ck-nexus/skills/")
```

## Sources

| Source | Skills | Access |
|--------|--------|--------|
| CK-NEXUS Local | Built-in | Always available |
| ClawHub | 4,000+ | API (free) |
| SkillNet | 500,000+ | REST API |
| GitHub Topics | 15,000+ | Search API |
| SkillsMP | 387 | GitHub search |

## Features

- **Semantic search**: Natural language queries
- **Quality grading**: A-F scores for each skill
- **Security audit**: Detect dangerous patterns
- **Auto-install**: One-click install to any agent

## CLI Usage

```bash
python3 skills/skill-finder/searcher.py search "deploy kubernetes"
python3 skills/skill-finder/searcher.py install web-search
python3 skills/skill-finder/searcher.py audit skill-name
```

## Skill Quality Criteria

| Grade | Criteria |
|-------|----------|
| A | Well-documented, tested, no security issues |
| B | Good documentation, minor issues |
| C | Basic functionality, needs improvement |
| D | Minimal documentation, potential risks |
| F | Dangerous or broken |

## MCP Integration

Connect to remote skill registries via MCP:

```python
from skills.skill_finder.mcp_client import SkillRegistry

registry = SkillRegistry("https://registry.example.com")
skills = registry.search("react components")
```
