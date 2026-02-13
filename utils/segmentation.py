def _company_size_band(mu_count):
    """Derive company size band from managed-unit count (proxy for scale)."""
    try:
        n = int(mu_count or 0)
    except (TypeError, ValueError):
        return "unknown"
    if n >= 50:
        return "enterprise"
    if n >= 11:
        return "mid_market"
    if n >= 1:
        return "small"
    return "unknown"  # prospects often have 0


def segment_contact(row):
    """
    Returns segment label based on deterministic business rules.
    Used for outbound: PMS, property type, region, and scale (MU_count) inform targeting.
    """

    pms = str(row.get("PMS", "")).strip().lower()
    mu_count = row.get("MU_count", 0) or 0
    region = str(row.get("region", "")).strip().lower()
    property_type = str(row.get("type_of_properties_managed", "")).strip().lower()
    generic_domain = row.get("is_generic_domain", False)

    if mu_count >= 50:
        return "enterprise"

    if pms and "hostaway" in pms and mu_count >= 10:
        return "growth_hostaway"

    if generic_domain:
        return "early_stage_generic"

    return "standard_smb"


def get_company_size(row):
    """Return company size band for use in prompts (Scenario A: company size)."""
    return _company_size_band(row.get("MU_count"))