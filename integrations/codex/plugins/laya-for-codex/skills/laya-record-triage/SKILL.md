---
name: laya-record-triage
description: Classify multiple document excerpts or support tickets and score their urgency with local Laya, including Arabic and mixed-language records. Use when repeated items can be judged against shared explicit criteria.
---

For records already stored in a workspace JSON array of `{id,state}`, prefer `laya_classify_file` with choice questions. Pass the file path instead of reading all records into Codex context; inspect the returned review items and validate consequential decisions. For other formats, read records using available file or connector tools within the user's request. Preserve each source locator in an ID-to-source mapping. Laya does not fetch attachments.

Choose labels with concise definitions, including unknown when evidence is insufficient. For tickets, possible labels are billing, technical, sales, and unknown. Keep urgency separate from department. Use `laya_predict_batch` with independent `{id,state}` entries and shared `questions`; batch related questions on each state. Default to multilingual. Do not translate away details that determine the answer.

Example questions:

```json
{
  "department": {"type":"choice","instructions":"Who handles this request?","criteria":{"billing":"payments and refunds","technical":"software failures","sales":"new purchases","unknown":"insufficient evidence"}},
  "refund": {"type":"noul","instructions":"The customer explicitly requests a refund."}
}
```

Keep state short enough for the checkpoint's actual token budget, including question text and labels. If rejected, shorten faithfully or split; disclose omitted document coverage. Do not silently discard qualifiers, negations, or conflicting evidence.

Return per-item results with source references, incomplete items, and material disagreements with source evidence. Probability is an advisory model estimate. Do not send replies, move documents, issue refunds, or change ticket state merely because the model suggests it. Those actions require the user's task authorization and normal Codex controls.

The preview evaluation found errors on sales-versus-billing and explicit refund negation. Check negations and requested actions directly in the source before reporting a decision as supported. Do not automate ticket changes from these predictions.

If Laya is unavailable, continue using the available evidence and disclose that it was not used. Avoid benchmarking during ordinary triage.
