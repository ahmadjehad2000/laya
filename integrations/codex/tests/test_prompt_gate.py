import io
import json
import subprocess
from types import SimpleNamespace
import pytest
from laya_codex_companion import prompt_gate


@pytest.mark.parametrize("model", sorted(prompt_gate.MODELS))
def test_gate_requires_correlated_real_decision(model, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-secret-not-for-laya")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "another-test-secret")
    def run(args, **kwargs):
        assert "OPENAI_API_KEY" not in kwargs["env"]
        assert "ANTHROPIC_API_KEY" not in kwargs["env"]
        request = json.loads(kwargs["input"])
        assert request["model"] in ("gpt-6-astra", "gpt-6-sol")
        assert request["evidence"]["requests"] == ["Fix tests; do not deploy"]
        return SimpleNamespace(returncode=0, stdout=json.dumps({**request, "status": "decided", "effort": "high", "milestone": {"choices": {"approach": "inspect", "verification": "focused", "context": "retain"}}}))
    assert prompt_gate.evaluate({"model": model, "prompt": "Fix tests; do not deploy"}, run)["effort"] == "high"


@pytest.mark.parametrize("failure", ["worker", "timeout", "malformed", "wrong_id", "fallback"])
def test_gate_rejects_missing_or_invalid_inference(failure):
    def run(*args, **kwargs):
        if failure == "timeout":
            raise subprocess.TimeoutExpired("worker", 110)
        request = json.loads(kwargs["input"])
        return SimpleNamespace(returncode=1 if failure == "worker" else 0,
            stdout="not json" if failure == "malformed" else json.dumps({**request,
            "id": "wrong" if failure == "wrong_id" else request["id"],
            "status": "fallback" if failure == "fallback" else "decided", "effort": "low"}))
    with pytest.raises((ValueError, RuntimeError, subprocess.TimeoutExpired)):
        prompt_gate.evaluate({"model": "gpt-6-sol", "prompt": "Fix tests"}, run)


def test_hook_blocks_worker_failure_without_persisting_prompt(monkeypatch, tmp_path, capsys):
    monkeypatch.delenv("LAYA_NATIVE_CONTROLLER", raising=False)
    monkeypatch.setattr(prompt_gate, "home", lambda: tmp_path)
    monkeypatch.setattr(prompt_gate.sys, "stdin", SimpleNamespace(buffer=io.BytesIO(b'{"model":"gpt-6-sol","prompt":"private task"}')))
    def fail(*args):
        raise RuntimeError("worker unavailable")
    monkeypatch.setattr(prompt_gate, "evaluate", fail)
    assert prompt_gate.main() == 0
    assert json.loads(capsys.readouterr().out)["decision"] == "block"
    records = list((tmp_path / "hook-audit").glob("*.json"))
    assert records and "private task" not in records[0].read_text()
    assert json.loads(records[0].read_text())["admitted"] is False


def test_gate_blocks_old_worker_without_milestone_choices():
    def run(*args, **kwargs):
        request = json.loads(kwargs["input"])
        return SimpleNamespace(returncode=0, stdout=json.dumps({**request, "status": "decided", "effort": "low"}))
    with pytest.raises(RuntimeError, match="milestone"):
        prompt_gate.evaluate({"model": "gpt-6-sol", "prompt": "Verify source"}, run)
