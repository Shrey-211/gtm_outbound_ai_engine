# GTM Outbound AI Engine

Generates **personalised cold outreach emails** at scale using OpenAI. Each email is tailored by firmographic segment, property type, PMS, region, and company size so every prospect gets a relevant first-touch message.

Built for the PriceLabs outbound team.

---

## Setup

### Prerequisites

- Python 3.11+
- An OpenAI API key with access to the model you want to use

### 1. Clone and install

```bash
git clone <repo-url>
cd gtm_outbound_ai_engine
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

Copy the example env file and add your API key:

```bash
cp .env.example .env
```

Edit `.env`:

```
OPENAI_API_KEY=sk-your-key-here
OUTBOUND_LIMIT=5
OPENAI_MODEL=gpt-4.1
```

| Variable          | Description                                      | Default              |
|-------------------|--------------------------------------------------|----------------------|
| `OPENAI_API_KEY`  | Your OpenAI API key                              | *required*           |
| `OPENAI_MODEL`    | Model to use for generation                      | `gpt-4.1`           |
| `OUTBOUND_LIMIT`  | Number of contacts to process                    | `5`                  |
| `CSV_PATH`        | Path to the input contact CSV                    | `data/database.csv`  |

### 3. Add your contact data

Place your contact CSV in the `data/` folder. The default path is `data/database.csv`. Set `CSV_PATH` in `.env` to point to a different file.

**Required columns for filtering:** `type`, `Unsubscribed`, `is_blocked_domain`, `total_emails_sent`.

**Required columns for segmentation:** `MU_count`, `is_generic_domain`, `PMS`, `job_title`.

**Required columns for personalisation:** `email`, `first_name`, `company_name`, `type_of_properties_managed`, `region`.

Other columns are preserved but not actively used. See `data/database_types.csv` for the full field reference.

### 4. Run

```bash
python main.py
```

Output CSV is written to the `results/` folder with a timestamped filename.

---

## Output Format

Each row in the output CSV contains:

| Column           | Description                                              |
|------------------|----------------------------------------------------------|
| `email`          | Contact email address                                    |
| `segment`        | Assigned firmographic segment (e.g. `enterprise`, `growth_pms`) |
| `subject`        | Generated email subject line                             |
| `greetings`      | Opening greeting (e.g. "Hi Maria,")                      |
| `body`           | Core email body with value prop and CTA                  |
| `signature`      | Fixed sign-off (not AI-generated)                        |
| `complete_email` | Full ready-to-send draft (greetings + body + signature)  |
| `model`          | OpenAI model used                                        |
| `input_tokens`   | Prompt tokens consumed                                   |
| `output_tokens`  | Completion tokens consumed                               |
| `total_tokens`   | Total tokens                                             |
| `cost_usd`       | Estimated cost for this email                            |

---

## Architecture

```
main.py
  |
  |-- filter_cold_outreach.py   Load CSV, filter eligible contacts, assign firmographic segments
  |-- segmentation.py           Segment lookups + company size band
  |-- prompt_builder.py         Build prompt with firmographic angle + property-type context
  |-- ai_engine.py              OpenAI call (realtime or batch) + cost tracking
```

### Pipeline flow

```
CSV  →  Filter  →  Segment  →  Limit  →  Build Prompt  →  Generate (AI)  →  Output CSV
```

1. **Load** (Stage 1): Read contact CSV into a DataFrame.
2. **Filter** (Stage 2): Remove ineligible contacts using four deterministic rules — must be a prospect, not unsubscribed, not blocked, and never previously emailed (`total_emails_sent == 0`).
3. **Segment** (Stage 3): Each contact is assigned a firmographic segment (`enterprise`, `growth_pms`, `early_stage`, or `general`) based on listing count, PMS presence, domain type, and job title.
4. **Limit** (Stage 4): Apply `OUTBOUND_LIMIT` to cap how many contacts are processed.
5. **Prompt** (Stage 5): A prompt is built with a firmographic segment angle (primary) and property-type context (secondary), plus the contact's personalisation fields.
6. **Generate** (Stage 5): OpenAI produces a structured response with `subject`, `greetings`, and `body`. A fixed signature is appended.
7. **Output** (Stage 6): Results are written to a timestamped CSV in `results/`.

### Eligibility Filter (Stage 2)

Contacts must pass ALL four rules to be eligible for cold outreach:

| Rule | Column              | Condition    | Why                                                  |
|:----:|---------------------|--------------|------------------------------------------------------|
| 1    | `type`              | `== prospect`| Don't email existing users, trials, or customers     |
| 2    | `Unsubscribed`      | `== FALSE`   | Legal compliance — respect opt-outs                  |
| 3    | `is_blocked_domain` | `== FALSE`   | Don't email competitors or known spam domains        |
| 4    | `total_emails_sent` | `== 0`       | Only contact people who have never been emailed      |

AI does not decide who to contact. Business logic does.

### Firmographic Segmentation (Stage 3)

Each eligible contact is assigned one segment based on deterministic rules (first match wins):

| Priority | Segment        | Rules                                                                                       | Messaging Focus                                  |
|:--------:|----------------|---------------------------------------------------------------------------------------------|--------------------------------------------------|
| 1        | `enterprise`   | MU_count >= 50, non-generic domain, job title contains Founder/CEO/Revenue/Director         | Scale, automation, portfolio optimisation         |
| 2        | `growth_pms`   | PMS present, 10 <= MU_count <= 49                                                           | Integration benefits, revenue uplift via PMS      |
| 3        | `early_stage`  | is_generic_domain == TRUE, MU_count < 10                                                    | Education, quick wins, lightweight onboarding     |
| 4        | `general`      | Everything else that passed the filter                                                      | Broad PriceLabs intro, trial/demo CTA             |

Property type (`type_of_properties_managed`) is used as a secondary personalisation layer within the prompt — it does not determine the segment.

### Structured Output

Email responses use OpenAI's **Structured Outputs** (JSON schema mode) via a Pydantic model. This guarantees the response always contains exactly `subject`, `greetings`, and `body` — no parsing or regex needed.

---

## Realtime vs Batch Processing

The engine automatically picks the right processing mode based on the number of contacts:

| Contacts     | Mode       | Behaviour                                    |
|--------------|------------|----------------------------------------------|
| 1 - 10       | **Realtime** | Emails generated one-by-one, instant results |
| 11+          | **Batch**    | All emails submitted as a single batch job   |

The threshold is controlled by `BATCH_THRESHOLD` in `ai_engine.py` (default: `10`).

### How Batch Processing Works

When `OUTBOUND_LIMIT` exceeds the threshold, the engine switches to the [OpenAI Batch API](https://platform.openai.com/docs/guides/batch):

1. **Prepare**: All prompts are written to a `.jsonl` file in `tmp/`, one request per line.
2. **Upload & Submit**: The file is uploaded to OpenAI and a batch job is created.
3. **Poll**: The engine polls every 15 seconds, logging progress to the terminal.
4. **Parse**: Results are downloaded, parsed back into structured `ColdEmail` objects, and mapped to the original contact order.

### Why Batch?

**50% cost savings**: OpenAI charges half price for batch requests compared to realtime API calls. At scale this is significant:

| Contacts | Realtime Cost (gpt-4.1) | Batch Cost (gpt-4.1) | Savings |
|----------|------------------------|-----------------------|---------|
| 100      | ~$0.20                 | ~$0.10                | $0.10   |
| 1,000    | ~$2.00                 | ~$1.00                | $1.00   |
| 10,000   | ~$20.00                | ~$10.00               | $10.00  |

**Higher rate limits**: The Batch API has a separate, substantially higher rate-limit pool. Batch avoids throttling entirely — you submit all requests at once.

**Tradeoff**: Batch is asynchronous. Jobs typically complete in a few minutes but can take up to 24 hours. For small runs (10 or fewer), the engine uses realtime for instant results.

---

## Repo Structure

```
gtm_outbound_ai_engine/
  main.py                    Entrypoint — orchestrates the full 6-stage pipeline
  requirements.txt           Python dependencies
  .env.example               Template for environment variables
  .gitignore
  PRODUCT_DOCUMENT.md        Full product/onboarding document
  data/
    database.csv             Full contact database (525 contacts)
    database_dummy.csv       Sample contact database (101 contacts)
    database_types.csv       Field definitions reference
  utils/
    filter_cold_outreach.py  Load CSV, filter eligibility, assign firmographic segments
    segmentation.py          Segment lookups + company size band
    prompt_builder.py        Build prompts with firmographic angles + property-type context
    ai_engine.py             OpenAI integration (realtime + batch) + cost tracking
    PROMPT.md                Prompt architecture docs (how to modify prompts)
  results/                   Generated email CSVs (gitignored)
  tmp/                       Batch input files (gitignored)
```

---

## Extending

See [`utils/PROMPT.md`](utils/PROMPT.md) for detailed instructions on:

- Changing email tone, word limits, or CTA style
- Adding new firmographic segments or property-type contexts
- Modifying the structured output fields
- Changing the eligibility filter rules
- Changing the signature or model

For the full onboarding and technical reference, see [`PRODUCT_DOCUMENT.md`](PRODUCT_DOCUMENT.md).

---

## Dependencies

| Package        | Purpose                         |
|----------------|--------------------------------|
| `pandas`       | CSV loading and DataFrame ops  |
| `openai`       | OpenAI API client              |
| `pydantic`     | Structured output schema       |
| `python-dotenv`| Load `.env` variables          |
