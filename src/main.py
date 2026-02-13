import pandas as pd
from segmentation import segment_contact
from prompt_builder import build_prompt
from ai_engine import generate_email

def run():
    df = pd.read_csv("Unified Database Sample.csv")

    prospects = df[df["type"] == "prospect"]

    results = []

    for _, row in prospects.head(5).iterrows():  # limit for cost control
        segment = segment_contact(row)
        prompt = build_prompt(row, segment)
        email = generate_email(prompt)

        results.append({
            "email": row["email"],
            "segment": segment,
            "generated_email": email
        })

    output_df = pd.DataFrame(results)
    output_df.to_csv("generated_emails.csv", index=False)

    print("Done. Emails saved to generated_emails.csv")

if __name__ == "__main__":
    run()