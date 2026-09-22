from types import SimpleNamespace

import pytest

from laya_codex_companion.config import Config
from laya_codex_companion.validation import context_check, request_check


class Tokenizer:
    mask_token = "[MASK]"

    def __call__(self, value, **kwargs):
        return {"input_ids": list(range(len(value.split())))}


def agent():
    return SimpleNamespace(tok=Tokenizer(), cfg={"max_len": 40, "head_max_len": 30},
                           _to_internal=lambda q: {"t": q["type"], "ins": q["instructions"], "crit": q.get("criteria")})


Q = {"q": {"type": "choice", "instructions": "Choose role", "criteria": {"test": "test code", "app": "application code"}}}


def test_context_fit_and_overflow():
    assert context_check(agent(), "short evidence", Q)["q"] < 40
    with pytest.raises(ValueError, match="checkpoint limit"):
        context_check(agent(), "word " * 50, Q)


def test_option_and_instruction_truncation():
    q = {"q": {**Q["q"], "criteria": {"test": "word " * 60, "app": "code"}}}
    with pytest.raises(ValueError, match="criteria would be truncated"):
        context_check(agent(), "short", q)
    with pytest.raises(ValueError, match="criteria would be truncated"):
        context_check(agent(), "short", {"q": {**Q["q"], "instructions": "word " * 100}})


@pytest.mark.parametrize("question", [
    {"type": "unknown", "instructions": "x"},
    {"type": "choice", "instructions": "x", "criteria": ["a", "a"]},
    {"type": "score", "instructions": "x", "criteria": {"a": "b", "c": "d"}},
    {"type": "noul", "instructions": "x", "criteria": {"maybe": "yes"}},
    {"type": "noul", "instructions": ""},
])
def test_bad_schemas(question):
    with pytest.raises(ValueError):
        request_check("x", {"q": question}, Config())


def test_nonfinite_and_bytes():
    with pytest.raises(ValueError):
        request_check({"value": float("nan")}, Q, Config())
    with pytest.raises(ValueError, match="bytes"):
        request_check("x" * 2000, Q, Config(max_request_bytes=1024))
