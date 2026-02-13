import os
import json
import time
from pathlib import Path
from openai import OpenAI
from pydantic import BaseModel


class ColdEmail(BaseModel):
    subject: str
    greetings: str
    body: str


DEFAULT_SIGNATURE = "Best regards,\nShreyas Jadhav\nPriceLabs"

BATCH_THRESHOLD = 10

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


def _cold_email_response_format() -> dict:
    schema = ColdEmail.model_json_schema()
    schema["additionalProperties"] = False
    schema.pop("title", None)
    for prop in schema.get("properties", {}).values():
        prop.pop("title", None)
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "ColdEmail",
            "strict": True,
            "schema": schema,
        },
    }


def _build_result(email: ColdEmail, prompt_tokens: int, completion_tokens: int) -> dict:
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
        "total_tokens": prompt_tokens + completion_tokens,
        "cost_usd": round(cost_usd, 6),
    }


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
    return _build_result(email, prompt_tokens, completion_tokens)


# --- Batch API ---

def prepare_batch_file(prompts: list[str], batch_path: Path) -> Path:
    response_format = _cold_email_response_format()
    with open(batch_path, "w", encoding="utf-8") as f:
        for i, prompt in enumerate(prompts):
            request = {
                "custom_id": f"email-{i}",
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": response_format,
                    "temperature": 0.4,
                    "top_p": 0.9,
                },
            }
            f.write(json.dumps(request) + "\n")
    return batch_path


def submit_batch(batch_path: Path) -> str:
    with open(batch_path, "rb") as f:
        batch_file = client.files.create(file=f, purpose="batch")
    batch = client.batches.create(
        input_file_id=batch_file.id,
        endpoint="/v1/chat/completions",
        completion_window="24h",
    )
    print(f"[BATCH] Submitted batch {batch.id} with file {batch_file.id}")
    return batch.id


def poll_batch(batch_id: str, poll_interval: int = 15) -> object:
    while True:
        batch = client.batches.retrieve(batch_id)
        completed = batch.request_counts.completed if batch.request_counts else 0
        total = batch.request_counts.total if batch.request_counts else 0
        failed = batch.request_counts.failed if batch.request_counts else 0
        print(f"[BATCH] Status: {batch.status} | Progress: {completed}/{total} | Failed: {failed}")

        if batch.status == "completed":
            return batch
        if batch.status in ("failed", "expired", "cancelled"):
            raise RuntimeError(f"Batch {batch.status}: {batch.errors}")
        time.sleep(poll_interval)


def parse_batch_results(batch) -> list[dict]:
    result_content = client.files.content(batch.output_file_id)
    results = {}
    for line in result_content.text.strip().split("\n"):
        data = json.loads(line)
        idx = int(data["custom_id"].split("-")[1])
        response_body = data["response"]["body"]

        content = json.loads(response_body["choices"][0]["message"]["content"])
        email = ColdEmail(**content)

        usage = response_body.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)

        results[idx] = _build_result(email, prompt_tokens, completion_tokens)

    return [results[i] for i in sorted(results.keys())]
