# GTM Outbound AI Engine — Product Document

> Onboarding and technical reference for the PriceLabs cold outbound email generation system.
>
> Last updated: February 2026

---

## Table of Contents

1. [What This Product Does](#1-what-this-product-does)
2. [The Core Philosophy](#2-the-core-philosophy)
3. [System Requirements and Setup](#3-system-requirements-and-setup)
4. [Repository Structure](#4-repository-structure)
5. [The Complete Pipeline — Stage by Stage](#5-the-complete-pipeline--stage-by-stage)
6. [Input Data Model](#6-input-data-model)
7. [Stage 1 — Data Load](#7-stage-1--data-load)
8. [Stage 2 — Eligibility Filter](#8-stage-2--eligibility-filter)
9. [Stage 3 — Firmographic Segmentation](#9-stage-3--firmographic-segmentation)
10. [Stage 4 — Contact Limit](#10-stage-4--contact-limit)
11. [Stage 5 — AI Email Generation](#11-stage-5--ai-email-generation)
12. [Stage 6 — Save Results](#12-stage-6--save-results)
13. [Prompt Architecture](#13-prompt-architecture)
14. [AI Engine Internals](#14-ai-engine-internals)
15. [Output Format](#15-output-format)
16. [Cost Model](#16-cost-model)
17. [Terminal Log Walkthrough](#17-terminal-log-walkthrough)
18. [How to Extend and Modify](#18-how-to-extend-and-modify)
19. [FAQ and Troubleshooting](#19-faq-and-troubleshooting)

---

## 1. What This Product Does

The GTM Outbound AI Engine is a command-line Python tool that generates **personalised cold outreach emails** for the PriceLabs sales team.

You give it a CSV of contacts. It gives you back a CSV of ready-to-send emails — one per contact — each tailored to that person's company size, PMS software, property type, region, and job title.

**In one sentence:** Business rules decide *who* to email and *what angle* to use. AI writes the actual email.

---

## 2. The Core Philosophy

```
Business logic decides WHO to contact and WHAT to say.
AI decides HOW to say it.
```

This is a deliberate design choice. Cold outreach must be controlled and intentional:

- **AI does NOT decide who to contact.** Deterministic, rule-based filtering does (Stage 2).
- **AI does NOT decide the messaging angle.** Firmographic segmentation does (Stage 3).
- **AI only generates the email copy** after the segment and personalisation fields have been locked in by business rules (Stage 5).

This separation prevents hallucinated targeting logic, keeps compliance risk low, and makes every decision auditable in the terminal logs.

---

## 3. System Requirements and Setup

### Prerequisites

- Python 3.11 or higher
- An OpenAI API key with access to the model you want to use (gpt-4.1, gpt-4.1-mini, gpt-4.1-nano, gpt-4o, or gpt-4o-mini)

### Step-by-step Setup

**1. Clone and create a virtual environment:**

```bash
git clone <repo-url>
cd gtm_outbound_ai_engine
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

**2. Install dependencies:**

```bash
pip install -r requirements.txt
```

Dependencies (defined in `requirements.txt`):

| Package        | Purpose                                     |
|----------------|---------------------------------------------|
| `pandas`       | CSV loading, DataFrame operations, filtering |
| `openai`       | OpenAI API client (realtime + batch)         |
| `pydantic`     | Structured output schema for AI responses    |
| `python-dotenv`| Load environment variables from `.env`       |

**3. Configure environment variables:**

```bash
cp .env.example .env
```

Edit `.env`:

```
OPENAI_API_KEY=sk-your-key-here
OUTBOUND_LIMIT=5
OPENAI_MODEL=gpt-4.1
```

| Variable         | What it controls                                       | Default              |
|------------------|--------------------------------------------------------|----------------------|
| `OPENAI_API_KEY` | Your OpenAI API key                                    | *required*           |
| `OPENAI_MODEL`   | Which model generates the emails                       | `gpt-4.1`           |
| `OUTBOUND_LIMIT` | How many contacts to process per run                   | `5`                  |
| `CSV_PATH`       | Path to the input contact CSV                          | `data/database.csv`  |

**4. Run:**

```bash
python main.py
```

Output CSV appears in the `results/` folder with a timestamped filename.

---

## 4. Repository Structure

```
gtm_outbound_ai_engine/
│
├── main.py                          Entrypoint — orchestrates the full 6-stage pipeline
├── requirements.txt                 Python dependencies
├── .env.example                     Template for environment variables
├── .env                             Your local environment variables (gitignored)
├── .gitignore
├── README.md                        Quick-start readme
├── PRODUCT_DOCUMENT.md              This document
│
├── utils/
│   ├── filter_cold_outreach.py      Stage 1-3: Load CSV, filter, assign segments
│   ├── segmentation.py              Segment lookups + company size band
│   ├── prompt_builder.py            Build AI prompts with segment angles + contact fields
│   ├── ai_engine.py                 OpenAI integration (realtime + batch) + cost tracking
│   └── PROMPT.md                    Prompt architecture docs (how to modify prompts)
│
├── data/
│   ├── database.csv                 Full contact database (525 contacts)
│   ├── database_dummy.csv           Small sample database (101 contacts) for testing
│   └── database_types.csv           Field definitions reference (what each CSV column means)
│
├── results/                         Generated email CSVs (gitignored)
│   └── generated_emails_<timestamp>.csv
│
└── tmp/                             Batch API input files (gitignored)
    └── batch_input_<timestamp>.jsonl
```

### Which file does what

| File | Responsibility | AI involved? |
|------|---------------|:------------:|
| `main.py` | Orchestrates the pipeline, applies the contact limit, picks realtime vs batch mode, saves output | No |
| `filter_cold_outreach.py` | Loads CSV, applies eligibility filter, assigns firmographic segments | No |
| `segmentation.py` | Reads the pre-assigned segment, provides company size band | No |
| `prompt_builder.py` | Constructs the text prompt with segment angle + contact personalisation | No |
| `ai_engine.py` | Sends the prompt to OpenAI, parses the structured response, tracks cost | **Yes** |

The AI boundary is a single function: `generate_email()` in `ai_engine.py`. Everything before it is deterministic.

---

## 5. The Complete Pipeline — Stage by Stage

```
┌─────────────────────────────────────────────────────────────┐
│                    FULL PIPELINE FLOW                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  CSV File                                                   │
│    │                                                        │
│    ▼                                                        │
│  STAGE 1 · DATA LOAD                          (no AI)      │
│    │  Read CSV into DataFrame                               │
│    ▼                                                        │
│  STAGE 2 · ELIGIBILITY FILTER                  (no AI)      │
│    │  type == prospect                                      │
│    │  Unsubscribed == FALSE                                 │
│    │  is_blocked_domain == FALSE                            │
│    │  total_emails_sent == 0                                │
│    ▼                                                        │
│  STAGE 3 · FIRMOGRAPHIC SEGMENTATION           (no AI)      │
│    │  enterprise / growth_pms / early_stage / general       │
│    ▼                                                        │
│  STAGE 4 · CONTACT LIMIT                       (no AI)      │
│    │  Apply OUTBOUND_LIMIT                                  │
│    ▼                                                        │
│  STAGE 5 · AI EMAIL GENERATION                 (AI HERE)    │
│    │  For each contact:                                     │
│    │    1. Look up segment + company size                   │
│    │    2. Build prompt (segment angle + contact fields)    │
│    │    3. Call OpenAI → get subject, greeting, body        │
│    │    4. Append fixed signature                           │
│    ▼                                                        │
│  STAGE 6 · SAVE RESULTS                        (no AI)      │
│    │  Write to results/generated_emails_<timestamp>.csv     │
│    ▼                                                        │
│  DONE                                                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

Key insight: **Stages 1–4 are entirely deterministic.** No AI, no randomness. The same input CSV always produces the same filtered and segmented contact list. AI is only invoked at Stage 5, and its output is constrained by a JSON schema.

---

## 6. Input Data Model

The input CSV contains 55 columns per contact. The full reference is in `data/database_types.csv`. Here are the columns that the engine actively uses:

### Fields Used for Filtering (Stage 2)

| Column              | Type    | What it means                                            |
|---------------------|---------|----------------------------------------------------------|
| `type`              | String  | Lifecycle stage: `prospect`, `lead`, `trial`, `customer` |
| `Unsubscribed`      | Boolean | `TRUE` if the contact opted out of marketing emails      |
| `is_blocked_domain` | Boolean | `TRUE` if the domain is blocked (spam, competitors)      |
| `total_emails_sent` | Integer | Total emails sent across all platforms (must be 0)       |

### Fields Used for Segmentation (Stage 3)

| Column              | Type    | What it means                                         |
|---------------------|---------|-------------------------------------------------------|
| `MU_count`          | Integer | Number of managed units (listings) in PriceLabs       |
| `is_generic_domain` | Boolean | `TRUE` for Gmail, Yahoo, etc. vs company domains      |
| `PMS`               | String  | Property Management System (e.g. Guesty, Hostaway)    |
| `job_title`         | String  | Contact's role (e.g. CEO, Revenue Manager, Founder)   |

### Fields Used for Personalisation (Stage 5)

| Column                        | Type   | How it's used in the email prompt              |
|-------------------------------|--------|------------------------------------------------|
| `first_name`                  | String | Greeting: "Hi Maria,"                          |
| `company_name`                | String | Reference their business by name               |
| `job_title`                   | String | Tailor language to their seniority             |
| `PMS`                         | String | Mention their specific PMS integration         |
| `type_of_properties_managed`  | String | Vacation Rental, Hotel, Mixed, etc.            |
| `region`                      | String | Case study selection, localised proof points   |
| `MU_count`                    | Integer| Company size context for messaging             |

### Fields Not Used (but present in CSV)

The CSV contains many other fields (`Zoho_CRM_ID`, `User_ID`, `billing_stat`, `phone`, `website`, `Linkedin_URLs`, social URLs, email history fields, etc.) that are preserved in the DataFrame but not actively used by the engine. They exist for CRM context and future extensions.

---

## 7. Stage 1 — Data Load

**File:** `filter_cold_outreach.py` → `load_cold_outreach_contacts()`

**What happens:**
1. The CSV path is resolved (defaults to `data/database.csv`, overridable via `CSV_PATH` env var).
2. The entire CSV is loaded into a pandas DataFrame using `pd.read_csv()`.
3. The total row count and column names are logged.

**Terminal output:**
```
================================================================
  STAGE 1 · DATA LOAD
================================================================
[LOAD] Loaded 525 rows from database.csv
[LOAD] Columns: ['email', 'first_name', 'last_name', ...]
```

**No rows are dropped at this stage.** This is a pure I/O step.

---

## 8. Stage 2 — Eligibility Filter

**File:** `filter_cold_outreach.py` → `filter_eligible_contacts()`

**What happens:** Four rules are applied as an AND gate. A contact must pass ALL four to survive:

| Rule | Column | Condition | Why |
|------|--------|-----------|-----|
| 1 | `type` | Must equal `prospect` | Don't email existing users, trials, or customers |
| 2 | `Unsubscribed` | Must be `FALSE` | Legal compliance — respect opt-outs |
| 3 | `is_blocked_domain` | Must be `FALSE` | Don't email competitors or known spam domains |
| 4 | `total_emails_sent` | Must equal `0` | Only contact people who have never been emailed |

**Terminal output:**
```
================================================================
  STAGE 2 · ELIGIBILITY FILTER  (deterministic, no AI)
================================================================
[FILTER] Applying eligibility rules on 525 contacts …
[FILTER]   ├─ type == 'prospect'        : 312 pass
[FILTER]   ├─ Unsubscribed == FALSE      : 480 pass
[FILTER]   ├─ is_blocked_domain == FALSE  : 510 pass
[FILTER]   ├─ total_emails_sent == 0      : 198 pass
[FILTER]   └─ Combined: 142 eligible, 383 dropped
```

Each rule is logged independently so you can see exactly where contacts are being lost. The "Combined" line shows the AND result.

**Design notes:**
- The TRUE/FALSE values in the CSV are strings, not Python booleans. The `_to_bool()` helper handles case-insensitive string-to-boolean conversion.
- `total_emails_sent` is coerced to numeric via `pd.to_numeric()` with `errors="coerce"`. Empty or NaN values are treated as 0 (never emailed = passes the filter).

---

## 9. Stage 3 — Firmographic Segmentation

**File:** `filter_cold_outreach.py` → `assign_firmographic_segments()`

**What happens:** Every eligible contact is assigned exactly one firmographic segment. The rules are evaluated in priority order — first match wins:

### Segment Rules (Priority Order)

| Priority | Segment | Rules (ALL must be true) | Messaging Focus |
|:--------:|---------|--------------------------|-----------------|
| 1 | `enterprise` | MU_count >= 50 **AND** is_generic_domain == FALSE **AND** job_title contains "Founder", "CEO", "Revenue", or "Director" | Scale, automation, portfolio-wide optimisation |
| 2 | `growth_pms` | PMS is present (not empty/NaN) **AND** 10 <= MU_count <= 49 | Integration benefits, revenue uplift via PMS optimisation |
| 3 | `early_stage` | is_generic_domain == TRUE **AND** MU_count < 10 | Education, quick wins, lightweight onboarding |
| 4 | `general` | Everything else that passed Stage 2 | Broad PriceLabs intro, trial/demo CTA |

### Why these segments?

- **Enterprise:** These are large operators with real companies (non-generic domain) and decision-makers (leadership titles). They need to hear about scale.
- **Growth PMS:** They already use a PMS, so they understand tooling. They're growing (10-49 units) and want to plug PriceLabs into their existing workflow.
- **Early Stage:** Generic email domain + small portfolio signals an individual or early-stage business. They need education, not enterprise features.
- **General:** Catch-all for contacts that don't fit the above. Gets a broad, safe message.

### Job Title Matching (Enterprise)

The `_has_leadership_title()` function checks if the job title contains any of these keywords (case-insensitive substring match):

```
founder, ceo, revenue, director
```

So "Revenue Manager", "Co-Founder & CEO", and "Director of Operations" all match.

### Terminal output:
```
================================================================
  STAGE 3 · FIRMOGRAPHIC SEGMENTATION  (deterministic, no AI)
================================================================
[SEGMENT] Assigning firmographic segments to 290 contacts …
[SEGMENT]   ├─ early_stage     : 45
[SEGMENT]   ├─ enterprise      : 12
[SEGMENT]   ├─ general         : 180
[SEGMENT]   ├─ growth_pms      : 53
[SEGMENT]   └─ Total: 290
```

The segment is stored as a new column `firmographic_segment` on the DataFrame. It flows through the rest of the pipeline.

---

## 10. Stage 4 — Contact Limit

**File:** `main.py` → `run()`

**What happens:** The `OUTBOUND_LIMIT` environment variable controls how many contacts to process. The engine takes the first N contacts from the filtered + segmented DataFrame.

```python
limit = int(os.environ.get("OUTBOUND_LIMIT", "5"))
contacts = contacts.head(limit)
```

**Terminal output:**
```
================================================================
  STAGE 4 · CONTACT LIMIT
================================================================
[LIMIT] OUTBOUND_LIMIT=5  →  5 contacts to process
```

**Why this exists:** Generating emails costs money (OpenAI API). This lets you test with small batches before running on the full database.

---

## 11. Stage 5 — AI Email Generation

**File:** `main.py` → `_run_realtime_pipeline()` or `_run_batch_pipeline()`

**This is where AI is invoked.** Everything before this stage was deterministic business logic.

### Processing Mode Selection

The engine automatically picks realtime or batch mode:

| Contact Count | Mode | Behaviour |
|:-------------:|------|-----------|
| 1 – 10 | **Realtime** | One API call per contact, instant results |
| 11+ | **Batch** | All prompts submitted as a single batch job |

The threshold is controlled by `BATCH_THRESHOLD` in `ai_engine.py` (default: `10`).

### Realtime Mode (per-contact flow)

For each contact, the engine executes this sequence:

```
1. segment_contact(row)        → Look up the firmographic segment
2. get_company_size(row)       → Derive the size band (enterprise/growth/small/unknown)
3. build_prompt(row, segment)  → Construct the full text prompt
4. generate_email(prompt)      → CALL OPENAI API ← AI happens here
5. _build_row(...)             → Assemble the output row
```

**Terminal output (per contact):**
```
── Contact 1/5: maria.martinez@beachstays.com ──────────────────
[SEGMENT-LOOKUP] maria.martinez@beachstays.com   → general
[SIZE-LOOKUP]    maria.martinez@beachstays.com   → unknown (MU_count=0)
[PROMPT]         maria.martinez@beachstays.com   → segment=general, size=unknown, pms=Escapia, region=Africa
[PROMPT]         Prompt length: 842 chars
[AI]    ⚡ Calling OpenAI  model=gpt-4.1  temp=0.4 …
[AI]    ✓ Response in 1.3s  tokens=357+101=458  cost=$0.001522
[AI]      subject: Unlock Data-Driven Pricing for Your Mixed Portfolio
[DONE]   ✓ Email generated for maria.martinez@beachstays.com  (running total: $0.001522)
```

### Batch Mode (bulk flow)

When contact count exceeds the threshold:

```
Phase 1: Build all prompts            (no AI — deterministic)
Phase 2: Write prompts to .jsonl file (no AI — file I/O)
Phase 3: Upload + submit batch job    (AI starts here)
Phase 4: Poll until complete          (waiting for AI)
Phase 5: Download + parse results     (AI finished)
Phase 6: Assemble output rows         (no AI)
```

**Terminal output (batch):**
```
[PIPELINE] Mode: BATCH  (15 contacts, > 10 threshold)
[PIPELINE] All prompts built first → single batch AI call → parse

── Building prompts (no AI yet) ─────────────────────────────────
  [1/15] maria@example.com
  [2/15] carlos@example.com
  ...

── Submitting to OpenAI Batch API (AI starts here) ─────────────
[BATCH-PREP] Writing 15 requests → batch_input_1234.jsonl
[BATCH-PREP] Done – 12.3 KB
[AI]    ⚡ Uploading batch file to OpenAI …
[AI]    ⚡ Submitting batch  model=gpt-4.1  file=file-abc123 …
[AI]    ✓ Batch created: batch_xyz789
[AI]    ⏳ Polling batch batch_xyz789 every 15s …
[AI]    ⏳ Poll #1: status=in_progress  progress=5/15  failed=0
[AI]    ⏳ Poll #2: status=in_progress  progress=12/15  failed=0
[AI]    ⏳ Poll #3: status=completed  progress=15/15  failed=0
[AI]    ✓ Batch completed – 15 results ready
[AI]    Downloading batch results from file-result456 …
[AI]    ✓ Parsed 15 batch results  total_cost=$0.024000
```

### Why Batch?

| Benefit | Detail |
|---------|--------|
| **50% cheaper** | OpenAI charges half price for batch API requests |
| **Higher rate limits** | Batch has its own rate-limit pool — no throttling at 500+ emails |
| **Tradeoff** | Asynchronous — typically minutes, can take up to 24 hours |

---

## 12. Stage 6 — Save Results

**File:** `main.py` → `run()`

**What happens:** The output DataFrame is written to a timestamped CSV in the `results/` folder.

```
results/generated_emails_1770993957.8282015.csv
```

**Terminal output:**
```
================================================================
  STAGE 6 · SAVE RESULTS
================================================================
[SAVE] 5 emails → results/generated_emails_1770993957.csv

================================================================
  SUMMARY
================================================================
[SUMMARY] Emails generated : 5
[SUMMARY] Segment breakdown: {'general': 3, 'early_stage': 2}
[SUMMARY] Total cost       : $0.008244 USD
[SUMMARY] Wall time        : 12.1s
[SUMMARY] Output file      : results/generated_emails_1770993957.csv
```

---

## 13. Prompt Architecture

The AI prompt has four layers, built by `prompt_builder.py`:

### Layer 1: Role and Rules

Tells the AI it is an outbound SDR at PriceLabs, sets constraints:

- Body under 120 words
- One clear CTA
- No fluff, sound human and friendly
- Skip any field that says "Not specified"

### Layer 2: Firmographic Segment Angle (primary)

A per-segment instruction that drives the core messaging. This is the **primary** personalisation axis:

| Segment | What the AI is told to emphasise |
|---------|----------------------------------|
| `enterprise` | Scale, automation, portfolio-wide optimisation. Position PriceLabs as infrastructure for revenue management at scale. |
| `growth_pms` | Integration benefits with their specific PMS, revenue uplift via PMS-connected dynamic pricing, plugs into existing workflow. |
| `early_stage` | Education, quick wins, lightweight onboarding. Free trial, no commitment, immediate value with few listings. |
| `general` | Broad intro to PriceLabs as a dynamic pricing tool, ease of setup, trial or demo invitation. |

### Layer 3: Property-Type Context (secondary)

A secondary personalisation layer based on `type_of_properties_managed`:

| Property Type | Context added to prompt |
|---------------|------------------------|
| Vacation Rental | Mention occupancy optimisation and seasonal pricing |
| Short-term Rental | Mention nightly rate optimisation and Airbnb-style market data |
| Hotel | Mention demand-based rate updates and comp-set tracking |
| Boutique Hotel | Mention competing with chains via hyper-local intelligence |
| Serviced Apartment | Mention length-of-stay pricing and corporate vs leisure balancing |
| Mixed | Mention single dashboard across property types |

This layer is only added when the property type is known.

### Layer 4: Contact Block

Injects the actual personalisation fields:

```
Contact (use these for personalisation):
- First Name: Maria
- Company: Maria's Hospitality
- Job Title: CEO
- PMS: Escapia
- Property type: Mixed
- Region: Africa
- Company size (by listing count): unknown
```

Empty or NaN fields are replaced with "Not specified", and the rules instruct the AI to skip mentioning those fields entirely.

### Geographic Note

The prompt explicitly scopes region usage:

> "Use the Region only for selecting a relevant case study or localised proof point. Do NOT change the core value proposition based on region."

This prevents the AI from inventing region-specific claims.

---

## 14. AI Engine Internals

**File:** `ai_engine.py`

### Structured Output

Email responses use OpenAI's **Structured Outputs** via a Pydantic model:

```python
class ColdEmail(BaseModel):
    subject: str      # Email subject line
    greetings: str    # Opening greeting (e.g. "Hi Maria,")
    body: str         # Core email body with value prop and CTA
```

This guarantees the response **always** contains exactly three fields — no regex parsing, no "sometimes the AI forgets the subject line" issues.

The schema is converted to a JSON schema and passed as `response_format` to the OpenAI API.

### Signature

The signature is **not AI-generated**. It is a fixed constant appended to every email:

```
Best regards,
Shreyas Jadhav
PriceLabs
```

Defined as `DEFAULT_SIGNATURE` in `ai_engine.py`.

### Model Parameters

| Parameter | Value | Why |
|-----------|-------|-----|
| `temperature` | 0.4 | Low enough for consistency, high enough for natural variation |
| `top_p` | 0.9 | Slightly constrained nucleus sampling |

### Cost Tracking

Every API call tracks token usage and computes cost using built-in pricing:

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------:|----------------------:|
| gpt-4.1 | $2.00 | $8.00 |
| gpt-4.1-mini | $0.40 | $1.60 |
| gpt-4.1-nano | $0.10 | $0.40 |
| gpt-4o | $2.50 | $10.00 |
| gpt-4o-mini | $0.15 | $0.60 |

Cost is logged per-email and as a running total.

---

## 15. Output Format

The output CSV (`results/generated_emails_<timestamp>.csv`) has these columns:

| Column | Description | Source |
|--------|-------------|--------|
| `email` | Contact's email address | CSV input |
| `segment` | Assigned firmographic segment | Stage 3 rules |
| `subject` | Generated email subject line | AI |
| `greetings` | Opening greeting (e.g. "Hi Maria,") | AI |
| `body` | Core email body with value prop and CTA | AI |
| `signature` | Fixed sign-off | Constant |
| `complete_email` | Full draft: greetings + body + signature | Assembled |
| `model` | OpenAI model used | Config |
| `input_tokens` | Prompt tokens consumed | OpenAI API |
| `output_tokens` | Completion tokens consumed | OpenAI API |
| `total_tokens` | Total tokens | Computed |
| `cost_usd` | Estimated cost for this email | Computed |

### Example Output Row

```
email:           maria.martinez@beachstays.com
segment:         general
subject:         Unlock Data-Driven Pricing for Your Mixed Portfolio
greetings:       Hi Maria,
body:            I noticed Maria's Hospitality manages a mixed portfolio
                 with Escapia. PriceLabs is a dynamic pricing tool that
                 helps hospitality leaders like you maximize revenue with
                 data-driven insights—all from a single dashboard, no
                 matter the property type.

                 Setup is quick and seamless with Escapia. Would you be
                 open to a quick demo or free trial to see how PriceLabs
                 can simplify pricing for your team?
signature:       Best regards,
                 Shreyas Jadhav
                 PriceLabs
model:           gpt-4.1
cost_usd:        $0.001522
```

---

## 16. Cost Model

### Per-Email Cost Estimates

Using ~350 input tokens and ~115 output tokens per email (typical):

| Model | Cost per Email | 100 Emails | 1,000 Emails |
|-------|---------------:|-----------:|-------------:|
| gpt-4.1 | ~$0.0016 | ~$0.16 | ~$1.60 |
| gpt-4.1-mini | ~$0.0003 | ~$0.03 | ~$0.33 |
| gpt-4.1-nano | ~$0.0001 | ~$0.01 | ~$0.08 |
| gpt-4o | ~$0.0020 | ~$0.20 | ~$2.03 |
| gpt-4o-mini | ~$0.0001 | ~$0.01 | ~$0.12 |

### Batch Discount

When using batch mode (11+ contacts), OpenAI charges **50% less**. The numbers above are for realtime; halve them for batch runs.

### Recommendation

- **Testing:** Use `gpt-4.1-nano` — cheapest, fast, good enough to verify the pipeline.
- **Production:** Use `gpt-4.1` or `gpt-4.1-mini` — best quality-to-cost ratio.
- **Budget runs at scale:** Use `gpt-4.1-nano` in batch mode — 1,000 emails for ~$0.04.

---

## 17. Terminal Log Walkthrough

When you run `python main.py`, here is exactly what you see and what each line means:

```
╔══════════════════════════════════════════════════════════════╗
║   GTM OUTBOUND AI ENGINE                                     ║
╚══════════════════════════════════════════════════════════════╝

================================================================
  STAGE 1 · DATA LOAD                                          ← Pure I/O. CSV → DataFrame.
================================================================
[LOAD] Loaded 525 rows from database.csv
[LOAD] Columns: [email, first_name, last_name, ...]

================================================================
  STAGE 2 · ELIGIBILITY FILTER  (deterministic, no AI)          ← Business rules. No AI.
================================================================
[FILTER] Applying eligibility rules on 525 contacts …
[FILTER]   ├─ type == 'prospect'        : 312 pass              ← 213 are not prospects
[FILTER]   ├─ Unsubscribed == FALSE      : 480 pass              ← 45 unsubscribed
[FILTER]   ├─ is_blocked_domain == FALSE  : 510 pass              ← 15 blocked
[FILTER]   ├─ total_emails_sent == 0      : 198 pass              ← 327 already emailed
[FILTER]   └─ Combined: 142 eligible, 383 dropped               ← AND of all four

================================================================
  STAGE 3 · FIRMOGRAPHIC SEGMENTATION  (deterministic, no AI)   ← Business rules. No AI.
================================================================
[SEGMENT] Assigning firmographic segments to 290 contacts …
[SEGMENT]   ├─ early_stage     : 45
[SEGMENT]   ├─ enterprise      : 12
[SEGMENT]   ├─ general         : 180
[SEGMENT]   ├─ growth_pms      : 53
[SEGMENT]   └─ Total: 290

================================================================
  STAGE 4 · CONTACT LIMIT                                      ← Cap for this run.
================================================================
[LIMIT] OUTBOUND_LIMIT=5  →  5 contacts to process

================================================================
  STAGE 5 · AI EMAIL GENERATION  (AI is invoked here)           ← AI STARTS HERE
================================================================
[AI-CONFIG] Model: gpt-4.1
[AI-CONFIG] Batch threshold: 10

[PIPELINE] Mode: REALTIME  (5 contacts, <= 10 threshold)
[PIPELINE] Each contact → segment → prompt → AI call → email

── Contact 1/5: maria@beachstays.com ──────────────────────────
[SEGMENT-LOOKUP] maria@beachstays.com  → general                ← Deterministic lookup
[SIZE-LOOKUP]    maria@beachstays.com  → unknown (MU_count=0)   ← Deterministic lookup
[PROMPT]         maria@beachstays.com  → segment=general, ...   ← Prompt built (no AI)
[PROMPT]         Prompt length: 842 chars
[AI]    ⚡ Calling OpenAI  model=gpt-4.1  temp=0.4 …             ← AI CALL
[AI]    ✓ Response in 1.3s  tokens=357+101=458  cost=$0.001522  ← AI response received
[AI]      subject: Unlock Data-Driven Pricing for Your ...      ← Generated subject line
[DONE]   ✓ Email generated  (running total: $0.001522)

── Contact 2/5: carlos@gmail.com ──────────────────────────────
...                                                             ← Same pattern repeats

================================================================
  STAGE 6 · SAVE RESULTS                                       ← File I/O. No AI.
================================================================
[SAVE] 5 emails → results/generated_emails_1770993957.csv

================================================================
  SUMMARY
================================================================
[SUMMARY] Emails generated : 5
[SUMMARY] Segment breakdown: {'general': 3, 'early_stage': 2}
[SUMMARY] Total cost       : $0.008244 USD
[SUMMARY] Wall time        : 12.1s
[SUMMARY] Output file      : results/generated_emails_1770993957.csv
```

### Reading the Logs

- **`[LOAD]`** = Data load operations
- **`[FILTER]`** = Eligibility filter (deterministic rules)
- **`[SEGMENT]`** = Firmographic segment assignment (deterministic rules)
- **`[SEGMENT-LOOKUP]`** = Per-contact segment retrieval
- **`[SIZE-LOOKUP]`** = Per-contact company size derivation
- **`[PROMPT]`** = Prompt construction (no AI — just string building)
- **`[AI]`** = OpenAI API interaction (this is where money is spent)
- **`[BATCH-PREP]`** = Batch file preparation (no AI)
- **`[DONE]`** = Email successfully generated
- **`[SAVE]`** = File output
- **`[SUMMARY]`** = Run summary

---

## 18. How to Extend and Modify

### Change the email tone or word limit

Edit the `role_and_rules` string in `utils/prompt_builder.py`. Currently set to:

- Body under 120 words
- One clear CTA
- Sound human and friendly, not AI

### Add a new firmographic segment

1. Add the rule in `_assign_segment()` in `utils/filter_cold_outreach.py` — insert it at the right priority position.
2. Add the messaging angle in `_FIRMOGRAPHIC_ANGLES` in `utils/prompt_builder.py`.

### Add a new property type context

Add an entry to `_PROPERTY_TYPE_CONTEXT` in `utils/prompt_builder.py` with the raw property type string as the key (lowercase).

### Change the structured output fields

1. Edit the `ColdEmail` Pydantic model in `utils/ai_engine.py`.
2. Update `_build_result()` in the same file.
3. Update `_build_row()` in `main.py` to include the new fields in the output CSV.

### Change the signature

Edit `DEFAULT_SIGNATURE` in `utils/ai_engine.py`.

### Change the model

Set `OPENAI_MODEL` in your `.env` file. Supported models with built-in pricing: `gpt-4.1`, `gpt-4.1-mini`, `gpt-4.1-nano`, `gpt-4o`, `gpt-4o-mini`.

### Change the batch threshold

Edit `BATCH_THRESHOLD` in `utils/ai_engine.py` (default: `10`).

### Change the eligibility filter rules

Edit `filter_eligible_contacts()` in `utils/filter_cold_outreach.py`. Add or remove conditions from the mask.

### Change the enterprise title keywords

Edit the `_ENTERPRISE_TITLE_KEYWORDS` set in `utils/filter_cold_outreach.py`.

---

## 19. FAQ and Troubleshooting

### "Why did a contact get segment `general` instead of `enterprise`?"

The enterprise segment requires ALL THREE conditions:
1. MU_count >= 50
2. is_generic_domain == FALSE
3. job_title contains founder/ceo/revenue/director

If any one fails, the contact falls through to the next priority. Check the specific contact's values for those fields.

### "Why are so many contacts dropped at Stage 2?"

The four filter rules are AND-ed. Common drop reasons:
- `type` is `trial`, `customer`, or `lead` (not `prospect`)
- `Unsubscribed` is `TRUE`
- The domain is blocked
- `total_emails_sent` is greater than 0 (already been emailed)

Check the per-rule pass counts in the terminal log to see which rule is the biggest filter.

### "How do I test without spending money?"

Set `OPENAI_MODEL=gpt-4.1-nano` and `OUTBOUND_LIMIT=2` in your `.env`. A 2-email test run costs less than $0.001.

### "What happens if the OpenAI API call fails?"

In realtime mode, the exception propagates and the run stops. In batch mode, the engine checks for `failed` / `expired` / `cancelled` status and raises a `RuntimeError` with the error details.

### "Can I use a different AI provider?"

Currently the engine is built for OpenAI's API. To swap providers, you'd need to modify `ai_engine.py` — specifically `generate_email()` for realtime and the batch functions. The rest of the pipeline (filtering, segmentation, prompts, output) is provider-agnostic.

### "Where are the generated emails saved?"

In the `results/` folder (gitignored). Each run creates a new file: `results/generated_emails_<timestamp>.csv`.

### "What's in the `tmp/` folder?"

Batch API input files (`.jsonl`). These are intermediate files used when running in batch mode. Also gitignored.

### "Does order matter in the output?"

Yes. The output order matches the input CSV order (after filtering and limiting). In batch mode, results are re-sorted to match the original prompt order.
