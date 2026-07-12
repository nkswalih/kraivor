from fastapi import FastAPI
from prometheus_client import Counter, Gauge, Histogram, make_asgi_app

http_requests = Counter(
    "ai_http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
)

http_duration = Histogram(
    "ai_http_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1, 2, 5, 10, 30],
)

llm_calls = Counter(
    "ai_llm_calls_total", "LLM API calls", ["provider", "model", "status"]
)

llm_duration = Histogram(
    "ai_llm_duration_seconds",
    "LLM call duration",
    ["model"],
    buckets=[0.5, 1, 2, 5, 10, 30, 60],
)

llm_cost = Counter(
    "ai_llm_cost_total_usd", "Total LLM cost in USD", ["model", "user_id"]
)

llm_tokens = Counter("ai_llm_tokens_total", "Tokens processed", ["model", "type"])

agent_calls = Counter(
    "ai_agent_calls_total", "Agent invocations", ["agent_name", "status"]
)

agent_duration = Histogram(
    "ai_agent_duration_seconds",
    "Agent execution duration",
    ["agent_name"],
    buckets=[0.5, 1, 2, 5, 10, 30, 60],
)

cache_hits = Counter("ai_cache_hits_total", "Cache hits", ["cache_type"])

cache_misses = Counter("ai_cache_misses_total", "Cache misses", ["cache_type"])

active_streams = Gauge("ai_active_streams", "Active SSE streams")
active_keys = Gauge("ai_active_api_keys", "Active API keys")

metrics_app = make_asgi_app()


def setup_metrics(app: FastAPI | None = None) -> None:
    if app is not None:
        app.mount("/metrics", metrics_app)
