import json

import pytest

from laya_codex_companion.compaction import compact_file, read_messages, recall
from laya_codex_companion.config import Config
from laya_codex_companion.offload import classify_file


def test_handoff_preserves_instructions_errors_recent_and_exact_recovery(tmp_path):
    messages = [{"role": role, "content": "must keep " * 400} for role in
                ("system", "developer", "user", "assistant")]
    messages += [{"role": "tool", "content": "data row\n" * 2000},
                 {"role": "tool", "content": "FAILED important\n" * 400},
                 {"role": "tool", "content": "recent\n" * 400}]
    source = tmp_path / "chat.json"
    source.write_text(json.dumps(messages), encoding="utf-8")
    result = compact_file(str(tmp_path), "chat.json", keep_recent=1)
    context = json.loads(__import__("pathlib").Path(result["context"]).read_text(encoding="utf-8"))
    assert result["archived_indices"] == [4]
    assert context["messages"][:4] == messages[:4]
    assert context["messages"][5:] == messages[5:]
    assert recall(str(tmp_path), result["archive"], 4) == messages[4]
    assert result["cloud_model_calls"] == 0 and not result["native_compaction_replaced"]
    assert compact_file(str(tmp_path), "chat.json", keep_recent=1) == result


def test_recall_rejects_tampering(tmp_path):
    (tmp_path / "x.json").write_text('[{"role":"user","content":"hello"}]')
    result = compact_file(str(tmp_path), "x.json")
    from pathlib import Path
    Path(result["archive"]).write_text("[]")
    with pytest.raises(ValueError, match="hash mismatch"):
        recall(str(tmp_path), result["archive"], 0)


def test_workspace_escape_and_invalid_parameters(tmp_path):
    from laya_codex_companion.local_files import workspace_file
    child = tmp_path / "child"
    child.mkdir()
    (tmp_path / "outside").write_text("private")
    with pytest.raises(ValueError, match="inside"):
        workspace_file(str(child), "../outside")
    with pytest.raises(ValueError, match="keep_recent"):
        compact_file(str(child), "anything", keep_recent=-1)


def test_rollout_parser_no_duplicate_event_messages_and_rejects_opaque_context():
    entries = [{"type": "event_msg", "payload": {"type": "user_message", "message": "duplicate"}},
               {"type": "response_item", "payload": {"type": "message", "role": "user", "content": "original"}}]
    assert read_messages("\n".join(map(json.dumps, entries)).encode()) == [{"role": "user", "content": "original"}]
    with pytest.raises(ValueError, match="Already compacted"):
        read_messages(b'{"type":"compacted","payload":{}}')
    with pytest.raises(ValueError, match="Unsupported"):
        read_messages(b'{"type":"response_item","payload":{"type":"image"}}')


class FakeRuntime:
    config = Config(max_items=2)

    def predict_batch(self, items, questions, model=None):
        return {"items": [{"id": item["id"], "result": {
            "runtime": {"device": "cpu"}, "answers": {"topic": {"choice": "a",
                "probabilities": {"a": item["state"], "b": 1 - item["state"]}}}}} for item in items]}


def test_file_offload_flags_uncertainty_and_writes_full_result(tmp_path):
    from pathlib import Path
    items = [{"id": str(i), "state": confidence} for i, confidence in enumerate([0.99, 0.6, 0.98])]
    (tmp_path / "records.json").write_text(json.dumps(items))
    questions = {"topic": {"type": "choice", "instructions": "Select topic", "criteria": ["a", "b"]}}
    result = classify_file(FakeRuntime(), str(tmp_path), "records.json", questions)
    assert result["needs_review"] == 1 and result["review_ids_preview"] == ["1"]
    assert result["records"] == 3 and result["cloud_model_calls_by_laya"] == 0
    assert result["failed"] == 0 and result["succeeded"] == 3
    artifact = json.loads(Path(result["artifact"]).read_text())
    assert len(artifact["items"]) == 3
    assert [item["needs_review"] for item in artifact["items"]] == [False, True, False]
    with pytest.raises(ValueError, match="finite"):
        classify_file(FakeRuntime(), str(tmp_path), "records.json", questions, min_probability=float("nan"))
    (tmp_path / "records.json").write_text(json.dumps([items[0], items[0]]))
    with pytest.raises(ValueError, match="unique"):
        classify_file(FakeRuntime(), str(tmp_path), "records.json", questions)


def test_file_offload_oversized_record_keeps_other_results(tmp_path):
    items = [{"id": "too-large", "state": "word " * 30000}, {"id": "good", "state": 0.99}]
    (tmp_path / "records.json").write_text(json.dumps(items))
    questions = {"topic": {"type": "choice", "instructions": "Select topic", "criteria": ["a", "b"]}}
    result = classify_file(FakeRuntime(), str(tmp_path), "records.json", questions)
    assert result["failed"] == 1 and result["succeeded"] == 1
    assert result["review_ids_preview"] == ["too-large"]


def test_continue_lean_uses_new_readonly_thread_and_explicit_model(tmp_path, monkeypatch):
    import shutil
    import subprocess
    import sys
    from types import SimpleNamespace
    from laya_codex_companion.cli import main
    (tmp_path / "chat.json").write_text('[{"role":"user","content":"Do not deploy"}]')
    result = compact_file(str(tmp_path), "chat.json")
    argv = ["laya-for-codex", "continue", "--workspace", str(tmp_path), "--context", result["context"],
            "--prompt", "Review tests", "--lean", "--target", "codex"]
    monkeypatch.setattr(shutil, "which", lambda name: "codex")
    monkeypatch.setattr(sys, "argv", argv)
    assert main() == 1
    calls = []
    def run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setattr(sys, "argv", argv + ["--model", "example-model"])
    assert main() == 0
    command, kwargs = calls[0]
    assert "--ignore-user-config" in command and "read-only" in command and "example-model" in command
    assert "resume" not in command and "Do not deploy" in kwargs["input"]
    assert "Review tests" in kwargs["input"] and "subject to current instructions" in kwargs["input"]
