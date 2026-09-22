import json
import sys

import pytest

from laya_codex_companion import cli


@pytest.mark.parametrize("required,actual,cached,expected", [
    ("cuda", "cpu", False, 1), ("cuda", "cuda", False, 0),
    ("mps", "cpu", False, 1), ("cpu", "cpu", False, 0),
    ("cuda", "cuda", True, 0),
])
def test_cli_device_validation_rejects_fallback_and_always_releases(tmp_path, monkeypatch, capsys, required, actual, cached, expected):
    request = tmp_path / "request.json"
    request.write_text(json.dumps({"state": "evidence", "questions": {}}))
    closed = []
    class FakeRuntime:
        def predict(self, **kwargs):
            if cached:
                return {"runtime": {"cache_hit": True}, "original_runtime": {"device": actual}}
            return {"runtime": {"device": actual}}
        def close(self):
            closed.append(True)
    monkeypatch.setattr("laya_codex_companion.runtime.Runtime", FakeRuntime)
    monkeypatch.setattr(sys, "argv", ["laya-for-codex", "predict", str(request), "--require-device", required])
    assert cli.main() == expected
    assert closed == [True]
    output = capsys.readouterr()
    if expected:
        assert "not verified" in json.loads(output.err)["message"]
        assert not output.out
    else:
        assert "runtime" in json.loads(output.out)
