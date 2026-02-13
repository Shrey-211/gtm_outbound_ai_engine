import pandas as pd

_PROPERTY_TYPE_SEGMENTS = {
    "vacation rental": "vacation_rental",
    "short-term rental": "short_term_rental",
    "hotel": "hotel",
    "boutique hotel": "boutique_hotel",
    "serviced apartment": "serviced_apartment",
    "mixed": "mixed_portfolio",
}


def _company_size_band(mu_count):
    try:
        n = int(mu_count or 0)
    except (TypeError, ValueError):
        return "unknown"
    if n > 50:
        return "enterprise"
    if 6 <= n <= 50:
        return "mid"
    if 1 <= n <= 5:
        return "small"
    return "unknown"


def segment_contact(row):
    raw = row.get("type_of_properties_managed")
    if pd.isna(raw) or not str(raw).strip():
        return "general"
    return _PROPERTY_TYPE_SEGMENTS.get(str(raw).strip().lower(), "general")


def get_company_size(row):
    return _company_size_band(row.get("MU_count"))
