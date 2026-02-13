# AI use justification (Part 2D)

## 1. Why use AI for this use case? What would it look like without AI?

**Why AI:** Cold email needs to feel personal (PMS, property type, region, company size) and varied. Doing that with static templates means either many rigid templates (hard to maintain, still repetitive) or one generic message (low reply rates). AI can compose one-off, natural-sounding copy that references the contact’s context without hand-writing every variant.

**Without AI:** You’d rely on:
- **Templates only:** e.g. “Hi {{first_name}}, we help {{PMS}} users in {{region}}…” with placeholders. Easy and cheap, but limited variety and easy to spot as templated.
- **Pre-written blocks:** Different paragraphs per segment/PMS/region, combined by rules. Better than one template, but combinatorics explode (segments × PMS × region × property type) and copy still feels formulaic.

AI is justified where we want **varied, context-aware copy** without maintaining hundreds of template combinations.

---

## 2. Keeping costs down at scale (e.g. 10,000 contacts/month)

- **Model choice:** Use `gpt-4o-mini` (or similar low-cost model), not GPT-4. Roughly an order of magnitude cheaper per token.
- **Limit scope:** Only send to a qualified prospect list (e.g. after filters: valid domain, not unsubscribed, segment/region criteria). Fewer contacts → fewer API calls.
- **Prompt design:** Short system + user prompt; ask for “under 120 words” so output tokens stay bounded. No long context dumps.
- **Batching and caps:** Process in batches; use `OUTBOUND_LIMIT` or a daily cap so one run can’t blow the budget. At 10k contacts/month, cost is still manageable with mini models and short prompts.
- **Caching:** If the same contact (same email + segment + key fields) is run again, reuse the last generated email instead of calling the API again.
- **Fallbacks:** For high-volume, low-touch segments, consider a single good template and use AI only for a subset (e.g. enterprise or high-intent) to balance cost and quality.

---

## 3. What genuinely needs AI vs. simpler logic?

| Part of the workflow | Needs AI? | Alternative |
|----------------------|-----------|-------------|
| **Who to contact (segmentation)** | No | Rules in code: PMS, MU_count, region, domain, etc. (current `segmentation.py`). |
| **Company size band** | No | Rules from MU_count: unknown / small / mid_market / enterprise. |
| **Building the prompt** | No | Template with placeholders filled from the row + segment (current `prompt_builder.py`). |
| **Writing the email body** | Yes | This is where variation and natural language matter. Templates can’t match the diversity of good cold email. |
| **Subject line** | Optional | Could be AI or a small set of A/B test templates. |
| **Sending / scheduling** | No | Handled by your email/CRM stack, not this script. |

**Summary:** Segmentation, targeting, and prompt assembly are rule- and template-driven. The only part that “genuinely” needs AI is the generation of the **email body** (and optionally subject) so each message can feel tailored without maintaining a huge template matrix.
