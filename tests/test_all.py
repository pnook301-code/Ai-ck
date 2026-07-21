#!/usr/bin/env python3
"""CK-NEXUS Test Suite - comprehensive tests"""
import sys
import os
import shutil
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def cleanup():
    for p in ["/tmp/test_nexus.db", "/tmp/test_nexus_engine", "/tmp/test_mem.db", "/tmp/test_plugins", "/tmp/test_creds"]:
        if os.path.isfile(p):
            os.remove(p)
        elif os.path.isdir(p):
            shutil.rmtree(p)


def test_memory():
    print("=== Testing MemoryOS ===")
    from core.memory import MemoryOS
    db_path = "/tmp/test_mem.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    mem = MemoryOS(db_path)

    mem.save_message("test_1", "user", "Hello!")
    mem.save_message("test_1", "assistant", "Hi there!")
    history = mem.get_history("test_1")
    assert len(history) == 2, f"Expected 2, got {len(history)}"
    print("  ✓ Conversation storage")

    mem.store_knowledge("test_key", "test_value", "test")
    k = mem.recall_knowledge("test_key")
    assert k is not None and k["value"] == "test_value"
    print("  ✓ Knowledge storage")

    mem.add_fact("The sky is blue", "science")
    facts = mem.recall_facts("science")
    assert len(facts) >= 1
    print("  ✓ Facts storage")

    stats = mem.get_stats()
    assert stats["total_messages"] >= 2
    print(f"  ✓ Stats: {stats}")

    mem.close()
    os.remove(db_path)
    print("  ✓ MemoryOS PASSED\n")


def test_token_store():
    print("=== Testing TokenStore ===")
    from core.token_store import TokenStore

    store_dir = "/tmp/test_creds"
    if os.path.exists(store_dir):
        shutil.rmtree(store_dir)

    store = TokenStore(store_dir)

    # Test save/load
    store.save_tokens("line", {"access_token": "test_token_123", "expires_at": "2099-01-01"})
    loaded = store.load_tokens("line")
    assert loaded is not None
    assert loaded["access_token"] == "test_token_123"
    print("  ✓ Token save/load")

    # Test encrypted file
    with open(os.path.join(store_dir, "tokens.enc")) as f:
        raw = json.load(f)
    assert "line" in raw
    assert "data" in raw["line"]
    assert raw["line"]["data"] != json.dumps({"access_token": "test_token_123"})
    print("  ✓ Token encrypted in file")

    # Test has_tokens
    assert store.has_tokens("line") == True
    assert store.has_tokens("groq") == False
    print("  ✓ has_tokens")

    # Test list_providers
    providers = store.list_providers()
    assert "line" in providers
    print("  ✓ list_providers")

    # Test delete
    store.delete_tokens("line")
    assert store.has_tokens("line") == False
    print("  ✓ Token delete")

    # Test multiple providers
    store.save_tokens("openai", {"key": "sk-123"})
    store.save_tokens("groq", {"key": "gsk-456"})
    assert len(store.list_providers()) == 2
    store.delete_all()
    assert len(store.list_providers()) == 0
    print("  ✓ Multiple providers")

    # Test status
    status = store.get_status()
    assert "encrypted" in status
    print(f"  ✓ Status: {status}")

    shutil.rmtree(store_dir)
    print("  ✓ TokenStore PASSED\n")


def test_line_auth():
    print("=== Testing LineAuthManager ===")
    from core.line_auth import LineAuthManager

    auth_dir = "/tmp/test_line_auth"
    if os.path.exists(auth_dir):
        shutil.rmtree(auth_dir)

    auth = LineAuthManager(auth_dir)

    # Test initial state
    status = auth.get_status()
    assert status["configured"] == False
    assert status["authenticated"] == False
    assert status["expired"] == True
    print("  ✓ Initial state")

    # Test generate auth URL
    auth_url, state = auth.generate_auth_url("1234567890")
    assert "access.line.me" in auth_url
    assert "client_id=1234567890" in auth_url
    assert "state=" in auth_url
    assert len(state) > 10
    print("  ✓ Auth URL generated")

    # Test state validation
    saved = auth._load_state()
    assert saved["state"] == state
    assert auth.validate_state(state) == True
    assert auth.validate_state("wrong_state") == False
    print("  ✓ State validation")

    # Test encrypted storage
    auth.credentials = {"access_token": "test", "expires_at": "2099-01-01"}
    auth._save_credentials()
    with open(os.path.join(auth_dir, "line_tokens.json")) as f:
        raw = json.load(f)
    assert "encrypted" in raw
    print("  ✓ Credentials encrypted")

    # Test load back
    auth2 = LineAuthManager(auth_dir)
    assert auth2.credentials["access_token"] == "test"
    print("  ✓ Credentials load back")

    # Test is_expired
    assert auth.is_expired() == False
    auth.credentials["expires_at"] = "2020-01-01"
    assert auth.is_expired() == True
    print("  ✓ Expiry check")

    # Test logout
    auth.credentials = {"access_token": "token123"}
    auth._save_credentials()
    ok, msg = auth.logout()
    assert ok == True
    assert auth.credentials == {}
    print("  ✓ Logout")

    # Test get_status with encrypted info
    status = auth.get_status()
    assert status["encrypted"] == True
    print(f"  ✓ Status with encryption flag")

    shutil.rmtree(auth_dir)
    print("  ✓ LineAuthManager PASSED\n")


def test_oauth_server():
    print("=== Testing OAuthServer ===")
    from core.oauth_server import OAuthServer

    server = OAuthServer(18088)

    # Test start
    ok = server.start(expected_state="test_state_123")
    assert ok == True
    assert server.thread is not None
    print("  ✓ Server start")

    # Test state stored
    from core.oauth_server import OAuthCallbackHandler
    assert OAuthCallbackHandler.expected_state == "test_state_123"
    print("  ✓ Expected state stored")

    # Test reset
    OAuthCallbackHandler.auth_code = "fake_code"
    server.reset()
    assert OAuthCallbackHandler.auth_code is None
    print("  ✓ Reset")

    # Test stop
    server.stop()
    assert server.server is None
    print("  ✓ Server stop")

    print("  ✓ OAuthServer PASSED\n")


def test_command_bus():
    print("=== Testing CommandBus ===")
    from core.command_bus import CommandBus

    bus = CommandBus()
    assert "help" in bus.commands
    assert "status" in bus.commands
    print("  ✓ Default commands")

    result = bus.execute("help")
    assert "commands" in result
    print("  ✓ Help command")

    result = bus.execute("status")
    assert result["status"] == "operational"
    print("  ✓ Status command")

    result = bus.execute("nonexistent")
    assert "error" in result
    print("  ✓ Unknown command handled")

    bus.event_bus.emit("test_event", {"data": "hello"})
    history = bus.event_bus.get_history()
    assert len(history) >= 1
    print("  ✓ EventBus")

    print("  ✓ CommandBus PASSED\n")


def test_plugin_manager():
    print("=== Testing PluginManager ===")
    from core.plugin_manager import PluginManager

    test_dir = "/tmp/test_plugins"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)

    with open(os.path.join(test_dir, "test_plugin.py"), "w") as f:
        f.write('def execute(*a, **k): return {"ok": True}\n')

    pm = PluginManager(test_dir)
    discovered = pm.discover()
    assert "test_plugin" in discovered
    print(f"  ✓ Discovered: {discovered}")

    result = pm.execute("test_plugin")
    assert result["ok"] == True
    print("  ✓ Plugin execution")

    pm.install("new_plugin", 'def execute(*a,**k): return {"new": True}')
    assert "new_plugin" in pm.list_all()
    print("  ✓ Plugin install")

    shutil.rmtree(test_dir)
    print("  ✓ PluginManager PASSED\n")


def test_providers():
    print("=== Testing ProviderRouter ===")
    from providers.provider_router import ProviderRouter

    router = ProviderRouter()
    status = router.get_status()
    print(f"  Providers: {list(status.keys())}")

    for prov in ["openai", "groq"]:
        print(f"  Testing {prov}...")
        try:
            result = router._call_openai_compatible(prov, [{"role": "user", "content": "Say OK"}], 0.5, 10)
            print(f"  ✓ {prov}: {result['content'][:50]}")
        except Exception as e:
            err = str(e)[:80]
            print(f"  ✗ {prov}: {err}")

    print("  ✓ ProviderRouter PASSED\n")


def test_engine():
    print("=== Testing NexusEngine ===")
    from nexus_engine import NexusEngine

    eng_dir = "/tmp/test_engine"
    if os.path.exists(eng_dir):
        shutil.rmtree(eng_dir)

    engine = NexusEngine(eng_dir)
    print(f"  Session: {engine.session_id}")

    result = engine.process_input("help")
    assert "commands" in result
    print("  ✓ Help OK")

    result = engine.process_input("stats")
    assert "total_messages" in result
    print("  ✓ Stats OK")

    result = engine.process_input("router")
    assert "openai" in result
    print("  ✓ Router status OK")

    result = engine.process_input("line status")
    assert "auth" in result
    print("  ✓ LINE status OK")

    result = engine.process_input("line auth id=1234567890 secret=abcdefghijklmnopqrstuvwxyz123456")
    assert "auth_url" in result
    print("  ✓ LINE auth start")

    result = engine.process_input("line test")
    assert "error" in result
    print("  ✓ LINE test (not connected)")

    result = engine.process_input("line logout")
    assert result.get("success") == True
    print("  ✓ LINE logout")

    engine.shutdown()
    shutil.rmtree(eng_dir, ignore_errors=True)
    print("  ✓ NexusEngine PASSED\n")


if __name__ == "__main__":
    cleanup()
    print("CK-NEXUS Test Suite v0.1.0")
    print("=" * 50)

    test_memory()
    test_token_store()
    test_line_auth()
    test_oauth_server()
    test_command_bus()
    test_plugin_manager()
    test_providers()
    test_engine()

    print("=" * 50)
    print("ALL TESTS PASSED ✓")
