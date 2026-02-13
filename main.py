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
    MODEL,
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
    print(f"[PIPELINE] Mode: REALTIME  ({len(contacts)} contacts, "
          f"<= {BATCH_THRESHOLD} threshold)")
    print(f"[PIPELINE] Each contact → segment → prompt → AI call → email")
    print()

    results = []
    total_cost = 0.0
    for i, (_, row) in enumerate(contacts.iterrows(), 1):
        email_addr = row.get("email", "")
        print(f"── Contact {i}/{len(contacts)}: {email_addr} " + "─" * 30)

        segment = segment_contact(row)
        company_size = get_company_size(row)
        prompt = build_prompt(row, segment, company_size=company_size)
        print(f"[PROMPT]         Prompt length: {len(prompt)} chars")

        result = generate_email(prompt)
        total_cost += result["cost_usd"]
        results.append(_build_row(email_addr, segment, result))
        print(f"[DONE]   ✓ Email generated for {email_addr}  "
              f"(running total: ${total_cost:.6f})")
        print()

    return pd.DataFrame(results), total_cost


def _run_batch_pipeline(contacts: pd.DataFrame) -> tuple[pd.DataFrame, float]:
    count = len(contacts)
    print(f"[PIPELINE] Mode: BATCH  ({count} contacts, "
          f"> {BATCH_THRESHOLD} threshold)")
    print(f"[PIPELINE] All prompts built first → single batch AI call → parse")
    print()

    print("── Building prompts (no AI yet) " + "─" * 33)
    prompts = []
    metadata = []
    for i, (_, row) in enumerate(contacts.iterrows(), 1):
        email_addr = row.get("email", "")
        print(f"  [{i}/{count}] {email_addr}")
        segment = segment_contact(row)
        company_size = get_company_size(row)
        prompt = build_prompt(row, segment, company_size=company_size)
        print(f"[PROMPT]         Prompt length: {len(prompt)} chars")
        prompts.append(prompt)
        metadata.append({"email": email_addr, "segment": segment})

    print()
    print("── Submitting to OpenAI Batch API (AI starts here) " + "─" * 13)
    batch_dir = _REPO_ROOT / "tmp"
    batch_dir.mkdir(parents=True, exist_ok=True)
    batch_path = batch_dir / f"batch_input_{time.time()}.jsonl"

    prepare_batch_file(prompts, batch_path)
    batch_id = submit_batch(batch_path)
    batch = poll_batch(batch_id)
    batch_results = parse_batch_results(batch)

    print()
    print("── Assembling results " + "─" * 43)
    results = []
    total_cost = 0.0
    for meta, result in zip(metadata, batch_results):
        total_cost += result["cost_usd"]
        results.append(_build_row(meta["email"], meta["segment"], result))
        print(f"  ✓ {meta['email']:40s}  segment={meta['segment']:12s}  "
              f"cost=${result['cost_usd']:.6f}")

    return pd.DataFrame(results), total_cost


def run():
    t_start = time.time()

    print()
    print("╔" + "═" * 62 + "╗")
    print("║   GTM OUTBOUND AI ENGINE                                     ║")
    print("╚" + "═" * 62 + "╝")
    print()

    csv_path = os.environ.get("CSV_PATH", _REPO_ROOT / "data" / "database.csv")
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    # ── Stages 1-3 happen inside load_cold_outreach_contacts ────────────
    contacts = load_cold_outreach_contacts(csv_path)

    limit = int(os.environ.get("OUTBOUND_LIMIT", "5"))
    contacts = contacts.head(limit)
    print("=" * 64)
    print("  STAGE 4 · CONTACT LIMIT")
    print("=" * 64)
    print(f"[LIMIT] OUTBOUND_LIMIT={limit}  →  {len(contacts)} contacts to process")
    print()

    # ── Stage 5: AI generation ──────────────────────────────────────────
    print("=" * 64)
    print("  STAGE 5 · AI EMAIL GENERATION  (AI is invoked here)")
    print("=" * 64)
    print(f"[AI-CONFIG] Model: {MODEL}")
    print(f"[AI-CONFIG] Batch threshold: {BATCH_THRESHOLD}")
    print()

    if len(contacts) > BATCH_THRESHOLD:
        out_emails, total_cost = _run_batch_pipeline(contacts)
    else:
        out_emails, total_cost = _run_realtime_pipeline(contacts)

    # ── Stage 6: Save results ───────────────────────────────────────────
    print("=" * 64)
    print("  STAGE 6 · SAVE RESULTS")
    print("=" * 64)
    out_dir = _REPO_ROOT / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"generated_emails_{time.time()}.csv"
    out_emails.to_csv(out_path, index=False)
    print(f"[SAVE] {len(out_emails)} emails → {out_path}")

    elapsed = time.time() - t_start
    print()
    print("=" * 64)
    print("  SUMMARY")
    print("=" * 64)
    seg_dist = out_emails["segment"].value_counts().to_dict()
    print(f"[SUMMARY] Emails generated : {len(out_emails)}")
    print(f"[SUMMARY] Segment breakdown: {seg_dist}")
    print(f"[SUMMARY] Total cost       : ${total_cost:.6f} USD")
    print(f"[SUMMARY] Wall time        : {elapsed:.1f}s")
    print(f"[SUMMARY] Output file      : {out_path}")
    print()


if __name__ == "__main__":
    run()
