import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
import time

# Load .env from repo root so OPENAI_API_KEY is set
_REPO_ROOT = Path(__file__).resolve().parent
load_dotenv(_REPO_ROOT / ".env")

# Run from repo root: python main.py
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from utils.filter_cold_outreach import load_cold_outreach_contacts
from utils.segmentation import segment_contact, get_company_size
from utils.prompt_builder import build_prompt
from utils.ai_engine import generate_email


def _run_pipeline(contacts: pd.DataFrame, limit: int) -> tuple[pd.DataFrame, float]:
    """Run segment -> prompt -> generate for cold outreach contacts."""
    results = []
    total_cost = 0.0
    for _, row in contacts.head(limit).iterrows():
        segment = segment_contact(row)
        company_size = get_company_size(row)
        prompt = build_prompt(row, segment, company_size=company_size)
        result = generate_email(prompt)

        total_cost += result["cost_usd"]
        results.append({
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
    csv_path = os.environ.get("CSV_PATH", _REPO_ROOT / "data" / "database_dummy.csv")
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(
            f"CSV not found: {csv_path}. Set CSV_PATH or place pricelabs_gtm_database_sample.csv in data/ as database.csv"
        )

    contacts = load_cold_outreach_contacts(csv_path)

    limit = int(os.environ.get("OUTBOUND_LIMIT", "5"))

    out_emails, total_cost = _run_pipeline(contacts, limit)

    out_path = _REPO_ROOT / f"generated_emails_{time.time()}.csv"
    out_emails.to_csv(out_path, index=False)
    print(f"Cold outreach: {len(out_emails)} emails -> {out_path} (${total_cost:.4f})")
    print(f"Total: ${total_cost:.4f} USD")

if __name__ == "__main__":
    run()