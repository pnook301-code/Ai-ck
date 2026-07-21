#!/usr/bin/env python3
"""
CK-NEXUS v0.6 - Auto API Key Generator
ระบบสร้าง API Key อัตโนมัติ 3 รูปแบบ
"""

import os
import sys
import json
import time
import secrets
import hashlib
import sqlite3
from pathlib import Path
from typing import Dict, Optional, List

sys.path.insert(0, os.path.dirname(__file__))


class APIKeyManager:
    """ระบบจัดการ API Key อัตโนมัติ"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = str(Path.home() / ".ck-nexus" / "api_keys.db")
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute('''CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_prefix TEXT NOT NULL,
            key_hash TEXT NOT NULL UNIQUE,
            user_email TEXT,
            user_name TEXT,
            plan TEXT DEFAULT 'free',
            rate_limit INTEGER DEFAULT 60,
            requests_today INTEGER DEFAULT 0,
            total_requests INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now')),
            last_used TEXT,
            expires_at TEXT,
            metadata TEXT DEFAULT '{}'
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS usage_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_id INTEGER,
            endpoint TEXT,
            status_code INTEGER,
            timestamp TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (key_id) REFERENCES api_keys(id)
        )''')
        conn.commit()
        conn.close()

    # ========== METHOD 1: Custom Backend ==========

    def generate_key_custom(self, user_email: str, user_name: str = "",
                            plan: str = "free", prefix: str = "sk_free") -> Dict:
        """สร้าง API Key แบบ Custom (Cryptographically Secure)"""
        raw_token = secrets.token_hex(32)
        full_key = f"{prefix}_{raw_token}"
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()

        rate_limits = {"free": 60, "pro": 600, "enterprise": 6000}
        rate_limit = rate_limits.get(plan, 60)

        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """INSERT INTO api_keys 
                   (key_prefix, key_hash, user_email, user_name, plan, rate_limit)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (prefix, key_hash, user_email, user_name, plan, rate_limit)
            )
            conn.commit()
            key_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        finally:
            conn.close()

        return {
            "status": "success",
            "api_key": full_key,
            "key_id": key_id,
            "plan": plan,
            "rate_limit": f"{rate_limit} req/min",
            "message": f"🔑 สร้าง Key สำเร็จ! แสดงแค่ครั้งเดียว 保存ไว้ด้วย"
        }

    # ========== METHOD 2: Docker/Linux Auto-Gen ==========

    def generate_key_docker(self, hostname: str = None) -> str:
        """สร้าง API Key สำหรับ Docker/Linux (auto on first boot)"""
        if hostname is None:
            hostname = os.uname().nodename

        raw_token = secrets.token_hex(32)
        key = f"docker_{hostname}_{raw_token[:16]}"
        key_hash = hashlib.sha256(key.encode()).hexdigest()

        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """INSERT INTO api_keys 
                   (key_prefix, key_hash, user_email, plan, rate_limit, metadata)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                ("docker", key_hash, f"auto@{hostname}.local", "docker", 120,
                 json.dumps({"hostname": hostname, "auto_generated": True}))
            )
            conn.commit()
        finally:
            conn.close()

        return key

    # ========== METHOD 3: Gateway-style (Stripe-ready) ==========

    def generate_key_gateway(self, customer_id: str, plan: str = "starter",
                             stripe_sub_id: str = None) -> Dict:
        """สร้าง API Key แบบ Gateway (สำหรับ Stripe/Payment integration)"""
        tier_map = {
            "starter": {"prefix": "gw_starter", "limit": 100, "price": 0},
            "growth": {"prefix": "gw_growth", "limit": 1000, "price": 29},
            "scale": {"prefix": "gw_scale", "limit": 10000, "price": 99},
            "unlimited": {"prefix": "gw_unlim", "limit": -1, "price": 299}
        }

        tier = tier_map.get(plan, tier_map["starter"])
        raw_token = secrets.token_hex(32)
        full_key = f"{tier['prefix']}_{raw_token}"
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()

        metadata = {
            "customer_id": customer_id,
            "stripe_sub_id": stripe_sub_id,
            "plan": plan,
            "price_usd": tier["price"]
        }

        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """INSERT INTO api_keys 
                   (key_prefix, key_hash, user_email, plan, rate_limit, metadata)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (tier["prefix"], key_hash, f"{customer_id}@gateway", plan,
                 tier["limit"], json.dumps(metadata))
            )
            conn.commit()
            key_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        finally:
            conn.close()

        return {
            "status": "success",
            "api_key": full_key,
            "key_id": key_id,
            "plan": plan,
            "rate_limit": f"{tier['limit']} req/min" if tier['limit'] > 0 else "unlimited",
            "price": f"${tier['price']}/mo",
            "customer_id": customer_id
        }

    # ========== Validation & Usage ==========

    def validate_key(self, api_key: str) -> Optional[Dict]:
        """ตรวจสอบ API Key"""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute(
                """SELECT id, user_email, plan, rate_limit, requests_today, 
                          total_requests, is_active, expires_at
                   FROM api_keys WHERE key_hash = ?""",
                (key_hash,)
            ).fetchone()
        finally:
            conn.close()

        if not row:
            return {"valid": False, "error": "Key not found"}

        key_id, email, plan, limit, today, total, active, expires = row

        if not active:
            return {"valid": False, "error": "Key suspended"}

        if expires:
            from datetime import datetime
            if datetime.now() > datetime.fromisoformat(expires):
                return {"valid": False, "error": "Key expired"}

        return {
            "valid": True,
            "key_id": key_id,
            "email": email,
            "plan": plan,
            "rate_limit": limit,
            "requests_today": today,
            "total_requests": total
        }

    def log_usage(self, api_key: str, endpoint: str, status_code: int):
        """บันทึกการใช้งาน"""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute(
                "SELECT id FROM api_keys WHERE key_hash = ?", (key_hash,)
            ).fetchone()
            if row:
                conn.execute(
                    "INSERT INTO usage_logs (key_id, endpoint, status_code) VALUES (?, ?, ?)",
                    (row[0], endpoint, status_code)
                )
                conn.execute(
                    """UPDATE api_keys SET requests_today = requests_today + 1,
                       total_requests = total_requests + 1, last_used = datetime('now')
                       WHERE id = ?""",
                    (row[0],)
                )
                conn.commit()
        finally:
            conn.close()

    def revoke_key(self, api_key: str) -> bool:
        """เพิกถอน API Key"""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "UPDATE api_keys SET is_active = 0 WHERE key_hash = ?", (key_hash,)
            )
            conn.commit()
            return conn.total_changes > 0
        finally:
            conn.close()

    def list_keys(self, user_email: str = None) -> List[Dict]:
        """ดูรายการ API Keys"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            if user_email:
                rows = conn.execute(
                    """SELECT id, key_prefix, user_email, user_name, plan, 
                              rate_limit, requests_today, total_requests, is_active, created_at
                       FROM api_keys WHERE user_email = ? ORDER BY created_at DESC""",
                    (user_email,)
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT id, key_prefix, user_email, user_name, plan, 
                              rate_limit, requests_today, total_requests, is_active, created_at
                       FROM api_keys ORDER BY created_at DESC"""
                ).fetchall()
        finally:
            conn.close()

        return [dict(row) for row in rows]

    def reset_daily_usage(self):
        """รีเซ็ตรายวัน (รันตอนเที่ยงคืน)"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("UPDATE api_keys SET requests_today = 0")
        conn.commit()
        conn.close()


# ========== Shell Script Generator ==========

def generate_init_script() -> str:
    """สร้าง init.sh สำหรับ Docker auto-gen"""
    return '''#!/bin/bash
# CK-NEXUS Auto API Key Generator (Docker/Linux)
# รันครั้งแรกเพื่อสร้าง .env อัตโนมัติ

ENV_FILE=".env"

if [ ! -f "$ENV_FILE" ]; then
    echo "🔧 Creating .env with auto-generated API key..."
    RANDOM_KEY=$(openssl rand -hex 32)
    cat > "$ENV_FILE" << EOF
APP_API_KEY=sk_auto_${RANDOM_KEY}
CK-NEXUS_VERSION=v0.6
DATABASE_URL=sqlite:///nexus_memory.db
HOST=127.0.0.1
PORT=8000
LOG_LEVEL=info
EOF
    echo "✅ .env created with key: sk_auto_${RANDOM_KEY:0:16}..."
else
    echo "✅ .env already exists, skipping..."
fi

# Start the application
python3 auto_system.py
'''


# ========== Test ==========

def demo():
    """สาธิตระบบ API Key Generator"""
    manager = APIKeyManager()

    print("=" * 60)
    print("🔑 CK-NEXUS Auto API Key Generator - DEMO")
    print("=" * 60)

    # Method 1: Custom
    print("\n📌 METHOD 1: Custom Backend Code")
    result1 = manager.generate_key_custom(
        user_email="arrtyuio42@gmail.com",
        user_name="CK-Owner",
        plan="pro"
    )
    print(f"   ✅ Key: {result1['api_key'][:30]}...")
    print(f"   📋 Plan: {result1['plan']} | Limit: {result1['rate_limit']}")

    # Method 2: Docker
    print("\n📌 METHOD 2: Docker/Linux Auto-Gen")
    result2 = manager.generate_key_docker()
    print(f"   ✅ Key: {result2[:30]}...")

    # Method 3: Gateway
    print("\n📌 METHOD 3: Gateway (Stripe-ready)")
    result3 = manager.generate_key_gateway(
        customer_id="cust_ck_nexus_001",
        plan="scale"
    )
    print(f"   ✅ Key: {result3['api_key'][:30]}...")
    print(f"   💰 Price: {result3['price']} | Limit: {result3['rate_limit']}")

    # Validate
    print("\n🔍 VALIDATION TEST:")
    v = manager.validate_key(result1["api_key"])
    print(f"   Valid: {v['valid']} | Plan: {v.get('plan')}")

    # List all
    print("\n📋 ALL KEYS:")
    for k in manager.list_keys():
        status = "🟢" if k["is_active"] else "🔴"
        print(f"   {status} [{k['plan']}] {k['key_prefix']}... | {k['user_email']} | {k['total_requests']} calls")

    print("\n" + "=" * 60)
    print("✅ ระบบ API Key Generator พร้อมใช้งาน!")
    print("=" * 60)


if __name__ == "__main__":
    if "--test" in sys.argv:
        demo()
    elif "--init-script" in sys.argv:
        print(generate_init_script())
    else:
        print("Usage:")
        print("  python3 api_key_generator.py --test          # สาธิตระบบ")
        print("  python3 api_key_generator.py --init-script   # สร้าง init.sh")
