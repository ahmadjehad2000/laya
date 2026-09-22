import pytest
from laya_codex_companion.context import context_file, select_excerpts


def test_context_keeps_uncertainty_source_ids_and_explicit_truncation():
    items = [{"id": "a", "state": "original evidence"}, {"id": "b", "state": "irrelevant"},
             {"id": "c", "state": "uncertain evidence"}]
    def prediction(key, label, score, review=False):
        return {"id": key, "needs_review": review, "result": {"answers": {"relevance": {
            "choice": label, "probabilities": {"relevant": score}}}}}
    predictions = [prediction("a", "relevant", .99), prediction("b", "irrelevant", .01),
                   prediction("c", "irrelevant", .4, True)]
    selected = select_excerpts(items, predictions, 20, 8)
    assert [r["id"] for r in selected] == ["a", "c"]
    assert selected[0]["excerpt"] == "original evidence"
    assert selected[1]["truncated"] and sum(len(r["excerpt"]) for r in selected) == 20


@pytest.mark.parametrize("kwargs", [{"query": ""}, {"query": "x" * 501},
    {"max_chars": 0}, {"max_chars": True}, {"max_records": 33}])
def test_invalid_context_budget_fails_before_loading(kwargs):
    with pytest.raises(ValueError):
        context_file(None, ".", "missing.json", **{"query": "task", **kwargs})
