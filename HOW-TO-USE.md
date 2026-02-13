# How to use the Outbound Email Generator (for marketers)

This tool generates personalized cold emails for prospects using your contact list. You don’t need to code—just follow these steps.

---

## What you need

1. **A computer with Python installed** (Python 3.8 or newer).  
   - Check: open Terminal (Mac/Linux) or Command Prompt (Windows) and type `python --version`. If you see a version number, you’re set.
2. **The contact list** as a CSV file.  
   - Use the same column names as the sample (e.g. `email`, `first_name`, `company_name`, `PMS`, `region`, `type_of_properties_managed`, `type`, `MU_count`).  
   - Save it as `database.csv` inside the `data` folder, or you can use a different file (see “Optional” below).
3. **An OpenAI API key** (for the AI that writes the emails).  
   - Get one at [platform.openai.com](https://platform.openai.com).  
   - Create a file named `.env` in the project folder with this line (replace with your key):  
     `OPENAI_API_KEY=sk-your-key-here`

---

## Step-by-step

1. **Install the tool (one time)**  
   - Open Terminal/Command Prompt and go to the project folder.  
   - Run:  
     `pip install -r requirements.txt`

2. **Add your data**  
   - Put your prospect CSV in the `data` folder and name it `database.csv`.  
   - The tool only uses rows where `type` is `prospect`.

3. **Run the generator**  
   - In the same project folder, run:  
     `python main.py`  
   - It will create a file called `generated_emails.csv` in the project folder.

4. **Use the output**  
   - Open `generated_emails.csv` in Excel or Google Sheets.  
   - You’ll see: contact email, segment, and the generated email. Copy into your outbound tool as needed.

---

## Optional

- **Limit how many emails are generated (saves cost)**  
  Before running, you can set how many prospects to process (default is 5).  
  - Windows: `set OUTBOUND_LIMIT=10` then `python main.py`  
  - Mac/Linux: `OUTBOUND_LIMIT=10 python main.py`  
  Replace `10` with any number you want.

- **Use a different CSV file or location**  
  - Windows: `set CSV_PATH=C:\path\to\your\file.csv` then `python main.py`  
  - Mac/Linux: `CSV_PATH=/path/to/your/file.csv python main.py`

---

## Personalization

Emails are tailored using:

- **PMS** (e.g. Guesty, Hostaway)  
- **Property type** (e.g. Vacation Rental, Boutique Hotel)  
- **Region** (e.g. North America, Europe)  
- **Company size** (derived from listing count when available)

The tool decides a “segment” for each contact (e.g. enterprise, growth_hostaway) and the AI writes one short email per prospect (under 120 words, with a clear CTA).

---

## If something goes wrong

- **“CSV not found”**  
  Make sure `data/database.csv` exists, or set `CSV_PATH` to your file’s full path.

- **“OPENAI_API_KEY” or API errors**  
  Check that your `.env` file is in the project folder and contains `OPENAI_API_KEY=sk-...` with a valid key.

- **No emails in the output**  
  Ensure your CSV has a column named `type` and at least some rows with value `prospect`.

For technical details and how to extend the project, see **PROMPT.md**.
