def build_prompt(row, segment, company_size="unknown", contact_type="prospect"):
    """
    Build the outbound cold-email prompt. Drafts different emails for prospect vs lead.

    - prospect: First-touch cold email; introduce PriceLabs and one clear CTA.
    - lead: Warmer email; they've shown interest, so emphasize next step / value and a specific CTA.
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

    if contact_type == "lead":
        role_and_rules = """
        You are an outbound SDR at PriceLabs. This contact is a LEAD (they have shown interest but are not yet trial/customer). Generate one short, personalized email.

        Angle: Warmer than cold. Acknowledge they're already in the funnel. Focus on the next step—e.g. start a trial, book a call, or try a specific feature. One clear CTA.

        Rules:
        - Under 120 words. One clear CTA. No fluff. Sound human, not AI.
        - Reference their PMS, property type, or region where it fits naturally.
        - Do not repeat a full product intro; assume some awareness.
        """
    else:
        role_and_rules = """
        You are an outbound SDR at PriceLabs. This contact is a PROSPECT (cold, first touch). Generate one short, personalized cold email.

        Angle: Introduce PriceLabs briefly. One clear value prop and one CTA (e.g. trial, demo, or resource). No fluff.

        Rules:
        - Under 120 words. One clear CTA. No fluff. Sound human, not AI.
        - Reference their PMS, property type, or region where it fits naturally.
        """

    return (role_and_rules.strip() + "\n" + contact_block).strip()