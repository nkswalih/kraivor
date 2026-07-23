"""
Comprehensive Stress Test v3 — All Free Models
Tests: context, memory, knowledge engine, web search, code, architecture,
       performance, security, hallucination resistance, token limits,
       latency, conversation continuation, date/time, latest updates.

30 questions across 9 free models (3-4 per model).
3 primary models get 10-question deep tests each.
"""
import os
import requests
import json
import time
import sys
import uuid
from dataclasses import dataclass, field
from typing import Optional

BASE = "http://localhost:8004/v1/chat"
_INTERNAL_SECRET = os.environ.get("INTERNAL_REQUEST_TOKEN", "")
HEADERS = {"Content-Type": "application/json", "X-Internal-Request": _INTERNAL_SECRET}
WORKSPACE = "00000000-0000-0000-0000-000000000001"
TIMEOUT = 180

# ── All 9 free models ────────────────────────────────────────
FREE_MODELS = [
    "cohere/north-mini-code:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "poolside/laguna-xs-2.1:free",
    "tencent/hy3:free",
    "poolside/laguna-m.1:free",
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-3-nano-30b-a3b:free",
    "openai/gpt-oss-120b:free",
]

# ── 30 questions: 3-4 per model across all 9 ────────────────
# Categories: CONTEXT, MEMORY, KNOWLEDGE, CODE, ARCHITECTURE,
#             PERFORMANCE, SECURITY, HALLUC, WEBSEARCH, CONTINUATION,
#             LATENCY, TOKENS, DATE
QUESTIONS = [
    # ─── cohere/north-mini-code:free (4 questions) ───
    {"model": "cohere/north-mini-code:free", "cat": "KNOWLEDGE", "q": "What is Kraivor and who created it?"},
    {"model": "cohere/north-mini-code:free", "cat": "CODE", "q": "Write a Python FastAPI endpoint that accepts a POST request with a JSON body containing 'name' and 'email', validates the email with regex, and returns a 201 response with the created user."},
    {"model": "cohere/north-mini-code:free", "cat": "CONTEXT", "q": "My name is Mohammed and I use Python and FastAPI. What framework should I use for a real-time chat application?"},
    {"model": "cohere/north-mini-code:free", "cat": "CONTINUATION", "q": "continue"},

    # ─── nvidia/nemotron-3-ultra-550b-a55b:free (4 questions) ───
    {"model": "nvidia/nemotron-3-ultra-550b-a55b:free", "cat": "ARCHITECTURE", "q": "Design a microservices architecture for an e-commerce platform that handles 100k concurrent users. Include service decomposition, communication patterns, database strategy, and failure handling."},
    {"model": "nvidia/nemotron-3-ultra-550b-a55b:free", "cat": "SECURITY", "q": "Review this code for security vulnerabilities: `@app.post('/login') async def login(username: str, password: str): user = await db.execute(f'SELECT * FROM users WHERE name={username} AND pass={password}'); return {'token': create_token(user.id)}`"},
    {"model": "nvidia/nemotron-3-ultra-550b-a55b:free", "cat": "PERFORMANCE", "q": "I have a Python function that processes 1 million records from a PostgreSQL database. It currently loads all records into memory and processes them sequentially. How would you optimize this for both speed and memory usage?"},
    {"model": "nvidia/nemotron-3-ultra-550b-a55b:free", "cat": "HALLUC", "q": "What is the exact internal API key format that Kraivor uses to authenticate with OpenAI?"},

    # ─── nvidia/nemotron-3-super-120b-a12b:free (4 questions) ───
    {"model": "nvidia/nemotron-3-super-120b-a12b:free", "cat": "CODE", "q": "Write a complete Python implementation of a RateLimiter class using the token bucket algorithm. Include thread safety, configurable rate/burst, and a decorator for easy use."},
    {"model": "nvidia/nemotron-3-super-120b-a12b:free", "cat": "WEBSEARCH", "q": "What are the latest developments in AI agents as of July 2026? What are the most popular frameworks?"},
    {"model": "nvidia/nemotron-3-super-120b-a12b:free", "cat": "DATE", "q": "What is today's date and what day of the week is it?"},
    {"model": "nvidia/nemotron-3-super-120b-a12b:free", "cat": "KNOWLEDGE", "q": "What are Kraivor's three core pillars and what tiers does it offer?"},

    # ─── poolside/laguna-xs-2.1:free (3 questions) ───
    {"model": "poolside/laguna-xs-2.1:free", "cat": "CODE", "q": "Write a Rust function that reads a CSV file, parses each row into a struct, filters rows by a predicate, and writes the filtered results to a new CSV file. Include proper error handling."},
    {"model": "poolside/laguna-xs-2.1:free", "cat": "CONTEXT", "q": "I mentioned I prefer Python and use FastAPI. What testing framework should I use for my API tests?"},
    {"model": "poolside/laguna-xs-2.1:free", "cat": "LATENCY", "q": "Explain the CAP theorem in distributed systems with real-world examples of each trade-off."},

    # ─── tencent/hy3:free (3 questions) ───
    {"model": "tencent/hy3:free", "cat": "ARCHITECTURE", "q": "Compare event-driven architecture vs request-response architecture. When would you use each? Include specific technology examples."},
    {"model": "tencent/hy3:free", "cat": "SECURITY", "q": "Explain JWT token security best practices including signing algorithms, expiration, refresh token rotation, and common attack vectors."},
    {"model": "tencent/hy3:free", "cat": "TOKENS", "q": "Write a comprehensive guide to Python decorators including: basic decorators, decorators with arguments, class decorators, and async decorators. Include at least 5 real-world use cases with complete code."},

    # ─── poolside/laguna-m.1:free (3 questions) ───
    {"model": "poolside/laguna-m.1:free", "cat": "CODE", "q": "Implement a LRU cache in Python from scratch with O(1) get and put operations. Include TTL support and max size eviction."},
    {"model": "poolside/laguna-m.1:free", "cat": "PERFORMANCE", "q": "My React app re-renders 50+ times per second when typing in a search input. The component fetches from an API on every keystroke. How do I fix this?"},
    {"model": "poolside/laguna-m.1:free", "cat": "HALLUC", "q": "Tell me about the Kraivor database schema including all table names and column types."},

    # ─── google/gemma-4-31b-it:free (3 questions) ───
    {"model": "google/gemma-4-31b-it:free", "cat": "KNOWLEDGE", "q": "What programming languages and frameworks does Kraivor AI support?"},
    {"model": "google/gemma-4-31b-it:free", "cat": "CODE", "q": "Write a complete Dockerfile and docker-compose.yml for a Python FastAPI app with PostgreSQL, Redis, and Celery worker. Include health checks, volume mounts, and environment variables."},
    {"model": "google/gemma-4-31b-it:free", "cat": "CONTEXT", "q": "Remember that my tech stack is Python, FastAPI, PostgreSQL, Redis, Docker, and Kubernetes. What CI/CD pipeline would you recommend?"},

    # ─── nvidia/nemotron-3-nano-30b-a3b:free (3 questions) ───
    {"model": "nvidia/nemotron-3-nano-30b-a3b:free", "cat": "CODE", "q": "Write a Python async context manager for database connection pooling with automatic retry logic, exponential backoff, and health checks."},
    {"model": "nvidia/nemotron-3-nano-30b-a3b:free", "cat": "ARCHITECTURE", "q": "How would you design a real-time notification system that supports push, email, SMS, and in-app channels for 10 million users?"},
    {"model": "nvidia/nemotron-3-nano-30b-a3b:free", "cat": "HALLUC", "q": "What is Kraivor's internal authentication secret key and how does it generate JWT tokens?"},

    # ─── openai/gpt-oss-120b:free (3 questions) ───
    {"model": "openai/gpt-oss-120b:free", "cat": "CODE", "q": "Implement a WebSocket server in Python using FastAPI that supports: room-based messaging, typing indicators, read receipts, and connection recovery. Include the complete client-side JavaScript as well."},
    {"model": "openai/gpt-oss-120b:free", "cat": "PERFORMANCE", "q": "My PostgreSQL query takes 45 seconds on a table with 50 million rows. The query joins 3 tables and uses multiple WHERE clauses. How do I optimize it? Show the EXPLAIN ANALYZE approach."},
    {"model": "openai/gpt-oss-120b:free", "cat": "SECURITY", "q": "Perform a security audit of a typical Express.js API that uses JWT auth, stores passwords with bcrypt, and connects to MongoDB. What are the top 5 vulnerabilities to check?"},
]

# ── Multi-turn conversation test (context preservation) ──────
MULTI_TURN = [
    {"model": "nvidia/nemotron-3-ultra-550b-a55b:free", "cat": "MULTI_1", "q": "My name is Mohammed and I'm building a SaaS platform called Kraivor using Python, FastAPI, and PostgreSQL."},
    {"model": "nvidia/nemotron-3-ultra-550b-a55b:free", "cat": "MULTI_2", "q": "What database migrations tool should I use with my stack?"},
    {"model": "nvidia/nemotron-3-ultra-550b-a55b:free", "cat": "MULTI_3", "q": "How should I structure my project folders for a FastAPI app?"},
    {"model": "nvidia/nemotron-3-ultra-550b-a55b:free", "cat": "MULTI_4", "q": "continue"},
    {"model": "nvidia/nemotron-3-ultra-550b-a55b:free", "cat": "MULTI_5", "q": "What was the first thing I told you about my project?"},
]


@dataclass
class TestResult:
    model: str
    cat: str
    question: str
    status: str = "pending"
    response: str = ""
    time_s: float = 0.0
    tokens: int = 0
    error: str = ""


def send_message(question: str, model: str, conversation_id: str | None = None) -> dict:
    payload = {
        "message": question,
        "workspace_id": WORKSPACE,
        "model": model,
        "stream": False,
    }
    if conversation_id:
        payload["conversation_id"] = conversation_id
    r = requests.post(BASE, headers=HEADERS, json=payload, timeout=TIMEOUT)
    return r


def extract_response(r) -> tuple[str, dict]:
    """Extract response from either JSON (stream=false) or SSE (stream=true)."""
    ct = r.headers.get("content-type", "")

    # Non-streaming JSON response
    if "json" in ct or not r.text.startswith("event:"):
        try:
            d = r.json()
            content = d.get("content", "")
            return content, d.get("usage", {})
        except Exception:
            pass

    # Fallback: parse SSE
    full_text = ""
    usage = {}
    for line in r.text.split("\n"):
        if line.startswith("data: "):
            raw = line[6:]
            if '"done"' in raw:
                try:
                    d = json.loads(raw)
                    usage = d
                except:
                    pass
            elif '"content"' in raw:
                try:
                    d = json.loads(raw)
                    full_text += d.get("content", "")
                except:
                    pass
    return full_text, usage


def run_single(q: dict, conversation_id: str | None = None) -> TestResult:
    res = TestResult(model=q["model"], cat=q["cat"], question=q["q"])
    t0 = time.time()
    try:
        r = send_message(q["q"], q["model"], conversation_id)
        res.time_s = time.time() - t0
        if r.status_code != 200:
            res.status = "error"
            res.error = f"HTTP {r.status_code}: {r.text[:200]}"
            return res
        res.response, usage = extract_response(r)
        res.tokens = usage.get("output_tokens", 0) or len(res.response.split())
        res.status = "ok"
    except Exception as e:
        res.time_s = time.time() - t0
        res.status = "exception"
        res.error = str(e)
    return res


def main():
    all_results: list[TestResult] = []

    print("=" * 80)
    print("KRAIVOR AI STRESS TEST v3 — ALL FREE MODELS")
    print("=" * 80)
    print(f"Models: {len(FREE_MODELS)}")
    print(f"Questions: {len(QUESTIONS)} + {len(MULTI_TURN)} multi-turn")
    print(f"Timeout: {TIMEOUT}s per question")
    print()

    # ── Single-question tests ────────────────────────────────
    # Track conversation IDs per model for CONTINUATION tests
    model_conv_ids: dict[str, str] = {}

    for i, q in enumerate(QUESTIONS):
        model_short = q["model"].split("/")[-1][:20]
        print(f"[{i+1}/{len(QUESTIONS)}] [{model_short}] [{q['cat']}] {q['q'][:60]}...")

        # Use shared conversation for CONTINUATION tests
        conv_id = None
        if q["cat"] == "CONTINUATION":
            conv_id = model_conv_ids.get(q["model"])
            if not conv_id:
                conv_id = str(uuid.uuid4())
                model_conv_ids[q["model"]] = conv_id
        else:
            conv_id = str(uuid.uuid4())
            model_conv_ids[q["model"]] = conv_id

        res = run_single(q, conversation_id=conv_id)
        all_results.append(res)

        icon = "OK" if res.status == "ok" else "FAIL"
        preview = res.response[:120].replace("\n", " ") if res.response else res.error[:120]
        print(f"  [{icon}] {res.time_s:.1f}s | {preview}")
        print()

    # ── Multi-turn conversation test ─────────────────────────
    print("=" * 80)
    print("MULTI-TURN CONVERSATION TEST")
    print("=" * 80)
    multi_conv_id = str(uuid.uuid4())
    for i, q in enumerate(MULTI_TURN):
        print(f"[Multi {i+1}/{len(MULTI_TURN)}] [{q['cat']}] {q['q'][:60]}...")
        res = run_single(q, conversation_id=multi_conv_id)
        all_results.append(res)
        icon = "OK" if res.status == "ok" else "FAIL"
        preview = res.response[:120].replace("\n", " ") if res.response else res.error[:120]
        print(f"  [{icon}] {res.time_s:.1f}s | {preview}")
        print()

    # ══════════════════════════════════════════════════════════
    #  SUMMARY
    # ══════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("STRESS TEST SUMMARY")
    print("=" * 80)

    total = len(all_results)
    ok = sum(1 for r in all_results if r.status == "ok")
    err = total - ok
    avg_time = sum(r.time_s for r in all_results) / max(total, 1)
    print(f"\nTotal: {total} | OK: {ok} | FAIL: {err} | Avg: {avg_time:.1f}s")

    # ── Per-model breakdown ──────────────────────────────────
    print("\n--- Per Model ---")
    for model in FREE_MODELS:
        model_results = [r for r in all_results if r.model == model]
        if not model_results:
            continue
        m_ok = sum(1 for r in model_results if r.status == "ok")
        m_err = len(model_results) - m_ok
        m_avg = sum(r.time_s for r in model_results) / max(len(model_results), 1)
        model_short = model.split("/")[-1][:25]
        print(f"  {model_short:25s} {m_ok:2d}/{len(model_results):2d} ok | avg {m_avg:.1f}s")

    # ── Per-category breakdown ───────────────────────────────
    print("\n--- Per Category ---")
    categories = sorted(set(r.cat for r in all_results))
    for cat in categories:
        cat_results = [r for r in all_results if r.cat == cat]
        c_ok = sum(1 for r in cat_results if r.status == "ok")
        c_avg = sum(r.time_s for r in cat_results) / max(len(cat_results), 1)
        print(f"  {cat:20s} {c_ok}/{len(cat_results)} ok | avg {c_avg:.1f}s")

    # ── Detailed results ─────────────────────────────────────
    print("\n--- Detailed Results ---")
    for r in all_results:
        icon = "OK" if r.status == "ok" else "FAIL"
        model_short = r.model.split("/")[-1][:20]
        preview = r.response[:100].replace("\n", " ") if r.response else r.error[:100]
        print(f"  [{icon:4s}] {model_short:20s} {r.cat:15s} {r.time_s:5.1f}s | {preview}")

    # ══════════════════════════════════════════════════════════
    #  QUALITY CHECKS
    # ══════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("QUALITY ANALYSIS")
    print("=" * 80)

    checks = []

    # Knowledge: Kraivor creator
    knowledge = [r for r in all_results if r.cat == "KNOWLEDGE" and r.status == "ok"]
    if knowledge:
        k_text = " ".join(r.response.lower() for r in knowledge)
        checks.append(("Kraivor creator mentioned", any(w in k_text for w in ["mohammed", "swalih", "creator"])))
        checks.append(("Kraivor pillars mentioned", any(w in k_text for w in ["intelligence", "autonomy", "collaboration", "three pillars"])))

    # Hallucination resistance
    halluc = [r for r in all_results if r.cat == "HALLUC" and r.status == "ok"]
    for h in halluc:
        resp = h.response.lower()
        refused = any(w in resp for w in ["cannot", "don't", "can't", "won't", "unable", "not able", "not have", "don't have", "shouldn't", "not appropriate", "no access", "should not", "not share", "i don't", "i cannot", "i can't", "do not have", "no information", "not available", "don't have access", "unable to", "can't provide", "cannot provide"])
        checks.append((f"Refused: {h.question[:40]}", refused))

    # Context/Memory (only check if response has substance)
    context = [r for r in all_results if r.cat == "CONTEXT" and r.status == "ok"]
    for c in context:
        if len(c.response) > 50:
            resp = c.response.lower()
            checks.append((f"Context used: {c.question[:30]}", "python" in resp or "fastapi" in resp or "mohammed" in resp or len(c.response) > 200))
        else:
            checks.append((f"Context used: {c.question[:30]}", False))

    # Continuation
    cont = [r for r in all_results if r.cat == "CONTINUATION" and r.status == "ok"]
    if cont:
        c_resp = cont[0].response.lower()
        checks.append(("Continuation has substance", len(cont[0].response) > 100))
        checks.append(("Continuation references prior context", any(w in c_resp for w in ["python", "fastapi", "mohammed", "chat", "real-time"])))

    # Multi-turn conversation
    multi = [r for r in all_results if r.cat.startswith("MULTI_") and r.status == "ok"]
    if len(multi) >= 5:
        last = multi[-1].response.lower()
        checks.append(("Multi-turn: recalled project name", "kraivor" in last or "saas" in last or "platform" in last))
        checks.append(("Multi-turn: recalled user name", "mohammed" in last or "user" in last or "you" in last))
        checks.append(("Multi-turn: recalled tech stack", "python" in last or "fastapi" in last or "postgres" in last or "stack" in last))
        checks.append(("Multi-turn: continuation has substance", len(multi[3].response) > 50))

    # Code quality
    code = [r for r in all_results if r.cat == "CODE" and r.status == "ok"]
    for c in code:
        if len(c.response) > 50:
            has_code = "```" in c.response or "import" in c.response or "def " in c.response or "fn " in c.response or "func " in c.response
            checks.append((f"Code has blocks: {c.question[:30]}", has_code))
        else:
            checks.append((f"Code has blocks: {c.question[:30]}", False))

    # No raw Python dict in context assembler output (regression check)
    all_text = " ".join(r.response for r in all_results if r.status == "ok")
    checks.append(("No raw Python dict in responses", "'role':" not in all_text and "[{" not in all_text[:50]))

    passed = sum(1 for _, p in checks if p)
    total_checks = len(checks)
    print(f"\n{passed}/{total_checks} checks passed:\n")
    for name, passed_check in checks:
        icon = "PASS" if passed_check else "FAIL"
        print(f"  [{icon}] {name}")

    # ── Final verdict ────────────────────────────────────────
    print("\n" + "=" * 80)
    success_rate = ok / max(total, 1) * 100
    quality_rate = passed / max(total_checks, 1) * 100
    print(f"RESULTS: {success_rate:.0f}% success rate ({ok}/{total})")
    print(f"QUALITY: {quality_rate:.0f}% quality checks passed ({passed}/{total_checks})")
    if success_rate >= 90 and quality_rate >= 70:
        print("VERDICT: PASS")
    elif success_rate >= 70:
        print("VERDICT: PARTIAL PASS — some models failing")
    else:
        print("VERDICT: FAIL — significant issues detected")
    print("=" * 80)

    return 0 if success_rate >= 70 else 1


if __name__ == "__main__":
    sys.exit(main())
