import os
from openai import OpenAI

# gpt-4o-mini pricing per 1M tokens (as of 2024–2025)
MODEL = "gpt-4o-mini"
INPUT_PRICE_PER_1M = 0.15   # USD
OUTPUT_PRICE_PER_1M = 0.60   # USD

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_email(prompt):
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )

    content = response.choices[0].message.content
    usage = response.usage
    prompt_tokens = usage.prompt_tokens if usage else 0
    completion_tokens = usage.completion_tokens if usage else 0
    total_tokens = usage.total_tokens if usage else (prompt_tokens + completion_tokens)

    cost_usd = (prompt_tokens / 1_000_000 * INPUT_PRICE_PER_1M) + (
        completion_tokens / 1_000_000 * OUTPUT_PRICE_PER_1M
    )

    return {
        "content": content,
        "model": MODEL,
        "input_tokens": prompt_tokens,
        "output_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "cost_usd": round(cost_usd, 6),
    }