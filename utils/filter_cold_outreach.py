import pandas as pd
from pathlib import Path


def load_cold_outreach_contacts(csv_path: Path | str) -> pd.DataFrame:
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")
    return pd.read_csv(csv_path)
