import time
from types import SimpleNamespace

import pytest

from laya_codex_companion.config import Config
from laya_codex_companion.runtime import Runtime

QUESTIONS = {"role": {"type": "choice", "instructions": "What role?", "criteria": ["test", "application"]}}


class FakeBackend:
    def __init__(self, root, config):
        self.router = SimpleNamespace(loaded=[])
        self.fallback_reason = None
        self.predictions = 0

    def route(self, state, questions, model):
        return {"model": "multilingual" if model == "auto" else model, "reason": "fixture"}

    def load(self, name):
        self.router.loaded = [name]
        return SimpleNamespace(device="cpu")

    def check(self, agent, state, questions):
        if state == "too long":
            raise ValueError("Would truncate")
        return {key: 20 for key in questions}

    def predict(self, agent, state, questions):
        self.predictions += 1
        if state == "oom":
            raise MemoryError("memory")
        return {"answers": {key: {"choice": list(q["criteria"])[0]} for key, q in questions.items()},
                "usage": {"input_tokens": 20}}

    def release(self):
        self.router.loaded = []


@pytest.fixture
def runtime(tmp_path):
    instance = Runtime(tmp_path, Config(min_free_ram_gib=0.5), FakeBackend)
    yield instance
    instance.close()


def test_cache_isolated_by_model_option_order_and_mutation(runtime):
    first = runtime.predict("evidence", QUESTIONS)
    first["answers"]["role"]["choice"] = "changed externally"
    cached = runtime.predict("evidence", QUESTIONS)
    assert cached["answers"]["role"]["choice"] == "test"
    assert cached["runtime"]["cache_hit"] is True
    assert cached["runtime"]["inference_ms"] == 0
    assert runtime.predict("evidence", QUESTIONS, model="english")["runtime"]["cache_hit"] is False
    reverse = {"role": {**QUESTIONS["role"], "criteria": ["application", "test"]}}
    assert runtime.predict("evidence", reverse)["answers"]["role"]["choice"] == "application"


def test_batch_retains_order_and_partial_errors(runtime):
    result = runtime.predict_batch([{"id": "a", "state": "fine"}, {"id": "b", "state": "too long"},
                                    {"id": "c", "state": "other"}], QUESTIONS)
    assert [r["id"] for r in result["items"]] == ["a", "b", "c"]
    assert result["succeeded"] == 2 and result["failed"] == 1
    assert result["items"][1]["error"]["type"] == "ValueError"


def test_duplicate_ids_rejected_before_inference(runtime):
    with pytest.raises(ValueError, match="unique"):
        runtime.predict_batch([{"id": "a", "state": "x"}] * 2, QUESTIONS)
    assert runtime.backend is None


def test_release_and_reload(runtime):
    runtime.predict("fine", QUESTIONS)
    runtime.release()
    assert runtime.status()["loaded"] == []
    assert runtime.status()["cache_entries"] == 0
    assert not runtime.predict("fine", QUESTIONS)["runtime"]["cache_hit"]


def test_memory_failure_returns_no_partial_answer(runtime):
    with pytest.raises(MemoryError):
        runtime.predict("oom", QUESTIONS)
    assert runtime.status()["loaded"] == []
    assert runtime.errors == 1


def test_expired_cache(runtime):
    runtime.predict("fine", QUESTIONS)
    key = next(iter(runtime.cache))
    _, result = runtime.cache[key]
    runtime.cache[key] = (time.monotonic() - 1000, result)
    assert not runtime.predict("fine", QUESTIONS)["runtime"]["cache_hit"]


def test_idle_release(runtime):
    from dataclasses import replace
    instance = Runtime(runtime.root, replace(runtime.config, idle_unload_sec=1), FakeBackend)
    try:
        instance.predict("fine", QUESTIONS)
        assert not instance._expire_idle(instance.last_use + .5)
        assert instance._expire_idle(instance.last_use + 1)
        assert instance.status()["loaded"] == []
        assert instance.status()["cache_entries"] == 0
        assert not instance._expire_idle(instance.last_use + 5)
    finally:
        instance.close()


def test_question_batches_and_cache_bound(tmp_path):
    instance = Runtime(tmp_path, Config(question_batch_size=1, cache_entries=1, min_free_ram_gib=0.5), FakeBackend)
    try:
        questions = {"one": QUESTIONS["role"], "two": QUESTIONS["role"]}
        result = instance.predict("a", questions)
        assert set(result["answers"]) == {"one", "two"}
        assert instance.backend.predictions == 2
        instance.predict("b", QUESTIONS)
        assert len(instance.cache) == 1
        assert not instance.predict("a", questions)["runtime"]["cache_hit"]
    finally:
        instance.close()


def test_bad_state_in_batch_does_not_drop_other_items(runtime):
    result = runtime.predict_batch([{"id": "a", "state": 123}, {"id": "b", "state": "fine"}], QUESTIONS)
    assert result["failed"] == result["succeeded"] == 1


def test_status_does_not_create_backend(runtime):
    assert runtime.status()["device"] is None
    assert runtime.backend is None
