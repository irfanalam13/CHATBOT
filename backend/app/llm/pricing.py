"""Token pricing table ($ per 1M tokens) for cost tracking."""
from __future__ import annotations

# (input_per_mtok, output_per_mtok)
PRICING: dict[str, tuple[float, float]] = {
    # Anthropic
    "claude-fable-5": (10.0, 50.0),
    "claude-opus-4-8": (5.0, 25.0),
    "claude-opus-4-7": (5.0, 25.0),
    "claude-opus-4-6": (5.0, 25.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
    # OpenAI
    "gpt-4o": (2.5, 10.0),
    "gpt-4o-mini": (0.15, 0.6),
    # Google
    "gemini-1.5-pro": (1.25, 5.0),
    "gemini-1.5-flash": (0.075, 0.30),
    # Embeddings (input only)
    "text-embedding-3-small": (0.02, 0.0),
    "text-embedding-3-large": (0.13, 0.0),
}


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    in_rate, out_rate = PRICING.get(model, (0.0, 0.0))
    return (prompt_tokens / 1_000_000) * in_rate + (completion_tokens / 1_000_000) * out_rate
