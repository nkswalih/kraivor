COST_TABLE = {
    ("openrouter", "google/gemini-flash-1.5"): (0.000075, 0.000300),
    ("openrouter", "groq/llama3-70b"): (0.00059, 0.00079),
    ("openrouter", "deepseek/deepseek-coder"): (0.00014, 0.00028),
    ("openrouter", "openai/gpt-4o-mini"): (0.00015, 0.00060),
    ("openrouter", "anthropic/claude-3.5-sonnet"): (0.003, 0.015),
    ("openrouter", "openai/gpt-4o"): (0.005, 0.015),
    ("groq", "llama3-70b"): (0.0, 0.0),
    ("google", "gemini-flash-1.5"): (0.0, 0.0),
    ("local", "all-MiniLM-L6-v2"): (0, 0),
}


def estimate_cost(
    provider: str, model: str, input_tokens: int, output_tokens: int
) -> float:
    key = (provider, model)
    if key not in COST_TABLE:
        return 0.0
    input_cost, output_cost = COST_TABLE[key]
    return (input_tokens / 1000 * input_cost) + (output_tokens / 1000 * output_cost)
