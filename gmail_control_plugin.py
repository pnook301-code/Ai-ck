#!/usr/bin/env python3
"""
CK-NEXUS v1.3 - Gmail Control Plugin
Email scanner for VPS credentials + task ingestion
"""

import os
import time
import json
import sqlite3
import imaplib
import email
import re
from typing import Dict, Any, Optional


class NexusGmailControlPlugin:
    """Gmail Controller - Read emails, extract VPS creds, process tasks"""

    def __init__(self, sd_path: str = "/workspace/ck-nexus"):
        self.sd_path = sd_path
        self.db_path = os.path.join(sd_path, "nexus_system_sd.db")
        self.email_config_path = "/root/.ck-nexus/email_config.json"

    def execute_secure_inbox_login(self) -> Optional[imaplib.IMAP4_SSL]:
        """ล็อกอินเข้า Gmail ผ่าน IMAP"""
        try:
            with open(self.email_config_path) as f:
                cfg = json.load(f)

            if cfg["app_password"] == "YOUR_GMAIL_APP_PASSWORD_HERE":
                return None

            mail = imaplib.IMAP4_SSL(cfg["imap_server"])
            mail.login(cfg["email_address"], cfg["app_password"])
            return mail
        except:
            return None

    def process_and_clean_inbox_autonomous(self) -> Dict[str, Any]:
        """อ่านอีเมล ดึงข้อมูล VPS จัดการงานอัตโนมัติ"""
        mail = self.execute_secure_inbox_login()
        if not mail:
            return {"status": "AWAITING_APP_PASSWORD", "tasks": 0}

        try:
            mail.select("inbox")

            # Search for VPS provider emails
            status, data = mail.search(None, '(OR OR OR OR OR OR SENDER "kamatera" SENDER "vpsserver" SENDER "gratisvps" SENDER "solusvm" SENDER "oracle" SENDER "google" SENDER "amazon")')
            mail_ids = data[0].split()

            extracted = 0
            for m_id in mail_ids[-15:]:
                try:
                    _, msg_data = mail.fetch(m_id, '(RFC822)')
                    msg = email.message_from_bytes(msg_data[0][1])

                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() in ["text/plain", "text/html"]:
                                body += part.get_payload(decode=True).decode(errors='ignore')
                    else:
                        body = msg.get_payload(decode=True).decode(errors='ignore')

                    ip_match = re.search(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', body)
                    pass_match = re.search(
                        r'(?:password|pass|root pass|รหัสผ่าน)\s*[:=]\s*([A-Za-z0-9@#$%^&*_\-!+]+)',
                        body, re.IGNORECASE
                    )

                    if ip_match and pass_match:
                        vps_ip = ip_match.group(0)
                        vps_pass = pass_match.group(1).strip()

                        provider = "Unknown"
                        body_lower = body.lower()
                        for p in ["kamatera", "vpsserver", "gratisvps", "solusvm", "oracle", "google"]:
                            if p in body_lower:
                                provider = p.replace("vpsserver", "VPSServer").replace("gratisvps", "GratisVPS").replace("solusvm", "SolusVM").title()
                                break

                        with sqlite3.connect(self.db_path) as conn:
                            existing = conn.execute(
                                "SELECT id FROM autonomous_vps_servers WHERE provider_name LIKE ?",
                                (f"%{provider}%",)
                            ).fetchone()

                            if existing:
                                conn.execute("""
                                    UPDATE autonomous_vps_servers
                                    SET notes = ?, status = 'ACTIVE_WITH_CREDENTIALS'
                                    WHERE provider_name LIKE ?
                                """, (f"SSH_IP:{vps_ip}|SSH_PASSWORD:{vps_pass}", f"%{provider}%"))
                            else:
                                conn.execute("""
                                    INSERT INTO autonomous_vps_servers
                                    (provider_name, provider_url, signup_url, username, assigned_email,
                                     status, trial_days, features, registered_date, notes)
                                    VALUES (?, ?, ?, ?, ?, 'ACTIVE_WITH_CREDENTIALS', 30, 'Email-extracted', ?, ?)
                                """, (
                                    provider, f"https://{provider.lower()}.com", "",
                                    "nexus_cloud_operator", "arrtyuio42@gmail.com",
                                    time.strftime("%Y-%m-%d %H:%M:%S"),
                                    f"SSH_IP:{vps_ip}|SSH_PASSWORD:{vps_pass}"
                                ))
                            conn.commit()
                        extracted += 1
                        print(f"✅ [{provider}] {vps_ip}")
                except:
                    continue

            mail.logout()
            return {"status": "SUCCESS", "tasks": extracted}

        except Exception as e:
            return {"status": "ERROR", "reason": str(e)[:80], "tasks": 0}

    def check_for_commands(self) -> list:
        """ตรวจสอบอีเมลคำสั่งงาน"""
        mail = self.execute_secure_inbox_login()
        if not mail:
            return []

        commands = []
        try:
            mail.select("inbox")
            status, data = mail.search(None, '(UNSEEN SUBJECT "nexus-cmd")')
            mail_ids = data[0].split()

            for m_id in mail_ids[-5:]:
                try:
                    _, msg_data = mail.fetch(m_id, '(RFC822)')
                    msg = email.message_from_bytes(msg_data[0][1])
                    subject = msg.get("Subject", "")
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body += part.get_payload(decode=True).decode(errors='ignore')
                    else:
                        body = msg.get_payload(decode=True).decode(errors='ignore')

                    commands.append({"subject": subject, "body": body[:200]})
                    mail.store(m_id, '+FLAGS', '\\Seen')
                except:
                    continue

            mail.logout()
        except:
            pass

        return commands


if __name__ == "__main__":
    plugin = NexusGmailControlPlugin()
    result = plugin.process_and_clean_inbox_autonomous()
    print(f"Gmail Plugin: {result}")
