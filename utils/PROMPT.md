# Prompt Architecture

This document explains how the AI prompt is constructed, how filtering and segmentation drive personalisation, and how to modify the email output.

---

## Pipeline Overview

```
Contact CSV
  → Eligibility Filter (4 deterministic rules, no AI)
    → Firmographic Segmentation (deterministic rules, no AI)
      → Prompt Builder (firmographic angle + property-type context + contact fields)
        → OpenAI Structured Output (subject, greetings, body)
          → Fixed signature appended
            → Output CSV
```

AI is only invoked at the "OpenAI Structured Output" step. Everything before it is rule-based.

---

## Eligibility Filter (`filter_cold_outreach.py`)

Before any segmentation or AI, contacts must pass four rules (AND gate):

| Rule | Column              | Condition    | Why                                              |
|:----:|---------------------|--------------|--------------------------------------------------|
| 1    | `type`              | `== prospect`| Don't email users, trials, or customers          |
| 2    | `Unsubscribed`      | `== FALSE`   | Legal compliance — respect opt-outs              |
| 3    | `is_blocked_domain` | `== FALSE`   | Don't email competitors or spam domains          |
| 4    | `total_emails_sent` | `== 0`       | Only contact people never previously emailed     |

---

## Firmographic Segmentation (`filter_cold_outreach.py`)

This is the **primary axis** that determines the messaging angle. Each eligible contact is assigned exactly one segment using deterministic, priority-ordered rules (first match wins):

| Priority | Segment       | Rules (ALL must be true)                                                         | Messaging Focus                              |
|:--------:|---------------|----------------------------------------------------------------------------------|----------------------------------------------|
| 1        | `enterprise`  | MU_count >= 50, is_generic_domain == FALSE, job_title contains Founder/CEO/Revenue/Director | Scale, automation, portfolio optimisation    |
| 2        | `growth_pms`  | PMS is present, 10 <= MU_count <= 49                                             | Integration benefits, revenue uplift via PMS |
| 3        | `early_stage` | is_generic_domain == TRUE, MU_count < 10                                         | Education, quick wins, lightweight onboarding|
| 4        | `general`     | Everything else                                                                  | Broad PriceLabs intro, trial/demo CTA        |

### Company Size Band (secondary signal)

Company size is derived from `MU_count` and passed to the prompt for additional context:

| MU Count | Band         |
|----------|--------------|
| >= 50    | `enterprise` |
| 10 - 49  | `growth`     |
| 1 - 9    | `small`      |
| 0 / NaN  | `unknown`    |

### Property Type (secondary personalisation layer)

Property type from `type_of_properties_managed` adds context to the prompt but does **not** determine the segment:

| Property Type      | Context added to prompt                                        |
|--------------------|----------------------------------------------------------------|
| Vacation Rental    | Mention occupancy optimisation and seasonal pricing            |
| Short-term Rental  | Mention nightly rate optimisation and Airbnb-style market data |
| Hotel              | Mention demand-based rate updates and comp-set tracking        |
| Boutique Hotel     | Mention competing with chains via hyper-local intelligence     |
| Serviced Apartment | Mention length-of-stay pricing, corporate vs leisure balancing |
| Mixed              | Mention single dashboard across property types                 |

---

## Prompt Structure (`prompt_builder.py`)

Each prompt has four layers:

### Layer 1: Role & Rules

Tells the AI it is an outbound SDR at PriceLabs generating a cold first-touch email. Sets constraints:
- Body under 120 words
- One clear CTA
- Sound human and friendly, not AI
- Skip any field that says "Not specified"

### Layer 2: Firmographic Segment Angle (primary)

A per-segment instruction injected into the prompt. Defined in `_FIRMOGRAPHIC_ANGLES` inside `prompt_builder.py`:

- **enterprise**: scale, automation, portfolio-wide optimisation, centralised dashboards
- **growth_pms**: integration benefits with their specific PMS, revenue uplift, plugs into existing workflow
- **early_stage**: education, quick wins, lightweight onboarding, free trial, no commitment
- **general**: broad intro to PriceLabs as a dynamic pricing tool, ease of setup

### Layer 3: Property-Type Context (secondary)

An optional secondary instruction based on `type_of_properties_managed`. Defined in `_PROPERTY_TYPE_CONTEXT` inside `prompt_builder.py`. Only added when the property type is known and matches a key in the dictionary.

### Layer 4: Contact Block

Injects personalisation fields from the CSV row:
- First Name, Company, Job Title, PMS, Property Type, Region, Company Size

Fields that are empty or NaN are replaced with "Not specified", and the rules instruct the AI to skip mentioning those fields.

### Geographic Note

The prompt explicitly scopes region usage:

> "Use the Region only for selecting a relevant case study or localised proof point. Do NOT change the core value proposition based on region."

---

## Structured Output (`ai_engine.py`)

The AI response is enforced via OpenAI's **Structured Outputs** using a Pydantic schema:

```
ColdEmail:
  subject   → Email subject line
  greetings → Opening greeting (e.g. "Hi Maria,")
  body      → Core email content with value prop and CTA
```

The **signature** is not AI-generated. It is a fixed constant appended to every email:

```
Best regards,
Shreyas Jadhav
PriceLabs
```

The output CSV includes all individual fields plus a `complete_email` column that combines greetings + body + signature into a ready-to-send draft.

---

## How to Modify

### Change the email tone or rules
Edit the `role_and_rules` string in `prompt_builder.py`. This controls word limit, tone, CTA style, and formatting instructions.

### Add or change a firmographic segment angle
Edit the `_FIRMOGRAPHIC_ANGLES` dictionary in `prompt_builder.py`. Add a new key matching a segment from `filter_cold_outreach.py`, and write the angle text describing what to emphasise.

### Add a new firmographic segment
1. Add the rule in `_assign_segment()` in `filter_cold_outreach.py` — insert at the right priority position.
2. Add the corresponding messaging angle in `_FIRMOGRAPHIC_ANGLES` in `prompt_builder.py`.

### Add a new property-type context
Add an entry to `_PROPERTY_TYPE_CONTEXT` in `prompt_builder.py` with the raw property type string as the key (lowercase).

### Change the eligibility filter rules
Edit `filter_eligible_contacts()` in `filter_cold_outreach.py`. Add or remove conditions from the mask. Each rule should have its own logged line.

### Change the enterprise title keywords
Edit the `_ENTERPRISE_TITLE_KEYWORDS` set in `filter_cold_outreach.py`.

### Change the structured output fields
1. Edit the `ColdEmail` Pydantic model in `ai_engine.py`
2. Update the `_build_result` function in the same file
3. Update `_build_row` in `main.py` to include the new fields in the CSV

### Change the signature
Edit the `DEFAULT_SIGNATURE` constant in `ai_engine.py`.

### Change the model
Set `OPENAI_MODEL` in your `.env` file. Supported models with built-in pricing: `gpt-4.1`, `gpt-4.1-mini`, `gpt-4.1-nano`, `gpt-4o`, `gpt-4o-mini`.
