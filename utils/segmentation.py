"""
Segment contacts by property type for targeted cold outreach.

Primary axis: type_of_properties_managed — determines which PriceLabs
value props and angles to highlight in the email.
Company size (from MU_count) is passed separately to the prompt builder.
"""


# Canonical segment labels keyed by lowercase property type
_PROPERTY_TYPE_SEGMENTS = {
    "vacation rental": "vacation_rental",
    "short-term rental": "short_term_rental",
    "hotel": "hotel",
    "boutique hotel": "boutique_hotel",
    "serviced apartment": "serviced_apartment",
    "mixed": "mixed_portfolio",
}


def _company_size_band(mu_count):
    """Derive company size band from managed-unit count (proxy for scale)."""
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
    """
    Return a segment label based on the contact's property type.

    Maps type_of_properties_managed to a canonical segment used by the
    prompt builder to pick the right email angle.
    Falls back to 'general' when the property type is missing or unrecognised.
    """
    raw = str(row.get("type_of_properties_managed", "")).strip().lower()
    return _PROPERTY_TYPE_SEGMENTS.get(raw, "general")


def get_company_size(row):
    """Return company size band for use in prompts."""
    return _company_size_band(row.get("MU_count"))
