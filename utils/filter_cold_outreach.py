"""
Filter the contact database for cold outreach.

Cold emails are sent only to prospects and leads; trials and customers are excluded.
Prospects and leads are kept separate so you can draft different emails for each.
"""

import pandas as pd
from pathlib import Path
from typing import NamedTuple


class ColdOutreachSplit(NamedTuple):
    """Prospects and leads as separate DataFrames for separate email drafts."""

    prospects: pd.DataFrame
    leads: pd.DataFrame


def split_cold_outreach_contacts(df: pd.DataFrame) -> ColdOutreachSplit:
    """
    Split contacts into prospects and leads. Data is kept separate for different email drafts.

    Args:
        df: Full contact DataFrame with a "type" column.

    Returns:
        ColdOutreachSplit(prospects=..., leads=...) with copies of the relevant rows.
    """
    if "type" not in df.columns:
        raise ValueError('DataFrame must have a "type" column')

    t = df["type"].astype(str).str.strip().str.lower()
    prospects = df.loc[t == "prospect"].copy()
    leads = df.loc[t == "lead"].copy()

    return ColdOutreachSplit(prospects=prospects, leads=leads)


def load_and_split_cold_outreach(
    csv_path: Path | str,
    prospects_path: Path | str | None = None,
    leads_path: Path | str | None = None,
) -> ColdOutreachSplit:
    """
    Load database CSV and split into prospects and leads; optionally save each to CSV.

    Args:
        csv_path: Path to database CSV (e.g. data/database.csv).
        prospects_path: If set, write prospects to this CSV.
        leads_path: If set, write leads to this CSV.

    Returns:
        ColdOutreachSplit(prospects=..., leads=...).
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)
    split = split_cold_outreach_contacts(df)

    if prospects_path is not None:
        Path(prospects_path).parent.mkdir(parents=True, exist_ok=True)
        split.prospects.to_csv(prospects_path, index=False)
    if leads_path is not None:
        Path(leads_path).parent.mkdir(parents=True, exist_ok=True)
        split.leads.to_csv(leads_path, index=False)

    return split
