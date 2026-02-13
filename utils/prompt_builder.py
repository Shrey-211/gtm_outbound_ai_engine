def build_prompt(row, segment, company_size="unknown"):
    """
    Build the outbound cold-email prompt.

    All contacts are cold (first touch), so the prompt introduces PriceLabs
    with one clear value prop and one CTA.
    """
    pms = row.get("PMS") or "Not specified"
    property_type = row.get("type_of_properties_managed") or "Not specified"
    region = row.get("region") or "Not specified"

    contact_block = f"""
        Contact (use these for personalization):
        - First Name: {row.get("first_name")}
        - Company: {row.get("company_name")}
        - PMS: {pms}
        - Property type: {property_type}
        - Region: {region}
        - Company size (by listing count): {company_size}

        Segment (use for tone/angle): {segment}
        """

    role_and_rules = """
        You are an outbound SDR at PriceLabs. This contact is a cold prospect (first touch). Generate one short, personalized cold email.

        Angle: Introduce PriceLabs briefly. One clear value prop and one CTA (e.g. trial, demo, or resource). No fluff.

        Rules:
        - Under 200 words. One clear CTA. No fluff. Sound human, not AI.
        - Reference their PMS, property type, or region where it fits naturally.
        """

    return (role_and_rules.strip() + "\n" + contact_block).strip()
