# Technical handoff: GTM Outbound AI Engine (Scenario A)

Use this when extending or debugging the project with Claude Code, Codex, or similar tools.

## What this repo does

- **Scenario A (Outbound):** Generates personalized cold emails for prospects using the unified contact database. Personalization is driven by **PMS, property type, region, and company size** (derived from listing count).
- **Flow:** Load CSV → filter to `type == "prospect"` → for each row: segment → build prompt → call OpenAI → write results to `generated_emails.csv`.

## Repo layout

```
gtm_outbound_ai_engine/
├── data/
│   ├── database.csv          # Input: unified contact DB (or set CSV_PATH)
│   └── database_types.csv    # Field definitions (reference only)
├── utils/
│   ├── segmentation.py      # Deterministic segment + company_size band
│   ├── prompt_builder.py    # Builds the LLM prompt from row + segment
│   └── ai_engine.py         # OpenAI API call (gpt-4o-mini)
├── main.py                  # Entrypoint: load CSV, loop prospects, write output
├── requirements.txt
├── .env.example              # OPENAI_API_KEY (copy to .env)
├── PROMPT.md                 # This file
├── HOW-TO-USE.md            # Non-technical user guide
└── AI_JUSTIFICATION.md      # Why AI, cost, and what could be rules-only
```

## How to run

- **From repo root:** `python main.py`
- **Env vars:** `OPENAI_API_KEY` (required). Optional: `CSV_PATH` (default `data/database.csv`), `OUTBOUND_LIMIT` (default `5`).
- **Output:** `generated_emails.csv` in repo root (columns: email, segment, generated_email).

## Segmentation logic (where to change rules)

- **File:** `utils/segmentation.py`
- **Inputs used:** `PMS`, `MU_count`, `region`, `type_of_properties_managed`, `is_generic_domain`
- **Segments:** `enterprise` (MU ≥ 50), `growth_hostaway` (Hostaway + MU ≥ 10), `early_stage_generic` (generic email domain), else `standard_smb`
- **Company size (for prompt):** `get_company_size(row)` → bands from `MU_count`: unknown / small / mid_market / enterprise

To add segments or change bands, edit `segment_contact()` and/or `_company_size_band()`.

## Prompt and personalization

- **File:** `utils/prompt_builder.py`
- **Function:** `build_prompt(row, segment, company_size=...)`
- **Fields passed to the LLM:** first_name, company_name, PMS, type_of_properties_managed, region, company_size, segment.

To add a new personalization field: add it to the contact dict in `build_prompt` and ensure the CSV column exists; if the field needs a derived value (like company size), compute it in `main.py` or in segmentation and pass it in.

## AI layer

- **File:** `utils/ai_engine.py`
- **Model:** `gpt-4o-mini` (cost-conscious). Temperature 0.7.
- **API:** OpenAI `chat.completions.create`; key from `OPENAI_API_KEY`.

To switch model or provider, change only `ai_engine.py` and keep the same function interface (`generate_email(prompt) -> str`).

## Data layer and schema

- **Input:** CSV with columns documented in `data/database_types.csv`. Required for Scenario A: `type`, `PMS`, `type_of_properties_managed`, `region`, `MU_count`, plus `first_name`, `company_name`, `email`.
- **Segmentation relies on:** `type` (we filter to prospect), `PMS`, `MU_count`, `region`, `type_of_properties_managed`, `is_generic_domain`.
- **Missing data:** Empty PMS/region/property type are passed as "Not specified" in the prompt. Company size "unknown" when `MU_count` is 0 or missing.

## Evolving the workflow

- **New segments:** Add rules in `segmentation.py` and optionally reference the new segment in the prompt text in `prompt_builder.py`.
- **New fields:** Add column to CSV (or derive in code), pass into `build_prompt`, and extend the prompt template.
- **Batching / rate limits:** In `main.py`, add chunking and optional delay between `generate_email()` calls; keep `OUTBOUND_LIMIT` for testing.
- **Caching:** To avoid re-calling the API for the same contact, add a cache key (e.g. email + segment + hash of relevant fields) and skip or reuse previous output.

## Common tasks

- **Change number of emails per run:** Set env `OUTBOUND_LIMIT=20` (or edit default in `main.py`).
- **Use a different CSV:** Set `CSV_PATH` to the full path of `pricelabs_gtm_database_sample.csv` (or any CSV with the same column names).
- **Tweak email tone/length:** Edit the “Rules” section in `build_prompt()` in `prompt_builder.py`.
- **Reduce cost:** Keep using `gpt-4o-mini`, enforce `OUTBOUND_LIMIT`, and consider template-only or rule-based flows for segments that don’t need variation (see AI_JUSTIFICATION.md).
