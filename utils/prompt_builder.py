import pandas as pd

# ── Firmographic segment angles (primary messaging driver) ──────────────
_FIRMOGRAPHIC_ANGLES = {
    "enterprise": (
        "This is an enterprise-level prospect (50+ listings, leadership role). "
        "Emphasise scale, automation, and portfolio-wide optimisation. "
        "Position PriceLabs as infrastructure for revenue management at scale — "
        "automated pricing across their entire portfolio, centralised dashboards, "
        "and data-driven decision-making that frees their team from manual work."
    ),
    "growth_pms": (
        "This prospect already uses a PMS and manages 10–49 listings — they are "
        "in a growth phase. Emphasise integration benefits with their specific PMS, "
        "revenue uplift via PMS-connected dynamic pricing, and how PriceLabs plugs "
        "directly into their existing workflow to unlock better rates without extra "
        "manual effort."
    ),
    "early_stage": (
        "This is an early-stage prospect (small portfolio, generic domain). "
        "Emphasise education, quick wins, and lightweight onboarding. "
        "Position PriceLabs as the simplest way to start pricing smarter — "
        "free trial, no commitment, and immediate value even with a few listings."
    ),
    "general": (
        "Segment details are limited. Keep the angle broad: "
        "introduce PriceLabs as a data-driven dynamic pricing tool for hospitality, "
        "highlight ease of setup, and invite them to explore with a trial or demo."
    ),
}

# ── Property-type context (secondary personalisation layer) ─────────────
_PROPERTY_TYPE_CONTEXT = {
    "vacation rental": (
        "They manage vacation rentals — mention occupancy optimisation "
        "and seasonal pricing."
    ),
    "short-term rental": (
        "They run short-term rentals — mention nightly rate optimisation "
        "and Airbnb-style market data."
    ),
    "hotel": (
        "They operate a hotel — mention demand-based rate updates "
        "and comp-set tracking."
    ),
    "boutique hotel": (
        "They run a boutique hotel — mention competing with chains "
        "via hyper-local intelligence."
    ),
    "serviced apartment": (
        "They manage serviced apartments — mention length-of-stay pricing "
        "and corporate vs leisure balancing."
    ),
    "mixed": (
        "They manage a mixed portfolio — mention a single dashboard "
        "across property types."
    ),
}


def _safe(value, fallback="Not specified"):
    if value is None or pd.isna(value) or not str(value).strip():
        return fallback
    return str(value).strip()


def build_prompt(row, segment, company_size="unknown"):
    email = row.get("email", "?")
    first_name = _safe(row.get("first_name"), "there")
    company = _safe(row.get("company_name"))
    job_title = _safe(row.get("job_title"))
    pms = _safe(row.get("PMS"))
    property_type = _safe(row.get("type_of_properties_managed"))
    region = _safe(row.get("region"))

    # Primary angle — firmographic segment
    firmo_angle = _FIRMOGRAPHIC_ANGLES.get(segment, _FIRMOGRAPHIC_ANGLES["general"])

    # Secondary angle — property-type context (if known)
    prop_context = _PROPERTY_TYPE_CONTEXT.get(property_type.lower(), "")
    secondary_line = (
        f"\n        Property-type context: {prop_context}"
        if prop_context
        else ""
    )

    print(f"[PROMPT]         {email:40s} → segment={segment}, "
          f"size={company_size}, pms={pms}, region={region}")

    contact_block = f"""
        Contact (use these for personalisation):
        - First Name: {first_name}
        - Company: {company}
        - Job Title: {job_title}
        - PMS: {pms}
        - Property type: {property_type}
        - Region: {region}
        - Company size (by listing count): {company_size}
        """

    role_and_rules = f"""
        You are an outbound SDR at PriceLabs. This contact is a cold prospect \
(first touch). Generate one short, personalised cold email.

        Segment angle: {firmo_angle}{secondary_line}

        Geographic note: Use the Region only for selecting a relevant case \
study or localised proof point. Do NOT change the core value proposition \
based on region.

        Rules:
        - Body under 120 words. One clear CTA. No fluff. Sound human and \
friendly, not AI.
        - Reference their PMS, property type, or region where it fits \
naturally.
        - If a contact field says "Not specified", do NOT mention that field \
in the email.

        Output fields:
        - subject: A compelling, concise email subject line.
        - greetings: The opening greeting (e.g. "Hi {first_name},").
        - body: The core email content with value prop and CTA. Split in 2 \
paragraphs. Do NOT include the greeting or sign-off here.
        """

    return (role_and_rules.strip() + "\n" + contact_block).strip()
