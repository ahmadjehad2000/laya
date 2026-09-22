---
name: laya-rubric
description: Apply a user's explicit classification criteria or ordered scoring rubric repeatedly with local Laya. Use for comparable evidence-backed records, not open-ended reasoning or factual verification.
---

Preserve the user's criteria. Resolve materially ambiguous rubric meanings before scoring; do not invent a different objective. Use label-description maps for `choice`, ordered level descriptions for `score`, and a clearly stated proposition for `noul`. Each question needs `type` and nonempty `instructions`. Choice and score support 2–16 criteria. Related questions share one state; independent records use `laya_predict_batch`.

Keep stable item IDs and external source references. Return the zero-based expected score together with the rubric legend; it may be fractional and is not a percentage or a selected discrete level. `noul` is P(true). Choice/score confidence and noul confidence have different meanings; do not compare them as a universal probability of correctness.

Review the source when outputs contradict explicit evidence. Mark unsupported conclusions as needing review. Missing evidence is not automatically false. Use an unknown choice or leave a record unscored when the supplied rubric cannot express insufficient information.

Only compare or rank records scored with the same rubric and checkpoint. State the model and rubric used. Avoid automatic confidence thresholds unless a task-specific labeled evaluation supports them. Do not treat action probabilities as execution permission.

On truncation errors, reduce input faithfully or split the work and preserve coverage notes. On tool unavailability, continue without Laya and disclose it. Benchmark only for a requested performance investigation.
