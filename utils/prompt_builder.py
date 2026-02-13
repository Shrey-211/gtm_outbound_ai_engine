def build_prompt(row, segment, company_size="unknown"):
    """
    Build the outbound cold-email prompt (Scenario A).
    Personalization: PMS, property type, region, company size.
    """

    pms = row.get("PMS") or "Not specified"
    property_type = row.get("type_of_properties_managed") or "Not specified"
    region = row.get("region") or "Not specified"

    base_template = f"""
        You are an outbound SDR at PriceLabs. Generate one short, personalized cold email.

        Contact (use these for personalization):
        - First Name: {row.get("first_name")}
        - Company: {row.get("company_name")}
        - PMS: {pms}
        - Property type: {property_type}
        - Region: {region}
        - Company size (by listing count): {company_size}

        Segment (use for tone/angle): {segment}

        Rules:
        - Under 120 words. One clear CTA. No fluff. Sound human, not AI.
        - Reference their PMS, property type, or region where it fits naturally.
        """

    return base_template.strip()