def segment_contact(row):
    """
    Returns segment label based on deterministic business rules.
    """

    pms = str(row.get("PMS", "")).lower()
    mu_count = row.get("MU_count", 0) or 0
    region = str(row.get("region", "")).lower()
    generic_domain = row.get("is_generic_domain", False)

    if mu_count >= 50:
        return "enterprise"

    if "hostaway" in pms and mu_count >= 10:
        return "growth_hostaway"

    if generic_domain:
        return "early_stage_generic"

    return "standard_smb"