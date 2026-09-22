import pytest

from benchmarks.metrics import classification, latency, rubric_metrics


def test_percentiles_preserve_raw_samples_and_interpolate():
    result = latency([40, 10, 30, 20])
    assert result["p50_ms"] == 25
    assert result["p95_ms"] == pytest.approx(38.5)
    assert result["samples_ms"] == [40, 10, 30, 20]


def test_errors_stay_in_accuracy_and_macro_f1_denominators():
    result = classification(["a", "a", "b", "b"], ["a", None, "a", "b"], ["a", "b"])
    assert result["accuracy"] == .5
    assert result["macro_f1"] == pytest.approx((.5 + 2 / 3) / 2)
    assert result["per_label"]["a"]["fn"] == 1


def test_rubric_mae_does_not_disguise_errors_as_valid_predictions():
    result = rubric_metrics([0, 1, 3], [.2, 1.4, None], 4)
    assert result["errors"] == 1
    assert result["rounded_accuracy"] == pytest.approx(2 / 3)
    assert result["mae_valid"] == pytest.approx(.3)
    assert result["normalized_mae_valid"] == pytest.approx(.1)
