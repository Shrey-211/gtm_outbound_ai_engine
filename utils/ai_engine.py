import os
from openai import OpenAI
from pydantic import BaseModel


class ColdEmail(BaseModel):
    subject: str
    greetings: str
    body: str


DEFAULT_SIGNATURE = "Best regards,\nShreyas Jadhav\nPriceLabs"

MODEL_PRICING = {
    "gpt-4.1": (2.00, 8.00),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1-nano": (0.10, 0.40),
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
}

MODEL = os.getenv("OPENAI_MODEL")
_DEFAULT_PRICE = (2.00, 8.00)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def _get_pricing(model: str) -> tuple[float, float]:
    if not model:
        return _DEFAULT_PRICE
    model_lower = model.strip().lower()
    for key in sorted(MODEL_PRICING.keys(), key=len, reverse=True):
        if key == model_lower or key in model_lower:
            return MODEL_PRICING[key]
    return _DEFAULT_PRICE


def generate_email(prompt: str) -> dict:
    response = client.beta.chat.completions.parse(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format=ColdEmail,
        temperature=0.4,
        top_p=0.9,
    )

    email: ColdEmail = response.choices[0].message.parsed
    usage = response.usage
    prompt_tokens = usage.prompt_tokens if usage else 0
    completion_tokens = usage.completion_tokens if usage else 0
    total_tokens = usage.total_tokens if usage else (prompt_tokens + completion_tokens)

    input_per_1m, output_per_1m = _get_pricing(MODEL)
    cost_usd = (prompt_tokens / 1_000_000 * input_per_1m) + (
        completion_tokens / 1_000_000 * output_per_1m
    )

    return {
        "subject": email.subject,
        "greetings": email.greetings,
        "body": email.body,
        "signature": DEFAULT_SIGNATURE,
        "model": MODEL,
        "input_tokens": prompt_tokens,
        "output_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "cost_usd": round(cost_usd, 6),
    }
