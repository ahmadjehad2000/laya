import json
import os
from types import SimpleNamespace

import pytest

from laya_codex_companion import cli, native


@pytest.mark.parametrize("args, forwarded", [
    ([], []), (["chat"], []), (["chat", "--help"], ["--help"]),
    (["exec", "--json", "-"], ["exec", "--json", "-"]),
    (["resume", "--last"], ["resume", "--last"]),
    (["-C", "some folder"], ["-C", "some folder"]),
    (["Fix tests"], ["Fix tests"]),
    (["--", "doctor"], ["--", "doctor"]),
])
def test_native_dispatch_preserves_arguments_and_exit_code(monkeypatch, args, forwarded):
    seen = []
    monkeypatch.setattr(native, "main", lambda args: seen.append(args) or 17)
    assert cli.main(args) == 17
    assert seen == [forwarded]


def test_default_launch_enables_controller_and_keeps_parent_environment(monkeypatch, tmp_path):
    binary = tmp_path / "native/bin" / ("codex.exe" if os.name == "nt" else "codex")
    binary.parent.mkdir(parents=True)
    binary.touch()
    monkeypatch.setattr(native, "home", lambda: tmp_path)
    calls = []
    before = dict(os.environ)
    monkeypatch.setattr(native.subprocess, "run", lambda args, **kw: calls.append((args, kw)) or SimpleNamespace(returncode=0))
    assert cli.main([]) == 0
    args, options = calls[0]
    assert args[-2:] == ["-m", "laya-astra"]
    assert "step_model_switching" in args and "reasoning_effort_override" in args
    assert options["env"]["LAYA_CONTROLLER_PYTHON"]
    assert dict(os.environ) == before


def test_missing_native_reports_setup_without_launch_or_download(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(native, "home", lambda: tmp_path)
    monkeypatch.setattr(native.subprocess, "run", lambda *a, **kw: pytest.fail("Must not launch stock client"))
    assert cli.main([]) == 1
    assert "native/build.py" in capsys.readouterr().err


def test_default_mcp_configuration_is_valid_toml_and_isolated():
    import sys
    import tomllib
    options = native.integration_options()
    parsed = tomllib.loads("\n".join(options[1::2]))["mcp_servers"]["laya-for-codex"]
    assert parsed["command"] == sys.executable
    assert parsed["args"] == ["-I", "-m", "laya_codex_companion", "serve"]
    assert parsed["enabled"] and parsed["tool_timeout_sec"] == 300
    assert parsed["env"]["HF_HUB_OFFLINE"] == "1"


def test_local_help_and_doctor_do_not_dispatch_native(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(native, "main", lambda *args: pytest.fail("Unexpected native launch"))
    monkeypatch.setenv("LAYA_COMPANION_HOME", str(tmp_path))
    with pytest.raises(SystemExit) as exc:
        cli.main(["--help"])
    assert exc.value.code == 0
    assert "chat --help" in capsys.readouterr().out
    assert cli.main(["doctor"]) == 0
    assert json.loads(capsys.readouterr().out)["device"] is None


def test_native_handoff_is_default_and_lean_needs_no_model(monkeypatch, tmp_path):
    from laya_codex_companion.compaction import compact_file
    (tmp_path / "chat.json").write_text('[{"role":"user","content":"Do not deploy"}]')
    context = compact_file(tmp_path, "chat.json")["context"]
    calls = []
    monkeypatch.setattr("shutil.which", lambda name: name)
    monkeypatch.setattr("subprocess.run", lambda args, **kw: calls.append((args, kw)) or SimpleNamespace(returncode=0))
    assert cli.main(["continue", "--workspace", str(tmp_path), "--context", context,
                     "--lean", "--prompt", "Report status"]) == 0
    args, options = calls[0]
    assert "laya-for-codex" in args[0]
    assert args[1] == "exec" and "--ignore-user-config" in args
    assert "-m" not in args and "Do not deploy" in options["input"]
