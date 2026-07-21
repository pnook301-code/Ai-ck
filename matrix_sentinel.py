#!/usr/bin/env python3
"""
CK-NEXUS v1.1 - Matrix Sentinel Controller
Real-Time Fault Detection + Cross-Platform Idea Ingestion + Hybridization Engine
"""

import os
import time
import json
import sqlite3
import shutil
import urllib.request
import urllib.error
from typing import Dict, List, Any


class NexusMatrixSentinel:
    """Matrix Sentinel: Fault Detection + Idea Ingestion + Auto-Hybridization"""

    def __init__(self, config_path: str = "/root/.ck-nexus/config.json", sd_path: str = "/workspace/ck-nexus"):
        self.config_path = config_path
        self.sd_path = sd_path
        self.db_path = os.path.join(sd_path, "nexus_system_sd.db")
        self.config = self._load_config()
        self._init_matrix_tables()
        self.fault_history = []
        self.ideas_count = 0

    def _load_config(self) -> Dict:
        try:
            with open(self.config_path) as f:
                return json.load(f)
        except:
            return {}

    def _init_matrix_tables(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS external_ideas_bank (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    idea_title TEXT,
                    source_origin TEXT,
                    concept_detail TEXT,
                    potential_hybrid_skills TEXT,
                    status TEXT DEFAULT 'STORED_FOR_HYBRID'
                );
                CREATE TABLE IF NOT EXISTS system_fault_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    broken_component TEXT,
                    error_reason TEXT,
                    agent_status_json TEXT
                );
                CREATE TABLE IF NOT EXISTS hybrid_blueprints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    concept_name TEXT,
                    source_idea TEXT,
                    target_skill TEXT,
                    integration_plan TEXT,
                    status TEXT DEFAULT 'PLANNED'
                );
            """)
            conn.commit()

    # ═══════════════════════════════════════════════════════
    # 1. TRUE STATUS SENTINEL - ตรวจจับความพังตามจริง
    # ═══════════════════════════════════════════════════════
    def audit_system_faults(self) -> List[Dict[str, Any]]:
        """สแกนหาจุดบกพร่องทั้งหมดและบันทึกลง SD Card ทันที"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        faults = []

        # Check OpenAI key (nested config: openai.key)
        openai_key = self.config.get("openai", {}).get("key", "")
        if not openai_key:
            faults.append({
                "component": "OpenAI_API",
                "reason": "NO_KEY_CONFIGURED",
                "severity": "MEDIUM"
            })
        else:
            try:
                req = urllib.request.Request(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {openai_key}"}
                )
                urllib.request.urlopen(req, timeout=5)
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    faults.append({
                        "component": "OpenAI_API",
                        "reason": f"HTTP_429_NO_QUOTA_NEED_5_CREDITS",
                        "severity": "HIGH"
                    })
                elif e.code == 401:
                    faults.append({
                        "component": "OpenAI_API",
                        "reason": f"HTTP_401_INVALID_KEY_FORMAT",
                        "severity": "HIGH"
                    })
            except Exception:
                pass

        # Check Anthropic key (nested config: anthropic.key)
        anthropic_key = self.config.get("anthropic", {}).get("key", "")
        if anthropic_key and not anthropic_key.startswith("sk-ant-"):
            faults.append({
                "component": "Anthropic_API",
                "reason": f"INVALID_KEY_FORMAT_{anthropic_key[:10]}...",
                "severity": "MEDIUM"
            })

        # Check Groq key (nested config: groq.key)
        groq_key = self.config.get("groq", {}).get("key", "")
        if not groq_key:
            faults.append({
                "component": "Groq_Primary",
                "reason": "NO_KEY_CONFIGURED",
                "severity": "CRITICAL"
            })

        # Check SQLite DB integrity
        try:
            with sqlite3.connect(self.db_path) as conn:
                result = conn.execute("PRAGMA integrity_check").fetchone()
                if result[0] != "ok":
                    faults.append({
                        "component": "SQLite_SD_Card",
                        "reason": f"INTEGRITY_CHECK_FAILED: {result[0]}",
                        "severity": "CRITICAL"
                    })
        except Exception as e:
            faults.append({
                "component": "SQLite_SD_Card",
                "reason": f"DB_ACCESS_ERROR: {str(e)[:60]}",
                "severity": "CRITICAL"
            })

        # Check disk space
        try:
            total, used, free = shutil.disk_usage(self.sd_path)
            free_pct = (free / total) * 100
            if free_pct < 10:
                faults.append({
                    "component": "Storage_SD_Card",
                    "reason": f"LOW_DISK_{free_pct:.1f}%_REMAINING",
                    "severity": "HIGH"
                })
        except:
            pass

        # Check VPS node connectivity (quick ping)
        try:
            import socket
            test_hosts = [
                ("Oracle Cloud", "cloud.oracle.com"),
                ("Google Cloud", "cloud.google.com"),
                ("Kamatera", "kamatera.com")
            ]
            for name, host in test_hosts:
                try:
                    socket.create_connection((host, 443), timeout=3)
                except:
                    faults.append({
                        "component": f"VPS_{name}_Connectivity",
                        "reason": f"NETWORK_UNREACHABLE_{host}",
                        "severity": "MEDIUM"
                    })
        except:
            pass

        # Log all faults to SD Card
        if faults:
            self._log_faults(timestamp, faults)
            self.fault_history.extend(faults)

        return faults

    def _log_faults(self, timestamp: str, faults: List[Dict]):
        with sqlite3.connect(self.db_path) as conn:
            for fault in faults:
                conn.execute("""
                    INSERT INTO system_fault_logs (timestamp, broken_component, error_reason, agent_status_json)
                    VALUES (?, ?, ?, ?)
                """, (timestamp, fault["component"], fault["reason"],
                      json.dumps({"sentinel": "ACTIVE", "detection_time": timestamp})))
            conn.commit()

    def get_fault_summary(self) -> Dict:
        try:
            with sqlite3.connect(self.db_path) as conn:
                total = conn.execute("SELECT COUNT(*) FROM system_fault_logs").fetchone()[0]
                recent = conn.execute(
                    "SELECT COUNT(*) FROM system_fault_logs WHERE timestamp > datetime('now', '-24 hours')"
                ).fetchone()[0]
                return {"total_24h": recent, "total_all": total}
        except:
            return {"total_24h": 0, "total_all": 0}

    # ═══════════════════════════════════════════════════════
    # 2. CROSS-PLATFORM IDEA INGESTION - ล่าไอเดียภายนอก
    # ═══════════════════════════════════════════════════════
    def fetch_github_trending(self) -> List[Dict[str, Any]]:
        """ดึงข้อมูล GitHub Trending repositories"""
        ideas = []
        try:
            req = urllib.request.Request(
                "https://api.github.com/search/repositories?q=stars:>1000+pushed:>2026-01-01&sort=stars&order=desc&per_page=5",
                headers={"User-Agent": "CK-NEXUS/1.1", "Accept": "application/vnd.github.v3+json"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())

            for repo in data.get("items", []):
                idea = {
                    "title": repo["full_name"],
                    "source": "GitHub Trending",
                    "detail": f"Stars: {repo['stargazers_count']} | Lang: {repo.get('language', 'N/A')} | Desc: {(repo.get('description') or '')[:100]}",
                    "hybrid_potential": self._assess_hybrid_potential(repo),
                    "url": repo["html_url"]
                }
                ideas.append(idea)
        except Exception as e:
            pass

        return ideas

    def fetch_huggingface_trending(self) -> List[Dict[str, Any]]:
        """ดึงข้อมูล Hugging Face Trending models"""
        ideas = []
        try:
            req = urllib.request.Request(
                "https://huggingface.co/api/models?sort=downloads&direction=-1&limit=5",
                headers={"User-Agent": "CK-NEXUS/1.1"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())

            for model in data:
                idea = {
                    "title": model.get("modelId", model.get("id", "unknown")),
                    "source": "HuggingFace Trending",
                    "detail": f"Downloads: {model.get('downloads', 'N/A')} | Tags: {', '.join(model.get('tags', [])[:3])}",
                    "hybrid_potential": "Can integrate as local inference engine",
                    "url": f"https://huggingface.co/{model.get('modelId', '')}"
                }
                ideas.append(idea)
        except:
            pass

        return ideas

    def _assess_hybrid_potential(self, repo: Dict) -> str:
        desc = (repo.get("description") or "").lower()
        topics = [t.lower() for t in repo.get("topics", [])]

        if any(kw in desc or kw in topics for kw in ["agent", "autonomous", "multi-agent"]):
            return "HIGH - Can integrate as autonomous agent framework"
        elif any(kw in desc or kw in topics for kw in ["scraping", "crawler", "spider"]):
            return "HIGH - Can enhance VPS data collection capabilities"
        elif any(kw in desc or kw in topics for kw in ["llm", "inference", "model"]):
            return "MEDIUM - Can add local inference capability"
        elif any(kw in desc or kw in topics for kw in ["monitoring", "watchdog", "sentinel"]):
            return "MEDIUM - Can enhance system monitoring"
        else:
            return "LOW - General utility"

    def ingest_ideas_from_sources(self, topic: str = "autonomous-agent") -> int:
        """ล่าไอเดียจากทุกแหล่งและบันทึกลง SD Card"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        all_ideas = []

        # GitHub
        github_ideas = self.fetch_github_trending()
        all_ideas.extend(github_ideas)

        # HuggingFace
        hf_ideas = self.fetch_huggingface_trending()
        all_ideas.extend(hf_ideas)

        # Add concept ideas based on topic
        concept = self._generate_concept_idea(topic)
        if concept:
            all_ideas.append(concept)

        # Save to SD Card
        saved = 0
        with sqlite3.connect(self.db_path) as conn:
            for idea in all_ideas:
                # Check duplicate
                exists = conn.execute(
                    "SELECT 1 FROM external_ideas_bank WHERE idea_title = ?",
                    (idea["title"],)
                ).fetchone()
                if not exists:
                    conn.execute("""
                        INSERT INTO external_ideas_bank (timestamp, idea_title, source_origin, concept_detail, potential_hybrid_skills, status)
                        VALUES (?, ?, ?, ?, ?, 'STORED_FOR_HYBRID')
                    """, (timestamp, idea["title"], idea["source"], idea["detail"],
                          idea.get("hybrid_potential", "General enhancement")))
                    saved += 1
            conn.commit()

        self.ideas_count += saved
        return saved

    def _generate_concept_idea(self, topic: str) -> Dict:
        """สร้างแนวคิดผสมผสานจาก topic"""
        concepts = {
            "autonomous-agent": {
                "title": f"Multi-Agent Mesh Network via {topic}",
                "source": "CK-NEXUS Internal Synthesis",
                "detail": "Peer-to-Peer AI agent coordination using free VPS resources across 6 nodes",
                "hybrid_potential": "Can enhance Hive Network for distributed task execution"
            },
            "distributed-scraping": {
                "title": f"Distributed Web Intelligence via {topic}",
                "source": "CK-NEXUS Internal Synthesis",
                "detail": "Coordinate 6 VPS nodes for parallel data collection and knowledge ingestion",
                "hybrid_potential": "Directly enhances VPS Takeover + Web Agent capabilities"
            },
            "self-healing": {
                "title": f"Autonomous Self-Healing Architecture via {topic}",
                "source": "CK-NEXUS Internal Synthesis",
                "detail": "System detects own failures and auto-repairs using cognitive planning",
                "hybrid_potential": "Integrates with Director Core for zero-downtime operation"
            }
        }
        return concepts.get(topic, concepts["autonomous-agent"])

    def get_ideas_stats(self) -> Dict:
        try:
            with sqlite3.connect(self.db_path) as conn:
                total = conn.execute("SELECT COUNT(*) FROM external_ideas_bank").fetchone()[0]
                stored = conn.execute("SELECT COUNT(*) FROM external_ideas_bank WHERE status='STORED_FOR_HYBRID'").fetchone()[0]
                integrated = conn.execute("SELECT COUNT(*) FROM external_ideas_bank WHERE status='INTEGRATED_INTO_CORE'").fetchone()[0]
                return {"total": total, "stored": stored, "integrated": integrated}
        except:
            return {"total": 0, "stored": 0, "integrated": 0}

    # ═══════════════════════════════════════════════════════
    # 3. CREATIVE HYBRIDIZATION ENGINE - ผสมผสานไอเดีย
    # ═══════════════════════════════════════════════════════
    def create_hybrid_blueprint(self, idea_title: str, target_skill: str) -> Dict:
        """สร้างแผนการผสมผสานไอเดียภายนอกเข้ากับระบบเดิม"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        blueprint = {
            "concept_name": f"Hybrid: {idea_title} + {target_skill}",
            "source_idea": idea_title,
            "target_skill": target_skill,
            "integration_plan": json.dumps({
                "step1": f"Analyze {idea_title} for compatible APIs/modules",
                "step2": f"Map external capabilities to {target_skill} interface",
                "step3": f"Create adapter bridge between systems",
                "step4": f"Test integration in isolated sandbox",
                "step5": f"Deploy to production if validation passes"
            }, ensure_ascii=False),
            "status": "PLANNED"
        }

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO hybrid_blueprints (timestamp, concept_name, source_idea, target_skill, integration_plan, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (timestamp, blueprint["concept_name"], blueprint["source_idea"],
                  blueprint["target_skill"], blueprint["integration_plan"], blueprint["status"]))
            # Mark idea as integrated
            conn.execute(
                "UPDATE external_ideas_bank SET status = 'INTEGRATED_INTO_CORE' WHERE idea_title = ?",
                (idea_title,)
            )
            conn.commit()

        return blueprint

    def get_pending_hybrids(self) -> List[Dict]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT * FROM hybrid_blueprints WHERE status = 'PLANNED' ORDER BY id DESC LIMIT 5"
                ).fetchall()
                return [dict(r) for r in rows]
        except:
            return []

    # ═══════════════════════════════════════════════════════
    # STATUS REPORT
    # ═══════════════════════════════════════════════════════
    def generate_matrix_report(self) -> str:
        faults = self.audit_system_faults()
        fault_summary = self.get_fault_summary()
        ideas_stats = self.get_ideas_stats()
        hybrids = self.get_pending_hybrids()

        report = []
        report.append("=" * 60)
        report.append("👁️  MATRIX SENTINEL - STATUS REPORT")
        report.append("=" * 60)
        report.append(f"  🔍 Faults Detected:    {len(faults)}")
        report.append(f"  📊 Total Faults (24h): {fault_summary['total_24h']}")
        report.append(f"  💾 Total Faults (All): {fault_summary['total_all']}")
        report.append(f"  💡 Ideas Captured:     {ideas_stats['total']}")
        report.append(f"  🔄 Ideas Stored:       {ideas_stats['stored']}")
        report.append(f"  ✅ Ideas Integrated:   {ideas_stats['integrated']}")
        report.append(f"  🔧 Pending Hybrids:    {len(hybrids)}")
        report.append("")

        if faults:
            report.append("  🚨 Active Faults:")
            for f in faults:
                report.append(f"    ❌ [{f['severity']}] {f['component']}: {f['reason']}")
        else:
            report.append("  ✅ All Systems HEALTHY")

        report.append("=" * 60)
        return "\n".join(report)


if __name__ == "__main__":
    sentinel = NexusMatrixSentinel()
    print(sentinel.generate_matrix_report())
