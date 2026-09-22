"""Small, dependency-free metrics with explicit denominators."""
import math
import statistics


def percentile(values, fraction):
    ordered = sorted(values)
    if not ordered or not 0 <= fraction <= 1:
        raise ValueError("Need nonempty values and a fraction in [0,1]")
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def latency(values):
    return {"n": len(values), "p50_ms": percentile(values, .5),
            "p95_ms": percentile(values, .95), "mean_ms": statistics.mean(values),
            "min_ms": min(values), "max_ms": max(values), "samples_ms": values}


def classification(expected, predicted, labels):
    if len(expected) != len(predicted) or not expected:
        raise ValueError("Expected and predicted must have the same nonzero length")
    correct = sum(a == b for a, b in zip(expected, predicted))
    per_label = {}
    for label in labels:
        tp = sum(a == label and b == label for a, b in zip(expected, predicted))
        fp = sum(a != label and b == label for a, b in zip(expected, predicted))
        fn = sum(a == label and b != label for a, b in zip(expected, predicted))
        per_label[label] = {"support": expected.count(label), "tp": tp, "fp": fp, "fn": fn,
                            "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0}
    return {"n": len(expected), "correct": correct, "accuracy": correct / len(expected),
            "macro_f1": statistics.mean(x["f1"] for x in per_label.values()), "per_label": per_label}


def rubric_metrics(expected, predicted, levels):
    if len(expected) != len(predicted) or not expected or levels < 2:
        raise ValueError("Invalid rubric metric inputs")
    valid = [(a, b) for a, b in zip(expected, predicted) if b is not None]
    # Failures count as wrong for rounded accuracy; MAE is explicitly valid-only.
    return {"n": len(expected), "valid": len(valid), "errors": len(expected) - len(valid),
            "rounded_correct": sum(a == math.floor(b + .5) for a, b in valid),
            "rounded_accuracy": sum(a == math.floor(b + .5) for a, b in valid) / len(expected),
            "mae_valid": statistics.mean(abs(a - b) for a, b in valid) if valid else None,
            "normalized_mae_valid": statistics.mean(abs(a - b) / (levels - 1) for a, b in valid) if valid else None}
