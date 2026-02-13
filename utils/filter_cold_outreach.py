import pandas as pd
from pathlib import Path

# ── Enterprise job-title keywords (case-insensitive substring match) ────
_ENTERPRISE_TITLE_KEYWORDS = {"founder", "ceo", "revenue", "director"}


# ── Helpers ─────────────────────────────────────────────────────────────

def _to_bool(series: pd.Series) -> pd.Series:
    """Convert TRUE / FALSE string columns to real booleans."""
    return series.astype(str).str.strip().str.upper() == "TRUE"


def _has_leadership_title(title) -> bool:
    """True when *title* contains at least one enterprise keyword."""
    if pd.isna(title) or not str(title).strip():
        return False
    lower = str(title).lower()
    return any(kw in lower for kw in _ENTERPRISE_TITLE_KEYWORDS)


# ── Stage filter (eligibility gate) ────────────────────────────────────

def filter_eligible_contacts(df: pd.DataFrame) -> pd.DataFrame:
    """
    Deterministic eligibility gate — only contacts that are safe to
    cold-outreach survive:

        type               == 'prospect'
        Unsubscribed       == FALSE
        is_blocked_domain  == FALSE
        total_emails_sent  == 0

    Existing users, churned customers, suppressed contacts, and anyone
    who has already been emailed are removed *before* any AI touches
    the data.
    """
    total = len(df)
    print(f"[FILTER] Applying eligibility rules on {total} contacts …")

    is_prospect = df["type"].astype(str).str.strip().str.lower() == "prospect"
    not_unsubscribed = ~_to_bool(df["Unsubscribed"])
    not_blocked = ~_to_bool(df["is_blocked_domain"])
    never_emailed = pd.to_numeric(df["total_emails_sent"], errors="coerce").fillna(0) == 0

    # Log each rule independently so you can see where contacts drop
    print(f"[FILTER]   ├─ type == 'prospect'        : {is_prospect.sum()} pass")
    print(f"[FILTER]   ├─ Unsubscribed == FALSE      : {not_unsubscribed.sum()} pass")
    print(f"[FILTER]   ├─ is_blocked_domain == FALSE  : {not_blocked.sum()} pass")
    print(f"[FILTER]   ├─ total_emails_sent == 0      : {never_emailed.sum()} pass")

    mask = is_prospect & not_unsubscribed & not_blocked & never_emailed
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
      1. enterprise   — MU_count >= 50, non-generic domain, leadership title
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

    title = row.get("job_title", "")

    # 1. Enterprise
    if mu >= 50 and not is_generic and _has_leadership_title(title):
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
