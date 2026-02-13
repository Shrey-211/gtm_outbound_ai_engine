# Prompt Architecture

This document explains how the AI prompt is constructed, how segmentation drives personalisation, and how to modify the email output.

---

## Pipeline Overview

```
Contact CSV
  -> Segmentation (property type + company size)
    -> Prompt Builder (segment angle + contact fields)
      -> OpenAI Structured Output (subject, greetings, body)
        -> Fixed signature appended
          -> Output CSV
```

---

## Segmentation (`segmentation.py`)

Contacts are segmented by `type_of_properties_managed`. This is the primary axis that determines which PriceLabs value props the AI emphasises.

| Property Type         | Segment Key          |
|-----------------------|----------------------|
| Vacation Rental       | `vacation_rental`    |
| Short-term Rental     | `short_term_rental`  |
| Hotel                 | `hotel`              |
| Boutique Hotel        | `boutique_hotel`     |
| Serviced Apartment    | `serviced_apartment` |
| Mixed                 | `mixed_portfolio`    |
| Missing / Unknown     | `general`            |

Company size is derived from `MU_count` (managed-unit count) as a secondary signal:

| MU Count | Band         |
|----------|--------------|
| > 50     | `enterprise` |
| 6 - 50   | `mid`        |
| 1 - 5    | `small`      |
| 0 / NaN  | `unknown`    |

---

## Prompt Structure (`prompt_builder.py`)

Each prompt has three parts:

### 1. Role & Rules
Tells the AI it is an outbound SDR at PriceLabs generating a cold first-touch email. Sets constraints: word limit, tone, CTA requirement, and the instruction to skip any "Not specified" fields.

### 2. Segment Angle
A per-segment instruction injected into the prompt. Each segment gets a specific angle describing what PriceLabs features to highlight. These are defined in `_SEGMENT_ANGLES` inside `prompt_builder.py`.

Examples:
- **vacation_rental**: automates dynamic pricing, boosts off-season occupancy, PMS sync
- **hotel**: demand-based rate updates, comp-set tracking, channel-manager integrations
- **boutique_hotel**: compete with chains, hyper-local market intelligence
- **serviced_apartment**: length-of-stay pricing, corporate vs leisure demand balancing
- **mixed_portfolio**: single dashboard across property types, portfolio analytics
- **general**: broad intro to PriceLabs as a dynamic pricing tool

### 3. Contact Block
Injects personalisation fields from the CSV row:
- First Name, Company, PMS, Property Type, Region, Company Size

Fields that are empty or NaN are replaced with "Not specified", and the prompt explicitly tells the AI to skip mentioning those fields.

---

## Structured Output (`ai_engine.py`)

The AI response is enforced via OpenAI's **Structured Outputs** using a Pydantic schema:

```
ColdEmail:
  subject   -> Email subject line
  greetings -> Opening greeting (e.g. "Hi Maria,")
  body      -> Core email content with value prop and CTA
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

### Add or change a segment angle
Edit the `_SEGMENT_ANGLES` dictionary in `prompt_builder.py`. Add a new key matching a segment from `segmentation.py`, and write the angle text describing what to emphasise.

### Add a new property type segment
1. Add the mapping in `_PROPERTY_TYPE_SEGMENTS` in `segmentation.py`
2. Add the corresponding angle in `_SEGMENT_ANGLES` in `prompt_builder.py`

### Change the structured output fields
1. Edit the `ColdEmail` Pydantic model in `ai_engine.py`
2. Update the `_build_result` function in the same file
3. Update `_build_row` in `main.py` to include the new fields in the CSV

### Change the signature
Edit the `DEFAULT_SIGNATURE` constant in `ai_engine.py`.

### Change the model
Set `OPENAI_MODEL` in your `.env` file. Supported models with built-in pricing: `gpt-4.1`, `gpt-4.1-mini`, `gpt-4.1-nano`, `gpt-4o`, `gpt-4o-mini`.
