import os
from openai import OpenAI

# Standard tier pricing per 1M tokens (OpenAI platform.openai.com/docs/pricing)
# Input and output USD per 1M tokens
MODEL_PRICING = {
    "gpt-4.1": (2.00, 8.00),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1-nano": (0.10, 0.40),
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
}

MODEL = os.getenv("OPENAI_MODEL")
_DEFAULT_PRICE = (2.00, 8.00)  # gpt-4.1 standard

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def _get_pricing(model: str) -> tuple[float, float]:
    """Return (input_per_1m, output_per_1m) USD for the model."""
    if not model:
        return _DEFAULT_PRICE
    model_lower = model.strip().lower()
    # Prefer exact match, then longest key that appears in model (so gpt-4.1-mini before gpt-4.1)
    for key in sorted(MODEL_PRICING.keys(), key=len, reverse=True):
        if key == model_lower or key in model_lower:
            return MODEL_PRICING[key]
    return _DEFAULT_PRICE


def generate_email(prompt):
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        top_p=0.9,
    )

    content = response.choices[0].message.content
    usage = response.usage
    prompt_tokens = usage.prompt_tokens if usage else 0
    completion_tokens = usage.completion_tokens if usage else 0
    total_tokens = usage.total_tokens if usage else (prompt_tokens + completion_tokens)

    input_per_1m, output_per_1m = _get_pricing(MODEL)
    cost_usd = (prompt_tokens / 1_000_000 * input_per_1m) + (
        completion_tokens / 1_000_000 * output_per_1m
    )

    return {
        "content": content,
        "model": MODEL,
        "input_tokens": prompt_tokens,
        "output_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "cost_usd": round(cost_usd, 6),
    }