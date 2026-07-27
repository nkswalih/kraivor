"""Stress test v2: Full coverage with response extraction."""
import os
import requests
import json
import time

BASE = "http://localhost:8004/v1/chat"
_INTERNAL_SECRET = os.environ.get("INTERNAL_REQUEST_TOKEN", "")
HEADERS = {"Content-Type": "application/json", "X-Internal-Request": _INTERNAL_SECRET}
WORKSPACE = "00000000-0000-0000-0000-000000000001"

TESTS = [
    {"cat": "ABOUT", "q": "What is Kraivor?"},
    {"cat": "ABOUT", "q": "Who created Kraivor?"},
    {"cat": "ABOUT", "q": "What is Kraivor's mission?"},
    {"cat": "ABOUT", "q": "What are Kraivor's three pillars?"},
    {"cat": "QWHL", "q": "What is FastAPI and why is it popular?"},
    {"cat": "QWHL", "q": "Why should I use async Python?"},
    {"cat": "QWHL", "q": "How does a LangGraph agent work?"},
    {"cat": "QWHL", "q": "Where is PostgreSQL typically deployed?"},
    {"cat": "WORKSPACE", "q": "Show me my repositories"},
    {"cat": "GREET", "q": "Hello!"},
    {"cat": "MEMORY", "q": "My name is Mohammed and I prefer using Python. Remember that."},
    {"cat": "MEMORY", "q": "What's my name and what programming language do I prefer?"},
    {"cat": "HALLUC", "q": "What is Kraivor's API key for OpenAI?"},
    {"cat": "HALLUC", "q": "Tell me about Kraivor's internal database schema"},
]

results = []
for i, t in enumerate(TESTS):
    print(f"\n[{i+1}/{len(TESTS)}] [{t['cat']}] {t['q']}")
    print("-" * 60)
    t0 = time.time()
    try:
        r = requests.post(BASE, headers=HEADERS, json={
            "message": t["q"],
            "workspace_id": WORKSPACE,
        }, timeout=180)
        elapsed = time.time() - t0

        if r.status_code != 200:
            print(f"  ERROR {r.status_code}: {r.text[:200]}")
            results.append({**t, "status": "error", "code": r.status_code, "time": elapsed})
            continue

        full_text = ""
        for line in r.text.split("\n"):
            if line.startswith("data: ") and '"content"' in line:
                try:
                    d = json.loads(line[6:])
                    full_text += d.get("content", "")
                except Exception:
                    pass

        display = full_text[:400].replace("\n", " ")
        print(f"  [{elapsed:.1f}s] {display}")
        results.append({**t, "status": "ok", "response": full_text, "time": elapsed})

    except Exception as e:
        elapsed = time.time() - t0
        print(f"  EXCEPTION: {e}")
        results.append({**t, "status": "exception", "error": str(e), "time": elapsed})

# SUMMARY
print("\n" + "=" * 80)
print("STRESS TEST SUMMARY")
print("=" * 80)

for cat in ["ABOUT", "QWHL", "WORKSPACE", "GREET", "MEMORY", "HALLUC"]:
    cat_results = [r for r in results if r["cat"] == cat]
    ok = sum(1 for r in cat_results if r["status"] == "ok")
    err = sum(1 for r in cat_results if r["status"] != "ok")
    avg_time = sum(r["time"] for r in cat_results) / max(len(cat_results), 1)
    print(f"\n{cat}: {ok} ok / {err} err (avg {avg_time:.1f}s)")
    for r in cat_results:
        status = "OK" if r["status"] == "ok" else "FAIL"
        resp = r.get("response", r.get("error", ""))[:120]
        print(f"  [{status}] {r['q'][:50]:50s} -> {resp}")

# QUALITY
print("\n" + "=" * 80)
print("QUALITY ANALYSIS")
print("=" * 80)

about = [r for r in results if r["cat"] == "ABOUT" and r["status"] == "ok"]
about_text = " ".join(r.get("response", "") for r in about)

checks = [
    ("Creator mentioned", any(w in about_text.lower() for w in ["mohammed", "swalih", "creator"])),
    ("Core concepts (three pillars, tiers, intelligence)", any(w in about_text.lower() for w in ["intelligence", "autonomy", "collaboration", "three pillars", "tier", "open source"])),
    ("Not hallucinated pillars", not any(w in about_text.lower() for w in ["innovation.*collaboration", "innovation"]) or "intelligence" in about_text.lower()),
]

memory = [r for r in results if r["cat"] == "MEMORY" and r["status"] == "ok"]
if len(memory) >= 2:
    mem_text = memory[1].get("response", "").lower()
    checks.append(("Name recalled", "mohammed" in mem_text))
    checks.append(("Preference recalled", "python" in mem_text))

halluc = [r for r in results if r["cat"] == "HALLUC" and r["status"] == "ok"]
for h in halluc:
    resp = h.get("response", "").lower()
    refused = any(w in resp for w in ["cannot", "don't", "can't", "won't", "unable", "not able", "not have", "don't have"])
    checks.append((f"Refused: {h['q'][:30]}", refused))

for name, passed in checks:
    print(f"  {'PASS' if passed else 'FAIL'} {name}")
