import pandas as pd
import yaml
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_PATH = _REPO_ROOT / "config.yml"


# ── Helpers ─────────────────────────────────────────────────────────────

def _to_bool(series: pd.Series) -> pd.Series:
    """Convert TRUE / FALSE string columns to real booleans."""
    return series.astype(str).str.strip().str.upper() == "TRUE"


def _load_config() -> dict:
    """Load filter flags from config.yml."""
    with open(_CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


# ── Stage filter (eligibility gate) ────────────────────────────────────

def filter_eligible_contacts(df: pd.DataFrame) -> pd.DataFrame:
    """
    Deterministic eligibility gate — only contacts that are safe to
    cold-outreach survive.  Each rule can be toggled on/off in config.yml.

    Available rules:
        type               == 'prospect'
        Unsubscribed       == FALSE
        is_blocked_domain  == FALSE
        total_emails_sent  == 0

    Existing users, churned customers, suppressed contacts, and anyone
    who has already been emailed are removed *before* any AI touches
    the data.
    """
    config = _load_config()
    total = len(df)
    print(f"[FILTER] Applying eligibility rules on {total} contacts …")

    # Start with a mask that passes everyone; each enabled rule narrows it
    mask = pd.Series(True, index=df.index)

    if config.get("type", True):
        rule = df["type"].astype(str).str.strip().str.lower() == "prospect"
        print(f"[FILTER]   ├─ type == 'prospect'        : {rule.sum()} pass")
        mask &= rule
    else:
        print(f"[FILTER]   ├─ type == 'prospect'        : SKIPPED (disabled in config)")

    if config.get("Unsubscribed", True):
        rule = ~_to_bool(df["Unsubscribed"])
        print(f"[FILTER]   ├─ Unsubscribed == FALSE      : {rule.sum()} pass")
        mask &= rule
    else:
        print(f"[FILTER]   ├─ Unsubscribed == FALSE      : SKIPPED (disabled in config)")

    if config.get("is_blocked_domain", True):
        rule = ~_to_bool(df["is_blocked_domain"])
        print(f"[FILTER]   ├─ is_blocked_domain == FALSE  : {rule.sum()} pass")
        mask &= rule
    else:
        print(f"[FILTER]   ├─ is_blocked_domain == FALSE  : SKIPPED (disabled in config)")

    if config.get("total_emails_sent", True):
        rule = pd.to_numeric(df["total_emails_sent"], errors="coerce").fillna(0) == 0
        print(f"[FILTER]   ├─ total_emails_sent == 0      : {rule.sum()} pass")
        mask &= rule
    else:
        print(f"[FILTER]   ├─ total_emails_sent == 0      : SKIPPED (disabled in config)")

    filtered = df.loc[mask].reset_index(drop=True)
    dropped = total - len(filtered)
    print(f"[FILTER]   └─ Combined: {len(filtered)} eligible, "
          f"{dropped} dropped")

    return filtered


# ── Firmographic segment assignment ────────────────────────────────────

def _assign_segment(row: pd.Series) -> str:
    """
    Deterministic, rule-based firmographic segment for one contact.

    Priority order (first match wins):
      1. enterprise   — MU_count >= 50, non-generic domain
      2. growth_pms   — PMS present, 10 <= MU_count <= 49
      3. early_stage   — is_generic_domain == TRUE, MU_count < 10
      4. general       — everything else that passed the stage filter
    """
    try:
        mu = int(row.get("MU_count") or 0)
    except (TypeError, ValueError):
        mu = 0

    is_generic = str(row.get("is_generic_domain", "")).strip().upper() == "TRUE"

    pms_raw = str(row.get("PMS", "")).strip()
    has_pms = bool(pms_raw) and pms_raw.lower() not in ("", "nan", "none")

    # 1. Enterprise
    if mu >= 50 and not is_generic:
        return "enterprise"

    # 2. Growth PMS
    if has_pms and 10 <= mu <= 49:
        return "growth_pms"

    # 3. Early Stage / Generic Domain
    if is_generic and mu < 10:
        return "early_stage"

    # 4. Fallback
    return "general"


def assign_firmographic_segments(df: pd.DataFrame) -> pd.DataFrame:
    """Add a ``firmographic_segment`` column to *df*."""
    print(f"[SEGMENT] Assigning firmographic segments to {len(df)} contacts …")
    df = df.copy()
    df["firmographic_segment"] = df.apply(_assign_segment, axis=1)

    counts = df["firmographic_segment"].value_counts().to_dict()
    for seg, cnt in sorted(counts.items()):
        print(f"[SEGMENT]   ├─ {seg:15s} : {cnt}")
    print(f"[SEGMENT]   └─ Total: {len(df)}")
    return df


# ── Public entry point ─────────────────────────────────────────────────

def load_cold_outreach_contacts(csv_path: Path | str) -> pd.DataFrame:
    """Load → filter → segment.  Returns only outreach-ready contacts."""
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    print()
    print("=" * 64)
    print("  STAGE 1 · DATA LOAD")
    print("=" * 64)
    df = pd.read_csv(csv_path)
    print(f"[LOAD] Loaded {len(df)} rows from {csv_path.name}")
    print(f"[LOAD] Columns: {list(df.columns)}")

    print()
    print("=" * 64)
    print("  STAGE 2 · ELIGIBILITY FILTER  (deterministic, no AI)")
    print("=" * 64)
    df = filter_eligible_contacts(df)

    print()
    print("=" * 64)
    print("  STAGE 3 · FIRMOGRAPHIC SEGMENTATION  (deterministic, no AI)")
    print("=" * 64)
    df = assign_firmographic_segments(df)

    print()
    return df
