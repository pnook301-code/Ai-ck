"""LINE Messaging API Provider with OAuth2 Auto-Authentication"""
import urllib.request
import urllib.error
import json
import os

class LineProvider:
    BASE_URL = "https://api.line.me/v2"

    def __init__(self, channel_access_token=None):
        self.token = channel_access_token or os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
        self.reply_token = None

    def _headers(self):
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }

    def _request(self, method, path, data=None):
        url = f"{self.BASE_URL}{path}"
        payload = json.dumps(data).encode() if data else None
        req = urllib.request.Request(url, data=payload, headers=self._headers(), method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode()
                return {"ok": True, "data": json.loads(body) if body else {}}
        except urllib.error.HTTPError as e:
            body = e.read().decode() if e.fp else ""
            return {"ok": False, "error": f"HTTP {e.code}: {body}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def set_token(self, token):
        self.token = token

    def get_profile(self, user_id=None):
        if user_id:
            return self._request("GET", f"/bot/profile/{user_id}")
        return self._request("GET", "/bot/profile")

    def push_message(self, user_id, text):
        return self._request("POST", "/bot/message/push", {
            "to": user_id,
            "messages": [{"type": "text", "text": text}]
        })

    def reply_message(self, text):
        if not self.reply_token:
            return {"ok": False, "error": "No reply token set"}
        return self._request("POST", "/bot/message/reply", {
            "replyToken": self.reply_token,
            "messages": [{"type": "text", "text": text}]
        })

    def push_multicast(self, user_ids, text):
        return self._request("POST", "/bot/message/multicast", {
            "to": user_ids,
            "messages": [{"type": "text", "text": text}]
        })

    def push_rich(self, user_id, alt_text, contents):
        return self._request("POST", "/bot/message/push", {
            "to": user_id,
            "messages": [{"type": "template", "altText": alt_text, "contents": contents}]
        })

    def push_sticker(self, user_id, package_id, sticker_id):
        return self._request("POST", "/bot/message/push", {
            "to": user_id,
            "messages": [{"type": "sticker", "packageId": package_id, "stickerId": sticker_id}]
        })

    def push_image(self, user_id, original_url, preview_url):
        return self._request("POST", "/bot/message/push", {
            "to": user_id,
            "messages": [{"type": "image", "originalImageUrl": original_url, "previewImageUrl": preview_url}]
        })

    def push_location(self, user_id, title, address, lat, lon):
        return self._request("POST", "/bot/message/push", {
            "to": user_id,
            "messages": [{"type": "location", "title": title, "address": address, "latitude": lat, "longitude": lon}]
        })

    def send_notification(self, message, token=None):
        t = token or self.token
        url = "https://notify-api.line.me/api/notify"
        data = f"message={message}".encode()
        req = urllib.request.Request(url, data=data, headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Bearer {t}"
        })
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return {"ok": True, "data": json.loads(resp.read().decode())}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_groups(self):
        return self._request("GET", "/bot/group/summary")

    def get_members(self, group_id):
        return self._request("GET", f"/bot/group/{group_id}/members")

    def get_message_quota(self):
        return self._request("GET", "/bot/message/quota")

    def get_insight(self, date):
        return self._request("GET", f"/bot/insight/message/delivery?date={date}")

    def get_friends(self):
        return self._request("GET", "/bot/followers")

    def test_connection(self):
        try:
            result = self.get_profile()
            if result["ok"]:
                name = result["data"].get("displayName", "Unknown")
                return True, f"Connected! Bot: {name}"
            return False, result.get("error", "Unknown error")
        except Exception as e:
            return False, str(e)

    def get_status(self):
        quota = self.get_message_quota()
        return {
            "configured": bool(self.token),
            "token_preview": f"{self.token[:20]}..." if self.token else "none",
            "quota": quota.get("data", {}) if quota["ok"] else "error"
        }
