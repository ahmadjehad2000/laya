import pytest
from laya.common import build_sequence
from laya.agent import Agent


class Tokenizer:
    mask_token = "[MASK]"
    mask_token_id = 2
    cls_token_id = 0
    sep_token_id = 1
    def __call__(self, text, **kwargs):
        return {"input_ids": list(range(10, 10 + len(text.split())))}


Q = {"t": "choice", "ins": "Choose", "crit": {"a": "first", "b": "second"}}


def test_strict_core_refuses_lost_evidence_and_rubrics():
    with pytest.raises(ValueError, match="checkpoint limit"):
        build_sequence(Tokenizer(), "evidence " * 100, Q, max_len=30, strict=True)
    with pytest.raises(ValueError, match="Option description"):
        build_sequence(Tokenizer(), "short", {**Q, "crit": {"a": "long " * 60, "b": "short"}}, strict=True)
    with pytest.raises(ValueError, match="Instructions"):
        build_sequence(Tokenizer(), "short", {**Q, "ins": "long " * 200}, strict=True)


def test_strict_core_preserves_short_inputs():
    assert build_sequence(Tokenizer(), "short evidence", Q, strict=True) == build_sequence(Tokenizer(), "short evidence", Q)


def test_choice_stability_retains_original_and_counts_both_passes():
    agent = Agent.__new__(Agent)
    calls = []
    def predict(state, questions):
        calls.append(questions)
        return {"answers": {k: {"choice": next(iter(v["criteria"]))} for k,v in questions.items()},
                "usage": {"input_tokens": 20, "output_tokens": 0}}
    agent.system_one = predict
    result = agent.predict_checked("evidence", {"q": {"type": "choice", "criteria": {"a": "first", "b": "second"}}})
    assert result["answers"]["q"]["choice"] == "a"
    assert result["verification"]["review_required"] == ["q"]
    assert result["verification"]["alternate_answers"]["q"]["choice"] == "b"
    assert result["usage"]["input_tokens"] == 40
    assert list(calls[0]["q"]["criteria"]) == ["a", "b"]


def test_nonfinite_model_logits_cannot_become_a_label():
    import torch
    agent = Agent.__new__(Agent)
    agent.cfg = {}
    agent.tok = Tokenizer()
    agent.tok.pad_token_id = 3
    agent.device = torch.device("cpu")
    agent.dtype = torch.float32
    agent.temperature = [1, 1, 1]
    agent.temperature_by_options = {}
    agent.model = lambda *args: (torch.full((1, 2), float("nan")), torch.zeros((1, 2)))
    with pytest.raises(ValueError, match="Non-finite"):
        agent.predict("evidence", {"q": {"type": "choice", "instructions": "Choose", "criteria": ["a", "b"]}})
