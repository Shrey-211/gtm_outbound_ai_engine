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
    print(f"[AI]    ⚡ Calling OpenAI  model={MODEL}  temp=0.4 …")
    t0 = time.time()

    response = client.beta.chat.completions.parse(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format=ColdEmail,
        temperature=0.4,
        top_p=0.9,
    )

    elapsed = time.time() - t0
    email: ColdEmail = response.choices[0].message.parsed
    usage = response.usage
    prompt_tokens = usage.prompt_tokens if usage else 0
    completion_tokens = usage.completion_tokens if usage else 0
    result = _build_result(email, prompt_tokens, completion_tokens)

    print(f"[AI]    ✓ Response in {elapsed:.1f}s  "
          f"tokens={prompt_tokens}+{completion_tokens}={prompt_tokens + completion_tokens}  "
          f"cost=${result['cost_usd']:.6f}")
    print(f"[AI]      subject: {email.subject[:80]}")

    return result


# --- Batch API ---

def prepare_batch_file(prompts: list[str], batch_path: Path) -> Path:
    print(f"[BATCH-PREP] Writing {len(prompts)} requests → {batch_path.name}")
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
    print(f"[BATCH-PREP] Done – {batch_path.stat().st_size / 1024:.1f} KB")
    return batch_path


def submit_batch(batch_path: Path) -> str:
    print(f"[AI]    ⚡ Uploading batch file to OpenAI …")
    with open(batch_path, "rb") as f:
        batch_file = client.files.create(file=f, purpose="batch")
    print(f"[AI]    ⚡ Submitting batch  model={MODEL}  file={batch_file.id} …")
    batch = client.batches.create(
        input_file_id=batch_file.id,
        endpoint="/v1/chat/completions",
        completion_window="24h",
    )
    print(f"[AI]    ✓ Batch created: {batch.id}")
    return batch.id


def poll_batch(batch_id: str, poll_interval: int = 15) -> object:
    print(f"[AI]    ⏳ Polling batch {batch_id} every {poll_interval}s …")
    poll_count = 0
    while True:
        batch = client.batches.retrieve(batch_id)
        completed = batch.request_counts.completed if batch.request_counts else 0
        total = batch.request_counts.total if batch.request_counts else 0
        failed = batch.request_counts.failed if batch.request_counts else 0
        poll_count += 1
        print(f"[AI]    ⏳ Poll #{poll_count}: status={batch.status}  "
              f"progress={completed}/{total}  failed={failed}")

        if batch.status == "completed":
            print(f"[AI]    ✓ Batch completed – {completed} results ready")
            return batch
        if batch.status in ("failed", "expired", "cancelled"):
            raise RuntimeError(f"Batch {batch.status}: {batch.errors}")
        time.sleep(poll_interval)


def parse_batch_results(batch) -> list[dict]:
    print(f"[AI]    Downloading batch results from {batch.output_file_id} …")
    result_content = client.files.content(batch.output_file_id)
    results = {}
    total_cost = 0.0
    for line in result_content.text.strip().split("\n"):
        data = json.loads(line)
        idx = int(data["custom_id"].split("-")[1])
        response_body = data["response"]["body"]

        content = json.loads(response_body["choices"][0]["message"]["content"])
        email = ColdEmail(**content)

        usage = response_body.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)

        result = _build_result(email, prompt_tokens, completion_tokens)
        total_cost += result["cost_usd"]
        results[idx] = result

    print(f"[AI]    ✓ Parsed {len(results)} batch results  "
          f"total_cost=${total_cost:.6f}")
    return [results[i] for i in sorted(results.keys())]
