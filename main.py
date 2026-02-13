import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
import time

_REPO_ROOT = Path(__file__).resolve().parent
load_dotenv(_REPO_ROOT / ".env")

if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from utils.filter_cold_outreach import load_cold_outreach_contacts
from utils.segmentation import segment_contact, get_company_size
from utils.prompt_builder import build_prompt
from utils.ai_engine import (
    generate_email,
    prepare_batch_file,
    submit_batch,
    poll_batch,
    parse_batch_results,
    DEFAULT_SIGNATURE,
    BATCH_THRESHOLD,
)


def _build_row(email_addr: str, segment: str, result: dict) -> dict:
    complete_email = f"{result['greetings']}\n\n{result['body']}\n\n{result['signature']}"
    return {
        "email": email_addr,
        "segment": segment,
        "subject": result["subject"],
        "greetings": result["greetings"],
        "body": result["body"],
        "signature": result["signature"],
        "complete_email": complete_email,
        "model": result["model"],
        "input_tokens": result["input_tokens"],
        "output_tokens": result["output_tokens"],
        "total_tokens": result["total_tokens"],
        "cost_usd": result["cost_usd"],
    }


def _run_realtime_pipeline(contacts: pd.DataFrame) -> tuple[pd.DataFrame, float]:
    print(f"[REALTIME] Generating {len(contacts)} emails via realtime API...")
    results = []
    total_cost = 0.0
    for _, row in contacts.iterrows():
        segment = segment_contact(row)
        company_size = get_company_size(row)
        prompt = build_prompt(row, segment, company_size=company_size)
        result = generate_email(prompt)
        total_cost += result["cost_usd"]
        results.append(_build_row(row.get("email", ""), segment, result))
    return pd.DataFrame(results), total_cost


def _run_batch_pipeline(contacts: pd.DataFrame) -> tuple[pd.DataFrame, float]:
    count = len(contacts)
    print(f"[BATCH] {count} emails queued - using OpenAI Batch API (50% cheaper, may take a few minutes)...")

    prompts = []
    metadata = []
    for _, row in contacts.iterrows():
        segment = segment_contact(row)
        company_size = get_company_size(row)
        prompt = build_prompt(row, segment, company_size=company_size)
        prompts.append(prompt)
        metadata.append({"email": row.get("email", ""), "segment": segment})

    batch_dir = _REPO_ROOT / "tmp"
    batch_dir.mkdir(parents=True, exist_ok=True)
    batch_path = batch_dir / f"batch_input_{time.time()}.jsonl"

    prepare_batch_file(prompts, batch_path)
    batch_id = submit_batch(batch_path)
    batch = poll_batch(batch_id)
    batch_results = parse_batch_results(batch)

    results = []
    total_cost = 0.0
    for meta, result in zip(metadata, batch_results):
        total_cost += result["cost_usd"]
        results.append(_build_row(meta["email"], meta["segment"], result))

    return pd.DataFrame(results), total_cost


def run():
    csv_path = os.environ.get("CSV_PATH", _REPO_ROOT / "data" / "database_dummy.csv")
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    contacts = load_cold_outreach_contacts(csv_path)
    limit = int(os.environ.get("OUTBOUND_LIMIT", "5"))
    contacts = contacts.head(limit)

    if len(contacts) > BATCH_THRESHOLD:
        out_emails, total_cost = _run_batch_pipeline(contacts)
    else:
        out_emails, total_cost = _run_realtime_pipeline(contacts)

    out_dir = _REPO_ROOT / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"generated_emails_{time.time()}.csv"
    out_emails.to_csv(out_path, index=False)
    print(f"Done: {len(out_emails)} emails -> {out_path} (${total_cost:.4f})")
    print(f"Total cost: ${total_cost:.4f} USD")


if __name__ == "__main__":
    run()
