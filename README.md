# GTM Outbound AI Engine

This project generates personalized outbound emails for prospects using deterministic segmentation + AI personalization.

## Setup

1. Install dependencies:
   pip install pandas openai

2. Set your API key:
   export OPENAI_API_KEY="your_api_key_here"

3. Place the CSV file in the root directory as:
   Unified Database Sample.csv

4. Run:
   python main.py

## Architecture

- segmentation.py → deterministic segmentation logic
- prompt_builder.py → structured prompt generation
- ai_engine.py → AI call layer
- main.py → orchestration layer

AI is used only for email generation. Segmentation is rule-based to minimize cost and increase reliability.