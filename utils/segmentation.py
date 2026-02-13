import pandas as pd

# ── Property-type mapping (secondary personalisation dimension) ─────────
_PROPERTY_TYPE_SEGMENTS = {
    "vacation rental": "vacation_rental",
    "short-term rental": "short_term_rental",
    "hotel": "hotel",
    "boutique hotel": "boutique_hotel",
    "serviced apartment": "serviced_apartment",
    "mixed": "mixed_portfolio",
}


# ── Company-size band (aligned with firmographic thresholds) ────────────

def _company_size_band(mu_count):
    try:
        n = int(mu_count or 0)
    except (TypeError, ValueError):
        return "unknown"
    if n >= 50:
        return "enterprise"
    if 10 <= n <= 49:
        return "growth"
    if 1 <= n <= 9:
        return "small"
    return "unknown"


# ── Segment accessors ──────────────────────────────────────────────────

def segment_contact(row):
    """Return the firmographic segment pre-assigned by filter_cold_outreach.

    Falls back to property-type segmentation when the column is absent
    (e.g. in unit tests or ad-hoc usage).
    """
    seg = row.get("firmographic_segment")
    if seg and not pd.isna(seg) and str(seg).strip():
        segment = str(seg).strip()
    else:
        # Fallback: property-type segmentation
        raw = row.get("type_of_properties_managed")
        if pd.isna(raw) or not str(raw).strip():
            segment = "general"
        else:
            segment = _PROPERTY_TYPE_SEGMENTS.get(str(raw).strip().lower(), "general")

    print(f"[SEGMENT-LOOKUP] {row.get('email', '?'):40s} → {segment}")
    return segment


def get_property_type_segment(row):
    """Secondary dimension: what kind of properties they manage."""
    raw = row.get("type_of_properties_managed")
    if pd.isna(raw) or not str(raw).strip():
        return "general"
    return _PROPERTY_TYPE_SEGMENTS.get(str(raw).strip().lower(), "general")


def get_company_size(row):
    size = _company_size_band(row.get("MU_count"))
    print(f"[SIZE-LOOKUP]    {row.get('email', '?'):40s} → {size} "
          f"(MU_count={row.get('MU_count', '?')})")
    return size
