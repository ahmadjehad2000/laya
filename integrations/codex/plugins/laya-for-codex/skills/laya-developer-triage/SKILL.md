---
name: laya-developer-triage
description: Classify repeated natural-language issue descriptions or summarized log records and prioritize review candidates with local Laya. Use for shared explicit labels or rubrics; raw-code classification, ordinary coding and debugging are handled directly by Codex.
---

Use `laya_predict_batch` with one concise state per issue or summarized log record. Score review urgency separately against a shared ordered rubric. This preview's multilingual checkpoint failed 3 of 4 raw-code file-role cases; do not delegate raw-code classification to it. Codex should inspect code directly. Natural-language issue classification is advisory and must be checked against the source.

Read the relevant source first. Keep a mapping from each stable item ID to its issue link or log timestamp outside the model state. Include only evidence needed for the decision; names alone are insufficient. Define an unknown label when the evidence cannot distinguish the categories. Do not send a whole repository as one state.

Group questions about the same item, and send up to 32 independent items per request. `choice` accepts a label-description map; `score` accepts an ordered list from least to most severe and returns a zero-based expected index; `noul` evaluates a stated proposition. Use the multilingual default for mixed-language material. `model: auto` requires prepared English and multilingual checkpoints. The typed-decisions checkpoint is specialized and is not the default for code review.

If input exceeds the token budget, make a faithful smaller excerpt or split the item. Report omitted coverage. If a batch partially fails, keep successful results and retry only failures when repair is possible. Never fill missing results with guessed predictions.

Inspect supporting evidence for consequential priorities and apparent contradictions. A confident label can still be wrong. Report disagreement or insufficient evidence as needing Codex review. Laya does not establish exploitability, approve a change, or prove correctness. Rank only scores using the same rubric and preserve ties.

Return a compact table of item, predicted category/score, source reference, and review note. Explain any source-based corrections. Do not call benchmark unless the user is investigating performance. If tools are unavailable or unsuitable, continue normally and say Laya was not used.
