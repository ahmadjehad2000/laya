"""File-reference classification keeps bulk records outside Codex context."""
import math
import uuid
from collections import Counter

from .local_files import artifact_dir, digest, encoded, workspace_file, write_new
from .validation import questions_check


def classify_file(runtime, workspace, input_path, questions, model=None,
                  min_probability=0.95, min_margin=0.5):
    import json

    if any(not isinstance(v, (float, int)) or not math.isfinite(v) or not 0 <= v <= 1
           for v in (min_probability, min_margin)):
        raise ValueError("Probability and margin must be finite values from 0 to 1")
    questions_check(questions, runtime.config)
    if any(q["type"] != "choice" for q in questions.values()):
        raise ValueError("File offload supports choice classification only; rubric reliability is not established")
    root, path, raw = workspace_file(workspace, input_path)
    items = json.loads(raw)
    if not isinstance(items, list) or not 1 <= len(items) <= 1000:
        raise ValueError("Supply a JSON array of 1–1000 {id,state} records")
    ids = [item.get("id") if isinstance(item, dict) else None for item in items]
    if any(not isinstance(i, str) or not 1 <= len(i) <= 120 for i in ids) or len(set(ids)) != len(ids):
        raise ValueError("Record IDs must be unique nonempty strings, at most 120 characters")
    if any(set(item) != {"id", "state"} for item in items):
        raise ValueError("Every record must contain exactly id and state")
    output = artifact_dir(root, "results") / (uuid.uuid4().hex + ".json")
    records, counts, review, devices = [], Counter(), [], set()
    batches, pending = [], []
    for item in items:
        if pending and (len(pending) >= runtime.config.max_items or
                        len(encoded([pending + [item], questions])) > runtime.config.max_request_bytes):
            batches.append(pending)
            pending = []
        pending.append(item)
    batches.append(pending)
    for group in batches:
        if len(encoded([group, questions])) > runtime.config.max_request_bytes:
            batch = {"items": [{"id": item["id"], "error": {"type": "ValueError",
                                "message": "Record exceeds request byte limit; split evidence explicitly"}} for item in group]}
        else:
            batch = runtime.predict_batch(group, questions, model=model)
        for item in batch["items"]:
            needs_review = "error" in item
            if not needs_review:
                result = item["result"]
                devices.add(result["runtime"].get("device") or result.get("original_runtime", {}).get("device"))
                for qid, answer in result["answers"].items():
                    probs = answer.get("probabilities", {})
                    values = sorted(probs.values(), reverse=True)
                    label = answer.get("choice")
                    counts[qid + ":" + str(label)] += 1
                    needs_review |= (len(values) < 2 or probs.get(label, 0) < min_probability or
                                     values[0] - values[1] < min_margin or
                                     str(label).lower() in ("unknown", "other", "uncertain"))
            item["needs_review"] = bool(needs_review)
            if needs_review:
                review.append(item["id"])
            records.append(item)
    report = {"schema_version": 1, "source": str(path.relative_to(root)), "source_sha256": digest(raw),
              "questions": questions, "min_probability": min_probability, "min_margin": min_margin,
              "items": records, "scope": "Advisory; thresholds are not calibrated accuracy guarantees"}
    write_new(output, encoded(report))
    return {"artifact": str(output), "source_sha256": digest(raw), "records": len(records),
            "succeeded": sum("result" in item for item in records), "failed": sum("error" in item for item in records),
            "label_counts": dict(counts), "needs_review": len(review), "review_ids_preview": review[:20],
            "review_ids_truncated": len(review) > 20, "devices": sorted(d for d in devices if d),
            "cloud_model_calls_by_laya": 0,
            "scope": "Local classification only. Validate consequential labels; retrieve review records from source."}
