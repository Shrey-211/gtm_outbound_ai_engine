"""
Load the contact database for cold outreach.

All contacts in the database are cold outreach targets,
so no type-based filtering is needed.
"""

import pandas as pd
from pathlib import Path


def load_cold_outreach_contacts(csv_path: Path | str) -> pd.DataFrame:
    """
    Load all contacts from the database CSV for cold outreach.

    Args:
        csv_path: Path to database CSV (e.g. data/database.csv).

    Returns:
        DataFrame with all contacts.
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    return pd.read_csv(csv_path)
