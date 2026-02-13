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

from utils.segmentation import segment_contact, get_company_size
from utils.prompt_builder import build_prompt
from utils.ai_engine import generate_email


def run():
    csv_path = os.environ.get("CSV_PATH", _REPO_ROOT / "data" / "database.csv")
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(
            f"CSV not found: {csv_path}. Set CSV_PATH or place pricelabs_gtm_database_sample.csv in data/ as database.csv"
        )

    df = pd.read_csv(csv_path)
    prospects = df[df["type"] == "prospect"]

    limit = int(os.environ.get("OUTBOUND_LIMIT", "5"))
    results = []

    total_cost = 0.0
    for _, row in prospects.head(limit).iterrows():
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

    output_df = pd.DataFrame(results)
    out_path = _REPO_ROOT / "generated_emails.csv"
    output_df.to_csv(out_path, index=False)
    print(f"Done. Emails saved to {out_path}")
    print(f"Total: {output_df['total_tokens'].sum()} tokens, ${total_cost:.4f} USD")

if __name__ == "__main__":
    run()