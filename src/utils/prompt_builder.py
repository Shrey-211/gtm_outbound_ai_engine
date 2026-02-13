def build_prompt(row, segment):
    base_template = f"""
You are an outbound SDR at PriceLabs.

Generate a concise, personalized cold email.

Contact Details:
- First Name: {row.get("first_name")}
- Company: {row.get("company_name")}
- PMS: {row.get("PMS")}
- Region: {row.get("region")}
- Properties Managed: {row.get("MU_count")}

Segment: {segment}

Constraints:
- Keep under 120 words
- Clear CTA
- No fluff
- Sound human, not AI-generated
"""

    return base_template