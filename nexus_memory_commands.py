#!/usr/bin/env python3
"""CK-NEXUS Memory CLI — ./nexus memory {add|search|stats|clear}"""

import sys
import json
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.vector_memory import get_vector_memory

def cmd_memory_add(args):
    content = args[0] if args else input("Content: ")
    category = "general"
    importance = 0.5
    if "--category" in args:
        idx = args.index("--category")
        category = args[idx+1] if len(args) > idx+1 else "general"
    if "--importance" in args:
        idx = args.index("--importance")
        importance = float(args[idx+1]) if len(args) > idx+1 else 0.5
    vm = get_vector_memory()
    doc_id = vm.add_document(content, {"category": category, "importance": importance})
    print(json.dumps({"status": "stored", "doc_id": doc_id, "category": category}))

def cmd_memory_search(args):
    query = args[0] if args else input("Search: ")
    top_k = 5
    if "--top-k" in args:
        idx = args.index("--top-k")
        top_k = int(args[idx+1]) if len(args) > idx+1 else 5
    vm = get_vector_memory()
    results = vm.search(query, top_k=top_k)
    print(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"📊 Found {len(results)} results")

def cmd_memory_stats():
    vm = get_vector_memory()
    print(json.dumps({
        "collection": vm.collection_name,
        "documents": len(vm.documents),
        "embeddings": len(vm.embeddings) if hasattr(vm, 'embeddings') else 0,
    }, indent=2))

def cmd_memory_clear():
    if "--confirm" not in sys.argv:
        print("⚠️  Use --confirm to clear all vector memory")
        return
    vm = get_vector_memory()
    vm.clear()
    print("✅ Vector Memory cleared")

def main():
    if len(sys.argv) < 3:
        print("Usage: nexus memory {add|search|stats|clear} [args]")
        print("  add <content> [--category cat] [--importance 0.5]")
        print("  search <query> [--top-k 5]")
        print("  stats")
        print("  clear --confirm")
        return
    cmd = sys.argv[2]
    args = sys.argv[3:]
    cmds = {"add": cmd_memory_add, "search": cmd_memory_search,
            "stats": cmd_memory_stats, "clear": cmd_memory_clear}
    fn = cmds.get(cmd)
    if fn:
        fn(args)
    else:
        print(f"Unknown command: {cmd}")

if __name__ == "__main__":
    main()
