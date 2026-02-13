import os
import sys
from pathlib import Path

from dotenv import load_dotenv

import pandas as pd

# Load .env from repo root so OPENAI_API_KEY is set
_REPO_ROOT = Path(__file__).resolve().parent
load_dotenv(_REPO_ROOT / ".env")

# Run from repo root: python main.py
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from utils.filter_cold_outreach import split_cold_outreach_contacts
from utils.segmentation import segment_contact, get_company_size
from utils.prompt_builder import build_prompt
from utils.ai_engine import generate_email


def _run_pipeline(contacts: pd.DataFrame, limit: int, contact_type: str) -> tuple[pd.DataFrame, float]:
    """Run segment -> prompt -> generate for a contact list. Uses different email copy for prospect vs lead."""
    results = []
    total_cost = 0.0
    for _, row in contacts.head(limit).iterrows():
        segment = segment_contact(row)
        company_size = get_company_size(row)
        prompt = build_prompt(row, segment, company_size=company_size, contact_type=contact_type)
        result = generate_email(prompt)

        total_cost += result["cost_usd"]
        results.append({
            "type": contact_type,
            "email": row["email"],
            "segment": segment,
            "generated_email": result["content"],
            "model": result["model"],
            "input_tokens": result["input_tokens"],
            "output_tokens": result["output_tokens"],
            "total_tokens": result["total_tokens"],
            "cost_usd": result["cost_usd"],
        })
    return pd.DataFrame(results), total_cost


def run():
    csv_path = os.environ.get("CSV_PATH", _REPO_ROOT / "data" / "database.csv")
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(
            f"CSV not found: {csv_path}. Set CSV_PATH or place pricelabs_gtm_database_sample.csv in data/ as database.csv"
        )

    df = pd.read_csv(csv_path)
    split = split_cold_outreach_contacts(df)
    prospects = split.prospects
    leads = split.leads

    limit = int(os.environ.get("OUTBOUND_LIMIT", "5"))
    all_results = []
    total_cost = 0.0

    if not prospects.empty:
        out_prospects, cost_p = _run_pipeline(prospects, limit, "prospect")
        total_cost += cost_p
        all_results.append(out_prospects)
        out_path_p = _REPO_ROOT / "generated_emails_prospects.csv"
        out_prospects.to_csv(out_path_p, index=False)
        print(f"Prospects: {len(out_prospects)} emails -> {out_path_p} (${cost_p:.4f})")

    if not leads.empty:
        out_leads, cost_l = _run_pipeline(leads, limit, "lead")
        total_cost += cost_l
        all_results.append(out_leads)
        out_path_l = _REPO_ROOT / "generated_emails_leads.csv"
        out_leads.to_csv(out_path_l, index=False)
        print(f"Leads: {len(out_leads)} emails -> {out_path_l} (${cost_l:.4f})")

    if all_results:
        combined = pd.concat(all_results, ignore_index=True)
        combined_path = _REPO_ROOT / "generated_emails.csv"
        combined.to_csv(combined_path, index=False)
        print(f"Combined: {combined_path}")
    print(f"Total: ${total_cost:.4f} USD")

if __name__ == "__main__":
    run()