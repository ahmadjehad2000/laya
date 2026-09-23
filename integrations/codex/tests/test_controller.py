import json
import sys
from types import SimpleNamespace

import pytest

from laya_codex_companion import cli
from laya_codex_companion.controller import decide
from laya_codex_companion.compaction import compact_file, read_messages


def request(**changes):
    return {"protocol": 1, "id": "turn:1", "generation": 1, "model": "gpt-6-astra",
            "supported_efforts": ["low", "medium", "high"],
            "evidence": {"requests": ["Fix the failing test. Do not deploy."], "recent": []}, **changes}


@pytest.mark.parametrize("args, expected", [
    (["exec", "-mgpt-5.6-sol", "hello"], True),
    (["exec", "--model=gpt-6-astra", "hello"], True),
    (["exec", "-m", "gpt-6-astra", "hello"], True),
    (["exec", "--", "--model=quoted-prompt"], False),
    (["exec", "hello"], False),
])
def test_native_model_option_forms(args, expected):
    from laya_codex_companion.native import has_model_option
    assert has_model_option(args) is expected


def test_continue_automatically_archives_explicit_export(monkeypatch, tmp_path, capsys):
    import subprocess
    import shutil
    from pathlib import Path
    messages = [{"role": "user", "content": "Never deploy; budget 250 MiB"},
                {"role": "tool", "content": "inventory " * 5000},
                {"role": "user", "content": "Tests remain unresolved"}]
    (tmp_path / "chat.json").write_text(json.dumps(messages), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["laya-for-codex", "continue", "--workspace", str(tmp_path),
                                     "--input", "chat.json", "--keep-recent", "1", "--prompt", "Report status"])
    monkeypatch.setattr(shutil, "which", lambda name: "codex")
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda args, **kw: calls.append((args, kw)) or SimpleNamespace(returncode=0))
    assert cli.main() == 0
    prompt = calls[0][1]["input"]
    assert "Never deploy; budget 250 MiB" in prompt and "Tests remain unresolved" in prompt
    assert len(prompt) < 5000
    report = json.loads(capsys.readouterr().err)["automatic_handoff"]
    from laya_codex_companion.compaction import recall
    assert recall(tmp_path, report["archive"], 1) == messages[1]
    assert Path(report["context"]).is_file()


def test_auto_handoff_invalid_export_never_launches_cloud(monkeypatch, tmp_path):
    import subprocess
    (tmp_path / "bad.json").write_text("not json", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["laya-for-codex", "continue", "--workspace", str(tmp_path),
                                     "--input", "bad.json", "--prompt", "Report status"])
    def fail(*args, **kwargs):
        pytest.fail("Invalid export must not launch Codex")
    monkeypatch.setattr(subprocess, "run", fail)
    assert cli.main() == 1


class Runtime:
    def __init__(self):
        self.states = []

    def predict(self, state, questions, **options):
        assert options["use_cache"] is True
        self.states.append(json.loads(json.dumps(state)))
        if state["recent"]:
            raise ValueError("needs 1200 tokens, checkpoint limit 1024")
        return {"answers": {"effort": {"choice": "high", "probabilities": {"high": 0.8}},
                            "duration": {"choice": "1"}}, "runtime": {"device": "cuda"},
                "checkpoint": {"variant": "multilingual"}, "context_tokens": {"effort": 90}}


@pytest.mark.parametrize("model", ["gpt-6-astra", "gpt-6-sol"])
def test_controller_preserves_constraints_when_optional_context_does_not_fit(model):
    runtime = Runtime()
    req = request(model=model, evidence={"requests": ["Fix tests; never deploy."], "recent": ["large output"]})
    result = decide(runtime, req)
    assert result["status"] == "decided"
    assert result["coverage"] == {"requests": 1, "recent_items": 0, "omitted_items": 1}
    assert all(s["requests"] == ["Fix tests; never deploy."] for s in runtime.states)
    assert result["runtime"] == {"device": "cuda"}


@pytest.mark.parametrize("changes", [
    {"model": "different"}, {"protocol": 2}, {"supported_efforts": ["high"]},
    {"supported_efforts": ["high", "invented"]},
    {"evidence": {"requests": ["omitted goal"], "incomplete_requests": True}},
    {"evidence": {"requests": ["   "]}},
])
def test_controller_abstains_before_inference_on_invalid_capabilities_or_evidence(changes):
    runtime = Runtime()
    result = decide(runtime, request(**changes))
    assert result["status"] == "fallback" and "effort" not in result
    assert runtime.states == []


def test_essential_context_overflow_is_never_silently_shortened():
    class Oversized(Runtime):
        def predict(self, state, questions, **kwargs):
            raise ValueError("needs 4000 tokens, checkpoint limit 1024")
    result = decide(Oversized(), request())
    assert result["status"] == "fallback" and "checkpoint limit" in result["reason"]


def test_dependency_import_failure_returns_a_typed_abstention():
    class Broken(Runtime):
        def predict(self, *args, **kwargs):
            raise AssertionError("dependency initialization failed")
    result = decide(Broken(), request())
    assert result["status"] == "fallback"
    assert "AssertionError" in result["reason"]


def test_serve_keyboard_interrupt_is_quiet_and_130(monkeypatch, capsys):
    def interrupt():
        raise KeyboardInterrupt
    monkeypatch.setattr("laya_codex_companion.server.serve", interrupt)
    monkeypatch.setattr(sys, "argv", ["laya-for-codex", "serve"])
    assert cli.main() == 130
    assert capsys.readouterr().err == "Interrupted.\n"


@pytest.mark.parametrize("context", [[], [""], ["   "]])
def test_missing_or_empty_context_explains_powershell_recovery(monkeypatch, capsys, context):
    monkeypatch.setattr(sys, "argv", ["laya-for-codex", "continue", "--workspace", ".",
                                     "--context", *context, "--prompt", "Continue"])
    with pytest.raises(SystemExit) as error:
        cli.main()
    assert error.value.code == 2
    assert "Create a handoff first" in capsys.readouterr().err


def test_handoff_keeps_constraints_and_controller_provenance_without_a_lease(tmp_path):
    messages = [{"role": "user", "content": "Branch feature/test; memory 6 GiB; do not deploy; tests unresolved."}]
    (tmp_path / "chat.json").write_text(json.dumps(messages), encoding="utf-8")
    log = {"decision": {"status": "decided", "generation": 2, "lease": 2,
                        "checkpoint": {"variant": "multilingual"}, "evidence_sha256": "abc"},
           "actual_effort": "high", "applied": True}
    (tmp_path / "decisions.jsonl").write_text(json.dumps(log) + "\n", encoding="utf-8")
    result = compact_file(tmp_path, "chat.json", controller_log="decisions.jsonl")
    from pathlib import Path
    context = json.loads(Path(result["context"]).read_text(encoding="utf-8"))
    assert context["messages"] == messages
    metadata = context["controller_history"]
    assert metadata["active_lease"] is None
    assert "lease" not in metadata["recent"][0]
    assert metadata["recent"][0]["actual_effort"] == "high"
    assert Path(metadata["archive"]).is_file()


def test_native_rollout_configuration_updates_do_not_become_instructions():
    entries = [{"type": "response_item", "payload": {"type": "configuration_update", "reasoning": {"effort": "high"}}},
               {"type": "response_item", "payload": {"type": "message", "role": "user", "content": "No deployment"}}]
    assert read_messages("\n".join(map(json.dumps, entries)).encode()) == [{"role": "user", "content": "No deployment"}]


def test_native_launcher_keeps_explicit_model_and_sets_private_worker(monkeypatch, tmp_path):
    from laya_codex_companion import native
    import os
    binary = tmp_path / "native/bin" / ("codex.exe" if os.name == "nt" else "codex")
    binary.parent.mkdir(parents=True)
    binary.touch()
    monkeypatch.setattr(native, "home", lambda: tmp_path)
    monkeypatch.setattr(sys, "argv", ["laya-codex", "exec", "-m", "gpt-5.6-sol", "hello"])
    calls = []
    monkeypatch.setattr(native.subprocess, "run", lambda args, **kwargs: calls.append((args, kwargs)) or SimpleNamespace(returncode=0))
    assert native.main() == 0
    args, options = calls[0]
    assert "laya-astra" not in args and "gpt-5.6-sol" in args
    assert options["env"]["LAYA_CONTROLLER_PYTHON"] == sys.executable
    assert "LAYA_CONTROLLER_LOG_DIR" in options["env"]
