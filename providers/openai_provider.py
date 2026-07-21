"""OpenAI API Provider - uses only stdlib urllib"""
import urllib.request
import urllib.error
import json
import os

class OpenAIProvider:
    def __init__(self, api_key=None, model="gpt-4o-mini"):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.model = model
        self.base_url = "https://api.openai.com/v1"
        self.last_tokens = 0

    def chat(self, messages, temperature=0.7, max_tokens=2000):
        if not self.api_key:
            raise ValueError("No OpenAI API key configured")

        payload = json.dumps({
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode())
                self.last_tokens = data.get("usage", {}).get("total_tokens", 0)
                return {
                    "content": data["choices"][0]["message"]["content"],
                    "tokens": self.last_tokens,
                    "model": data.get("model", self.model),
                    "finish": data["choices"][0].get("finish_reason", "stop")
                }
        except urllib.error.HTTPError as e:
            body = e.read().decode() if e.fp else str(e)
            raise Exception(f"OpenAI API error {e.code}: {body}")

    def test_connection(self):
        try:
            result = self.chat([{"role": "user", "content": "Say 'OK'"}], max_tokens=5)
            return True, result["content"]
        except Exception as e:
            return False, str(e)

    def list_models(self):
        req = urllib.request.Request(
            f"{self.base_url}/models",
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                return [m["id"] for m in data.get("data", []) if "gpt" in m["id"]]
        except Exception as e:
            return [f"Error: {e}"]
