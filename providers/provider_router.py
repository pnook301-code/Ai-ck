"""Multi-Provider Router - OpenAI, Groq, OpenRouter, Ollama, LINE"""
import urllib.request
import urllib.error
import json
import os

class ProviderRouter:
    def __init__(self, config_path=None):
        self.providers = {}
        self.priority = ["openai", "groq", "openrouter", "ollama"]
        self.current_provider = None
        self.config = self._load_config(config_path)
        self.line = None
        self._init_line()

    def _load_config(self, path):
        config = {
            "openai": {
                "key": os.environ.get("OPENAI_API_KEY", ""),
                "model": "gpt-4o-mini",
                "base_url": "https://api.openai.com/v1"
            },
            "groq": {
                "key": os.environ.get("GROQ_API_KEY", ""),
                "model": "llama-3.3-70b-versatile",
                "base_url": "https://api.groq.com/openai/v1"
            },
            "openrouter": {
                "key": os.environ.get("OPENROUTER_API_KEY", ""),
                "model": "mistralai/mistral-7b-instruct",
                "base_url": "https://openrouter.ai/api/v1"
            },
            "ollama": {
                "key": "",
                "model": "llama3.1:8b",
                "base_url": "http://localhost:11434/v1"
            },
            "line": {
                "channel_access_token": "",
                "enabled": False
            }
        }
        if path and os.path.exists(path):
            try:
                with open(path) as f:
                    user_config = json.load(f)
                    config.update(user_config)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load config: {e}")
                pass
        return config

    def _init_line(self):
        line_cfg = self.config.get("line", {})
        if line_cfg.get("channel_access_token") and line_cfg.get("enabled", True):
            from providers.line_provider import LineProvider
            self.line = LineProvider(line_cfg["channel_access_token"])

    def _call_openai_compatible(self, provider_name, messages, temperature, max_tokens):
        cfg = self.config.get(provider_name, {})
        if not cfg.get("key") and provider_name != "ollama":
            raise ValueError(f"No API key for {provider_name}")

        payload = json.dumps({
            "model": cfg["model"],
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }).encode("utf-8")

        headers = {"Content-Type": "application/json", "User-Agent": "CK-NEXUS/0.1.0"}
        if cfg.get("key"):
            headers["Authorization"] = f"Bearer {cfg['key']}"

        req = urllib.request.Request(
            f"{cfg['base_url']}/chat/completions",
            data=payload, headers=headers
        )

        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
            return {
                "content": data["choices"][0]["message"]["content"],
                "tokens": data.get("usage", {}).get("total_tokens", 0),
                "model": data.get("model", cfg["model"]),
                "provider": provider_name,
                "finish": data["choices"][0].get("finish_reason", "stop")
            }

    def chat(self, messages, temperature=0.7, max_tokens=2000, prefer=None):
        errors = []
        providers = [prefer] + self.priority if prefer else self.priority
        seen = set()

        for prov in providers:
            if prov in seen or prov not in self.config:
                continue
            seen.add(prov)
            try:
                result = self._call_openai_compatible(prov, messages, temperature, max_tokens)
                self.current_provider = prov
                return result
            except Exception as e:
                errors.append(f"{prov}: {e}")
                continue

        raise Exception(f"All providers failed:\n" + "\n".join(errors))

    def test_all(self):
        results = {}
        for prov in self.priority:
            try:
                result = self._call_openai_compatible(prov, [{"role": "user", "content": "Say OK"}], 0.5, 5)
                results[prov] = {"status": "OK", "model": result["model"], "provider": result["provider"]}
            except Exception as e:
                results[prov] = {"status": "FAILED", "error": str(e)[:100]}

        # Test LINE
        if self.line:
            ok, msg = self.line.test_connection()
            results["line"] = {"status": "OK" if ok else "FAILED", "error": msg if not ok else None, "info": msg if ok else None}

        return results

    def get_status(self):
        status = {}
        for prov in self.priority:
            cfg = self.config.get(prov, {})
            status[prov] = {
                "configured": bool(cfg.get("key")) or prov == "ollama",
                "model": cfg.get("model", "?"),
                "current": prov == self.current_provider
            }
        # LINE status
        if self.line:
            line_status = self.line.get_status()
            status["line"] = {
                "configured": line_status["configured"],
                "token_preview": line_status.get("token_preview", "none"),
                "type": "messaging_api"
            }
        return status

    # LINE shortcuts
    def line_push(self, user_id, text):
        if not self.line:
            return {"ok": False, "error": "LINE not configured"}
        return self.line.push_message(user_id, text)

    def line_reply(self, text):
        if not self.line:
            return {"ok": False, "error": "LINE not configured"}
        return self.line.reply_message(text)

    def line_notify(self, message):
        if not self.line:
            return {"ok": False, "error": "LINE not configured"}
        return self.line.send_notification(message)
