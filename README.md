# GTM Outbound AI Engine

Generates **personalised cold outreach emails** at scale using OpenAI. Each email is tailored by property type, PMS, region, and company size so every prospect gets a relevant first-touch message.

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

| Variable          | Description                                      | Default                  |
|-------------------|--------------------------------------------------|--------------------------|
| `OPENAI_API_KEY`  | Your OpenAI API key                              | *required*               |
| `OPENAI_MODEL`    | Model to use for generation                      | `gpt-4.1`               |
| `OUTBOUND_LIMIT`  | Number of contacts to process                    | `5`                      |
| `CSV_PATH`        | Path to the input contact CSV                    | `data/database_dummy.csv`|

### 3. Add your contact data

Place your contact CSV in the `data/` folder. The default path is `data/database_dummy.csv`. Set `CSV_PATH` in `.env` to point to a different file.

Required columns: `email`, `first_name`, `type_of_properties_managed`, `MU_count`. Other columns (`company_name`, `PMS`, `region`, `last_name`, etc.) are used for personalisation when present. See `data/database_types.csv` for the full field reference.

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
| `segment`        | Assigned segment (e.g. `vacation_rental`, `hotel`)       |
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
  |-- filter_cold_outreach.py   Load contacts from CSV
  |-- segmentation.py           Segment by property type + company size
  |-- prompt_builder.py         Build prompt with segment-specific angle
  |-- ai_engine.py              OpenAI call (realtime or batch) + cost tracking
```

### Pipeline flow

```
CSV  ->  Segment  ->  Build Prompt  ->  Generate (AI)  ->  Output CSV
```

1. **Load**: Read contact CSV into a DataFrame.
2. **Segment**: Each contact is assigned a segment based on `type_of_properties_managed` (e.g. `vacation_rental`, `hotel`, `boutique_hotel`). Company size is derived from `MU_count`.
3. **Prompt**: A prompt is built with a segment-specific angle telling the AI which PriceLabs features to highlight, plus the contact's personalisation fields.
4. **Generate**: OpenAI produces a structured response with `subject`, `greetings`, and `body`. A fixed signature is appended.
5. **Output**: Results are written to a timestamped CSV in `results/`.

### Segmentation

Contacts are segmented by property type. Each segment gets a tailored angle that guides the AI on what to emphasise:

| Segment              | Angle                                                        |
|----------------------|--------------------------------------------------------------|
| `vacation_rental`    | Dynamic pricing, off-season occupancy, PMS sync              |
| `short_term_rental`  | Market data nightly rates, revenue per listing               |
| `hotel`              | Demand-based rates, comp-set tracking, channel managers      |
| `boutique_hotel`     | Compete with chains, hyper-local intelligence                |
| `serviced_apartment` | Length-of-stay pricing, corporate vs leisure demand           |
| `mixed_portfolio`    | Single dashboard, per-listing strategies, portfolio analytics|
| `general`            | Broad intro to PriceLabs dynamic pricing                     |

### Structured Output

Email responses use OpenAI's **Structured Outputs** (JSON schema mode) via a Pydantic model. This guarantees the response always contains exactly `subject`, `greetings`, and `body` - no parsing or regex needed.

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
3. **Poll**: The engine polls every 15 seconds, logging progress to the terminal:
   ```
   [BATCH] 100 emails queued - using OpenAI Batch API (50% cheaper, may take a few minutes)...
   [BATCH] Submitted batch batch_abc123 with file file_xyz789
   [BATCH] Status: in_progress | Progress: 45/100 | Failed: 0
   [BATCH] Status: completed | Progress: 100/100 | Failed: 0
   ```
4. **Parse**: Results are downloaded, parsed back into structured `ColdEmail` objects, and mapped to the original contact order.

### Why Batch?

**50% cost savings**: OpenAI charges half price for batch requests compared to realtime API calls. At scale this is significant:

| Contacts | Realtime Cost (gpt-4.1) | Batch Cost (gpt-4.1) | Savings |
|----------|------------------------|-----------------------|---------|
| 100      | ~$0.20                 | ~$0.10                | $0.10   |
| 1,000    | ~$2.00                 | ~$1.00                | $1.00   |
| 10,000   | ~$20.00                | ~$10.00               | $10.00  |

**Higher rate limits**: The Batch API has a separate, substantially higher rate-limit pool. With realtime calls, generating 500+ emails would hit rate limits and require retry logic. Batch avoids this entirely - you submit all requests at once and OpenAI processes them within its own rate-limit budget.

**Tradeoff**: Batch is asynchronous. Jobs typically complete in a few minutes but can take up to 24 hours. For small runs (10 or fewer), the engine uses realtime for instant results.

---

## Repo Structure

```
gtm_outbound_ai_engine/
  main.py                    Entrypoint - orchestrates the full pipeline
  requirements.txt           Python dependencies
  .env.example               Template for environment variables
  .gitignore
  data/
    database_dummy.csv       Sample contact database (101 contacts)
    database.csv             Full contact database
    database_types.csv       Field definitions reference
  utils/
    filter_cold_outreach.py  Load contacts from CSV
    segmentation.py          Segment by property type + company size band
    prompt_builder.py        Build prompts with segment-specific angles
    ai_engine.py             OpenAI integration (realtime + batch) + cost tracking
    PROMPT.md                Prompt architecture docs (how to modify prompts)
  results/                   Generated email CSVs (gitignored)
  tmp/                       Batch input files (gitignored)
```

---

## Extending

See [`utils/PROMPT.md`](utils/PROMPT.md) for detailed instructions on:

- Changing email tone, word limits, or CTA style
- Adding new property type segments
- Modifying the structured output fields
- Changing the signature or model

---

## Dependencies

| Package        | Purpose                         |
|----------------|--------------------------------|
| `pandas`       | CSV loading and DataFrame ops  |
| `openai`       | OpenAI API client              |
| `pydantic`     | Structured output schema       |
| `python-dotenv`| Load `.env` variables          |
