"""CK-NEXUS Main Engine - ties everything together"""
import os
import sys
import json
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from providers.provider_router import ProviderRouter
from core.memory import MemoryOS
from core.command_bus import CommandBus, EventBus
from core.plugin_manager import PluginManager
from core.line_auth import LineAuthManager
from core.oauth_server import OAuthServer
from core.vector_memory import get_vector_memory
from core.feedback_integration import FeedbackIntegration

class NexusEngine:
    def __init__(self, config_dir=None):
        self.config_dir = config_dir or os.path.expanduser("~/.ck-nexus")
        os.makedirs(self.config_dir, exist_ok=True)

        self.router = ProviderRouter(os.path.join(self.config_dir, "config.json"))
        self.memory = MemoryOS(os.path.join(self.config_dir, "memory.db"))
        self.commands = CommandBus()
        self.plugins = PluginManager(os.path.join(self.config_dir, "plugins"))
        self.session_id = f"session_{int(time.time())}"
        self.line_auth = LineAuthManager(os.path.join(self.config_dir, "credentials"))
        self.oauth_server = None

        self.system_prompt = """You are CK-NEXUS, an AI operating system assistant.
You are helpful, concise, and proactive.
You have access to memory, plugins, and multiple AI providers.
Current time: {time}
Always be direct and helpful. Respond in the same language the user uses."""

        self.commands.register("chat", self._cmd_chat)
        self.commands.register("ask", self._cmd_chat)
        self.commands.register("remember", self._cmd_remember)
        self.commands.register("recall", self._cmd_recall)
        self.commands.register("learn", self._cmd_learn)
        self.commands.register("fact", self._cmd_fact)
        self.commands.register("plugin", self._cmd_plugin)
        self.commands.register("router", self._cmd_router)
        self.commands.register("history", self._cmd_history)
        self.commands.register("clear", self._cmd_clear)
        self.commands.register("export", self._cmd_export)
        self.commands.register("new", self._cmd_new_session)
        self.commands.register("sessions", self._cmd_sessions)
        self.commands.register("stats", self._cmd_stats)
        self.commands.register("test", self._cmd_test)
        self.commands.register("line", self._cmd_line)
        self.commands.register("send", self._cmd_line_send)
        self.commands.register("notify", self._cmd_line_notify)
        self.commands.register("rate", self._cmd_rate)

        # Vector Memory integration
        self.vector_memory = get_vector_memory()

        # Feedback Loop
        self.feedback = FeedbackIntegration()

    def _build_messages(self, user_input, recall_limit=5):
        system = self.system_prompt.format(time=datetime.now().isoformat())
        messages = [{"role": "system", "content": system}]
        recent = self.memory.get_history(self.session_id, limit=10)
        for msg in recent:
            messages.append({"role": msg["role"], "content": msg["content"]})
        knowledge = self.memory.recall_knowledge(category="context", limit=5)
        if knowledge:
            ctx = "\n".join([f"- {k['key']}: {k['value']}" for k in knowledge])
            messages.append({"role": "system", "content": f"Relevant knowledge:\n{ctx}"})
        # Vector Memory recall
        vector_results = self.vector_memory.search(user_input, top_k=recall_limit)
        if vector_results:
            vctx = "\n".join([f"- {r['content']}" for r in vector_results])
            messages.insert(1, {
                "role": "system",
                "content": f"Related knowledge (Vector Memory):\n{vctx}"
            })
        messages.append({"role": "user", "content": user_input})
        return messages

    def chat(self, user_input, prefer_provider=None):
        self.memory.save_message(self.session_id, "user", user_input)
        messages = self._build_messages(user_input)
        try:
            result = self.router.chat(messages, prefer=prefer_provider)
            self.memory.save_message(
                self.session_id, "assistant", result["content"],
                model=result["model"], provider=result["provider"], tokens=result["tokens"]
            )
            self.commands.event_bus.emit("chat_complete", {
                "provider": result["provider"],
                "model": result["model"],
                "tokens": result["tokens"]
            })
            # Auto-store to Vector Memory if important
            self._store_to_vector_if_important(user_input, result["content"])
            return {
                "response": result["content"],
                "provider": result["provider"],
                "model": result["model"],
                "tokens": result["tokens"]
            }
        except Exception as e:
            return {"error": str(e)}

    def _store_to_vector_if_important(self, user_input, response):
        triggers = ["จำไว้ว่า", "บันทึก", "สำคัญ", "remember", "save this",
                      "important", "อย่าลืม", "note this", "store this"]
        if any(t in user_input.lower() for t in triggers):
            content = f"User: {user_input}\nAssistant: {response}"
            self.vector_memory.add_document(content, {
                "session_id": self.session_id,
                "type": "important_conversation",
                "timestamp": time.time()
            })

    def _cmd_chat(self, args, user, role):
        message = args.get("message", "") or args.get("text", "") or " ".join(args.values()) if args else ""
        if not message:
            return {"error": "Usage: chat <message>"}
        return self.chat(message)

    def _cmd_remember(self, args, user, role):
        key = args.get("key", "")
        value = args.get("value", "")
        category = args.get("category", "general")
        if key and value:
            self.memory.store_knowledge(key, value, category)
            return {"stored": key, "category": category}
        return {"error": "Usage: remember key=<key> value=<value> [category=<cat>]"}

    def _cmd_recall(self, args, user, role):
        key = args.get("key", None)
        category = args.get("category", None)
        return {"results": self.memory.recall_knowledge(key, category)}

    def _cmd_learn(self, args, user, role):
        text = args.get("text", "")
        if text:
            self.memory.add_fact(text, args.get("category", "general"))
            return {"learned": text}
        return {"error": "Usage: learn text=<fact>"}

    def _cmd_fact(self, args, user, role):
        return {"facts": self.memory.recall_facts(args.get("category"), limit=10)}

    def _cmd_plugin(self, args, user, role):
        action = args.get("action", "list")
        if action == "list":
            return self.plugins.list_all()
        elif action == "discover":
            return {"discovered": self.plugins.discover()}
        elif action == "reload":
            name = args.get("name")
            self.plugins.reload(name)
            return {"reloaded": name or "all"}
        return {"error": "Unknown plugin action"}

    def _cmd_router(self, args, user, role):
        action = args.get("action", "status")
        if action == "status":
            return self.router.get_status()
        elif action == "test":
            return self.router.test_all()
        return {"error": "Unknown router action"}

    def _cmd_history(self, args, user, role):
        session = args.get("session", self.session_id)
        limit = int(args.get("limit", 20))
        return {"history": self.memory.get_history(session, limit)}

    def _cmd_clear(self, args, user, role):
        self.session_id = f"session_{int(time.time())}"
        return {"new_session": self.session_id}

    def _cmd_new_session(self, args, user, role):
        self.session_id = f"session_{int(time.time())}"
        return {"session_id": self.session_id}

    def _cmd_sessions(self, args, user, role):
        return {"sessions": self.memory.get_all_sessions()}

    def _cmd_stats(self, args, user, role):
        stats = self.memory.get_stats()
        stats["active_session"] = self.session_id
        stats["plugins"] = len(self.plugins.plugins)
        stats["commands"] = len(self.commands.commands)
        stats["current_provider"] = self.router.current_provider
        stats["line_auth"] = self.line_auth.get_status()
        return stats

    def _cmd_export(self, args, user, role):
        data = {
            "sessions": self.memory.get_all_sessions(),
            "knowledge": self.memory.recall_knowledge(),
            "facts": self.memory.recall_facts(),
            "skills": self.memory.list_skills(),
            "stats": self.memory.get_stats()
        }
        export_path = os.path.join(self.config_dir, f"export_{int(time.time())}.json")
        with open(export_path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        return {"exported": export_path}

    def _cmd_test(self, args, user, role):
        return self.router.test_all()

    def _cmd_line(self, args, user, role):
        action = args.get("action", "status")

        if action == "status":
            auth_status = self.line_auth.get_status()
            return {"auth": auth_status}

        elif action == "auth":
            channel_id = args.get("id", "")
            channel_secret = args.get("secret", "")
            if not channel_id or not channel_secret:
                return {"error": "Usage: line auth id=<channel_id> secret=<channel_secret>"}

            auth_url, state = self.line_auth.generate_auth_url(channel_id, channel_secret)

            if self.oauth_server:
                self.oauth_server.stop()
            self.oauth_server = OAuthServer()
            self.oauth_server.start(expected_state=state)

            return {
                "auth_url": auth_url,
                "server": "http://localhost:8088",
                "instructions": [
                    "1. Open the auth URL in browser",
                    "2. Login and authorize the app",
                    "3. Copy the code from callback",
                    "4. Run: /line code=<CODE>"
                ]
            }

        elif action == "code":
            code = args.get("code", "")
            if not code:
                return {"error": "Usage: line code=<authorization_code>"}

            saved = self.line_auth._load_state()
            channel_id = saved.get("channel_id", "")
            channel_secret = args.get("secret", "") or saved.get("channel_secret", "")

            if not channel_id:
                return {"error": "No channel_id found. Run: line auth id=<id> secret=<secret>"}

            ok, msg = self.line_auth.exchange_code(code, channel_id, channel_secret)
            if ok:
                if self.router.line:
                    token = self.line_auth.credentials.get("access_token", "")
                    self.router.line.set_token(token)
            return {"success": ok, "message": msg}

        elif action == "verify":
            token, msg = self.line_auth.get_valid_token()
            if token:
                return self.line_auth.verify_token()
            return {"error": msg}

        elif action == "profile":
            token, msg = self.line_auth.get_valid_token()
            if token:
                return self.line_auth.get_profile()
            return {"error": msg}

        elif action == "refresh":
            secret = args.get("secret", "")
            ok, msg = self.line_auth.refresh_access_token(secret)
            if ok and self.router.line:
                token = self.line_auth.credentials.get("access_token", "")
                self.router.line.set_token(token)
            return {"success": ok, "message": msg}

        elif action == "logout":
            ok, msg = self.line_auth.logout()
            if self.router.line:
                self.router.line.set_token("")
            return {"success": ok, "message": msg}

        elif action == "test":
            token, msg = self.line_auth.get_valid_token()
            if token and self.router.line:
                self.router.line.set_token(token)
                ok, test_msg = self.router.line.test_connection()
                return {"connected": ok, "info": test_msg}
            return {"error": msg or "LINE not connected"}

        elif action == "quota":
            token, msg = self.line_auth.get_valid_token()
            if token and self.router.line:
                self.router.line.set_token(token)
                return self.router.line.get_message_quota()
            return {"error": msg or "LINE not connected"}

        elif action == "groups":
            token, msg = self.line_auth.get_valid_token()
            if token and self.router.line:
                self.router.line.set_token(token)
                return self.router.line.get_groups()
            return {"error": msg or "LINE not connected"}

        return {"error": "Unknown LINE action. Use: status, auth, code, verify, profile, refresh, logout, test, quota, groups"}

    def _cmd_line_send(self, args, user, role):
        user_id = args.get("to", "")
        message = args.get("msg", "") or args.get("message", "")
        if not user_id or not message:
            return {"error": "Usage: send to=<user_id> msg=<message>"}
        token, msg = self.line_auth.get_valid_token()
        if token and self.router.line:
            self.router.line.set_token(token)
            return self.router.line.push_message(user_id, message)
        return {"error": msg or "LINE not connected"}

    def _cmd_line_notify(self, args, user, role):
        message = args.get("msg", "") or args.get("message", "")
        if not message:
            return {"error": "Usage: notify msg=<message>"}
        token, msg = self.line_auth.get_valid_token()
        if token and self.router.line:
            self.router.line.set_token(token)
            return self.router.line.send_notification(message)
        return {"error": msg or "LINE not connected"}

    def _cmd_rate(self, args, user, role):
        doc_id = args.get("id", "")
        rating = float(args.get("rating", 0))
        if not doc_id or not (0 <= rating <= 1):
            return {"error": "Usage: rate id=<doc_id> rating=<0.0-1.0>"}
        self.feedback.record(doc_id, rating)
        return {"status": "recorded", "rating": rating, "doc_id": doc_id}

    def process_input(self, raw_input):
        raw_input = raw_input.strip()
        if not raw_input:
            return {"error": "Empty input"}

        parts = raw_input.split(maxsplit=1)
        cmd = parts[0].lower()
        arg_str = parts[1] if len(parts) > 1 else ""

        args = {}
        if arg_str:
            for part in arg_str.split():
                if "=" in part:
                    k, v = part.split("=", 1)
                    args[k] = v
            if not args:
                args = {"message": arg_str, "text": arg_str}

        # For commands with subcommands (like "line auth"), parse first word as action
        if cmd in self.commands.commands and arg_str:
            first_word = arg_str.split()[0] if arg_str.split() else ""
            if first_word.isalpha() and first_word not in args:
                args["action"] = first_word
                remaining = arg_str[len(first_word):].strip()
                if remaining:
                    for part in remaining.split():
                        if "=" in part:
                            k, v = part.split("=", 1)
                            args[k] = v

        if cmd not in self.commands.commands:
            args = {"message": raw_input}
            cmd = "chat"

        return self.commands.execute(cmd, args)

    def shutdown(self):
        if self.oauth_server:
            self.oauth_server.stop()
        self.memory.close()
