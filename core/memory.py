"""SQLite Memory System - conversations, knowledge, facts"""
import sqlite3
import json
import os
import time
from datetime import datetime

class MemoryOS:
    def __init__(self, db_path=None):
        self.db_path = db_path or os.path.expanduser("~/.ck-nexus/memory.db")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                role TEXT,
                content TEXT,
                model TEXT,
                provider TEXT,
                tokens INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE,
                value TEXT,
                category TEXT,
                confidence REAL DEFAULT 1.0,
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fact TEXT,
                category TEXT,
                confidence REAL DEFAULT 1.0,
                times_recalled INTEGER DEFAULT 0,
                last_recalled TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                description TEXT,
                content TEXT,
                enabled INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_conv_session ON conversations(session_id);
            CREATE INDEX IF NOT EXISTS idx_knowledge_key ON knowledge(key);
            CREATE INDEX IF NOT EXISTS idx_facts_category ON facts(category);
        """)
        self.conn.commit()

    # Conversation Memory
    def save_message(self, session_id, role, content, model="", provider="", tokens=0):
        self.conn.execute(
            "INSERT INTO conversations (session_id, role, content, model, provider, tokens) VALUES (?,?,?,?,?,?)",
            (session_id, role, content, model, provider, tokens)
        )
        self.conn.commit()

    def get_history(self, session_id, limit=20):
        rows = self.conn.execute(
            "SELECT * FROM conversations WHERE session_id=? ORDER BY id DESC LIMIT ?",
            (session_id, limit)
        ).fetchall()
        return [dict(r) for r in reversed(rows)]

    def get_all_sessions(self):
        rows = self.conn.execute(
            "SELECT session_id, COUNT(*) as msgs, MIN(created_at) as started, MAX(created_at) as last_msg FROM conversations GROUP BY session_id ORDER BY last_msg DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    # Knowledge Base
    def store_knowledge(self, key, value, category="general", confidence=1.0, source="user"):
        self.conn.execute(
            "INSERT OR REPLACE INTO knowledge (key, value, category, confidence, source, updated_at) VALUES (?,?,?,?,?,?)",
            (key, value, category, confidence, source, datetime.now().isoformat())
        )
        self.conn.commit()

    def recall_knowledge(self, key=None, category=None, limit=10):
        if key:
            row = self.conn.execute("SELECT * FROM knowledge WHERE key=?", (key,)).fetchone()
            return dict(row) if row else None
        elif category:
            rows = self.conn.execute("SELECT * FROM knowledge WHERE category=? ORDER BY confidence DESC LIMIT ?", (category, limit)).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM knowledge ORDER BY confidence DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    # Facts
    def add_fact(self, fact, category="general", confidence=1.0):
        self.conn.execute(
            "INSERT INTO facts (fact, category, confidence) VALUES (?,?,?)",
            (fact, category, confidence)
        )
        self.conn.commit()

    def recall_facts(self, category=None, limit=10):
        if category:
            rows = self.conn.execute("SELECT * FROM facts WHERE category=? ORDER BY confidence DESC LIMIT ?", (category, limit)).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM facts ORDER BY confidence DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    # Skills
    def save_skill(self, name, description, content):
        self.conn.execute(
            "INSERT OR REPLACE INTO skills (name, description, content) VALUES (?,?,?)",
            (name, description, content)
        )
        self.conn.commit()

    def get_skill(self, name):
        row = self.conn.execute("SELECT * FROM skills WHERE name=?", (name,)).fetchone()
        return dict(row) if row else None

    def list_skills(self):
        rows = self.conn.execute("SELECT name, description, enabled FROM skills").fetchall()
        return [dict(r) for r in rows]

    # Stats
    def get_stats(self):
        stats = {}
        stats["total_messages"] = self.conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
        stats["total_sessions"] = self.conn.execute("SELECT COUNT(DISTINCT session_id) FROM conversations").fetchone()[0]
        stats["total_knowledge"] = self.conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
        stats["total_facts"] = self.conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
        stats["total_skills"] = self.conn.execute("SELECT COUNT(*) FROM skills").fetchone()[0]
        stats["total_tokens"] = self.conn.execute("SELECT COALESCE(SUM(tokens),0) FROM conversations").fetchone()[0]
        return stats

    def close(self):
        self.conn.close()
