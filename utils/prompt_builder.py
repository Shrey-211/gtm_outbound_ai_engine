import pandas as pd

_SEGMENT_ANGLES = {
    "vacation_rental": (
        "This contact manages vacation rentals. "
        "Emphasise how PriceLabs automates dynamic pricing across listings, "
        "boosts occupancy during off-season, and syncs with their PMS in real time."
    ),
    "short_term_rental": (
        "This contact runs short-term rentals (Airbnb-style). "
        "Emphasise how PriceLabs uses market data to optimise nightly rates, "
        "increase revenue per listing, and save hours of manual price adjustments."
    ),
    "hotel": (
        "This contact operates a hotel. "
        "Emphasise how PriceLabs brings vacation-rental-grade dynamic pricing to hotels, "
        "with demand-based rate updates, comp-set tracking, and channel-manager integrations."
    ),
    "boutique_hotel": (
        "This contact runs a boutique / independent hotel. "
        "Emphasise how PriceLabs helps independent properties compete with chains "
        "through hyper-local market intelligence, automated rate recommendations, and easy PMS integration."
    ),
    "serviced_apartment": (
        "This contact manages serviced apartments. "
        "Emphasise how PriceLabs handles length-of-stay pricing, "
        "corporate vs leisure demand balancing, and automated rate adjustments across booking channels."
    ),
    "mixed_portfolio": (
        "This contact manages a mixed portfolio (hotels + rentals). "
        "Emphasise how PriceLabs provides a single pricing dashboard across property types, "
        "with custom strategies per listing and portfolio-wide revenue analytics."
    ),
    "general": (
        "Property type is unknown. Keep the angle broad: "
        "introduce PriceLabs as a data-driven dynamic pricing tool for hospitality, "
        "highlight ease of setup, and invite them to explore with a trial or demo."
    ),
}


def _safe(value, fallback="Not specified"):
    if value is None or pd.isna(value) or not str(value).strip():
        return fallback
    return str(value).strip()


def build_prompt(row, segment, company_size="unknown"):
    first_name = _safe(row.get("first_name"), "there")
    company = _safe(row.get("company_name"))
    pms = _safe(row.get("PMS"))
    property_type = _safe(row.get("type_of_properties_managed"))
    region = _safe(row.get("region"))

    angle = _SEGMENT_ANGLES.get(segment, _SEGMENT_ANGLES["general"])

    contact_block = f"""
        Contact (use these for personalization):
        - First Name: {first_name}
        - Company: {company}
        - PMS: {pms}
        - Property type: {property_type}
        - Region: {region}
        - Company size (by listing count): {company_size}
        """

    role_and_rules = f"""
        You are an outbound SDR at PriceLabs. This contact is a cold prospect (first touch). Generate one short, personalized cold email.

        Segment angle: {angle}

        Rules:
        - Body under 200 words. One clear CTA. No fluff. Sound human, and friendly not AI.
        - Reference their PMS, property type, or region where it fits naturally.
        - If a contact field says "Not specified", do NOT mention that field in the email.

        Output fields:
        - subject: A compelling, concise email subject line.
        - greetings: The opening greeting (e.g. "Hi {first_name},").
        - body: The core email content with value prop and CTA. Split in 2 paragraphs. Do NOT include the greeting or sign-off here.
        """

    return (role_and_rules.strip() + "\n" + contact_block).strip()
