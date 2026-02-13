# How to Use - GTM Outbound AI Engine

A step-by-step guide for generating personalised cold outreach emails. No coding knowledge required beyond running a few terminal commands.

---

## What This Tool Does

You give it a CSV of contacts. It generates a personalised cold email for each contact, tailored to their property type, PMS, region, and company size. Emails are saved to a CSV file you can import into your outreach tool.

Each email includes:
- A subject line
- A personalised greeting
- A body with a relevant PriceLabs value prop and a clear CTA
- A fixed signature

---

## First-Time Setup (One Time Only)

### Step 1: Install Python

Download and install Python 3.11 or newer from [python.org](https://www.python.org/downloads/). During installation, check the box that says **"Add Python to PATH"**.

### Step 2: Open a Terminal

- **Windows**: Search for "PowerShell" in the Start menu and open it.
- **Mac/Linux**: Open the "Terminal" app.

Navigate to the project folder:

```bash
cd path/to/gtm_outbound_ai_engine
```

### Step 3: Create a Virtual Environment

```bash
python -m venv venv
```

Activate it:

```bash
# Windows (PowerShell)
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate
```

You should see `(venv)` at the start of your terminal prompt.

### Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 5: Configure Your API Key

1. Open the file `.env.example` in any text editor
2. Save a copy as `.env` in the same folder
3. Replace the placeholder with your actual OpenAI API key:

```
OPENAI_API_KEY=sk-your-actual-key-here
OUTBOUND_LIMIT=5
OPENAI_MODEL=gpt-4.1
```

---

## Running the Tool

### Basic Run

Make sure your virtual environment is activated (`(venv)` visible in the terminal), then:

```bash
python main.py
```

This processes the first 5 contacts from `data/database_dummy.csv` and saves the output to `results/generated_emails_<timestamp>.csv`.

### Process More Contacts

Edit `OUTBOUND_LIMIT` in your `.env` file:

```
OUTBOUND_LIMIT=50
```

Or set it directly when running:

```bash
# Windows (PowerShell)
$env:OUTBOUND_LIMIT="50"; python main.py

# Mac / Linux
OUTBOUND_LIMIT=50 python main.py
```

### Use a Different Contact CSV

Edit `CSV_PATH` in your `.env` file:

```
CSV_PATH=data/database.csv
```

Or set it directly:

```bash
# Windows (PowerShell)
$env:CSV_PATH="data/database.csv"; python main.py

# Mac / Linux
CSV_PATH=data/database.csv python main.py
```

---

## Understanding the Output

Open the generated CSV in Excel, Google Sheets, or any spreadsheet tool. Key columns:

| Column           | What It Is                                                  |
|------------------|-------------------------------------------------------------|
| `email`          | The contact's email address                                 |
| `segment`        | What category they were placed in (e.g. `hotel`, `vacation_rental`) |
| `subject`        | The email subject line - copy this into your outreach tool  |
| `complete_email` | The full email draft ready to send (greeting + body + signature) |
| `cost_usd`       | How much this email cost to generate                        |

The `greetings`, `body`, and `signature` columns contain the individual parts if you need to customise them separately.

---

## Small Run vs Large Run

The tool automatically picks the best processing mode:

| Contacts   | What Happens                                                        |
|------------|---------------------------------------------------------------------|
| **1 - 10** | Emails are generated one at a time. Results appear in a few seconds.|
| **11+**    | All emails are submitted as a batch job. Takes a few minutes but costs 50% less. |

When running a batch, you will see progress updates in the terminal:

```
[BATCH] 100 emails queued - using OpenAI Batch API (50% cheaper, may take a few minutes)...
[BATCH] Status: in_progress | Progress: 45/100 | Failed: 0
[BATCH] Status: completed | Progress: 100/100 | Failed: 0
Done: 100 emails -> results/generated_emails_1770983463.csv ($0.1200)
```

Just wait for it to finish. Do not close the terminal while a batch is running.

---

## Changing the Model

Edit `OPENAI_MODEL` in your `.env` file. Available options:

| Model            | Speed    | Quality  | Cost           |
|------------------|----------|----------|----------------|
| `gpt-4.1`       | Medium   | Highest  | $2.00 / $8.00 per 1M tokens  |
| `gpt-4.1-mini`  | Fast     | High     | $0.40 / $1.60 per 1M tokens  |
| `gpt-4.1-nano`  | Fastest  | Good     | $0.10 / $0.40 per 1M tokens  |
| `gpt-4o`        | Medium   | High     | $2.50 / $10.00 per 1M tokens |
| `gpt-4o-mini`   | Fast     | Good     | $0.15 / $0.60 per 1M tokens  |

For testing or large runs where cost matters, `gpt-4.1-nano` or `gpt-4o-mini` are good choices. For highest quality, use `gpt-4.1`.

---

## Preparing Your Contact CSV

Your CSV needs at minimum these columns:

| Column                          | Required | Description                       |
|---------------------------------|----------|-----------------------------------|
| `email`                         | Yes      | Contact's email address           |
| `first_name`                    | Yes      | Used in the greeting              |
| `type_of_properties_managed`    | Yes      | Drives segmentation and email angle |
| `MU_count`                      | No       | Listing count, used for company size |
| `company_name`                  | No       | Used for personalisation          |
| `PMS`                           | No       | Property management system name   |
| `region`                        | No       | Geographic region                 |

Missing or empty fields are handled gracefully - the AI will skip mentioning them in the email rather than producing awkward copy.

Accepted values for `type_of_properties_managed`:
- Vacation Rental
- Short-term Rental
- Hotel
- Boutique Hotel
- Serviced Apartment
- Mixed

Any other value (or empty) will use a general PriceLabs intro angle.

---

## Troubleshooting

**"CSV not found" error**
Check that your CSV file exists at the path shown in the error. Update `CSV_PATH` in `.env` if needed.

**"OPENAI_API_KEY" error**
Make sure your `.env` file exists and contains a valid API key. The key should start with `sk-`.

**Batch job says "failed" or "expired"**
This is rare. Try running again. If it persists, reduce `OUTBOUND_LIMIT` to test with fewer contacts first.

**No `(venv)` in the terminal prompt**
You need to activate the virtual environment. Run `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Mac/Linux).

**Emails look too generic**
Make sure your CSV has `type_of_properties_managed` filled in. This is the main field that drives personalisation. Also check that `PMS`, `region`, and `company_name` are populated where possible.
