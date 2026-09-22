import importlib.util
import json
from pathlib import Path
import sys
import tomllib

import pytest

spec = importlib.util.spec_from_file_location("bootstrap", Path(__file__).parents[1] / "bootstrap.py")
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


def test_direct_registration_migration_and_repeat(tmp_path):
    root, codex = tmp_path / "runtime", tmp_path / "codex"
    codex.mkdir()
    config = codex / "config.toml"
    original = 'model = "unchanged"\n[mcp_servers.other]\ncommand = "other"\n' + bootstrap.OLD_BEGIN + '\n[mcp_servers.laya]\ncommand = "old"\n' + bootstrap.OLD_END + '\n'
    config.write_text(original, encoding="utf-8")
    with pytest.raises(RuntimeError, match="Existing Laya"):
        bootstrap.register(root, codex, "direct", False)
    assert config.read_text() == original
    bootstrap.register(root, codex, "direct", True)
    parsed = tomllib.loads(config.read_text())
    assert parsed["model"] == "unchanged"
    assert parsed["mcp_servers"]["other"]["command"] == "other"
    assert "laya" not in parsed["mcp_servers"]
    assert parsed["mcp_servers"]["laya-for-codex"]["command"] == str(bootstrap.python_at(root))
    once = config.read_bytes()
    bootstrap.register(root, codex, "direct", True)
    assert config.read_bytes() == once
    receipt = json.loads((root / "rollback.json").read_text())
    assert Path(receipt["backup"]).read_text() == original


def test_uninstall_preserves_unrelated_text(tmp_path):
    source = '# user comment\nmodel = "example"\n' + bootstrap.direct_block(tmp_path)
    result = bootstrap.replace_block(source, bootstrap.BEGIN, bootstrap.END)
    assert 'model = "example"' in result
    assert "mcp_servers" not in result


def test_managed_windows_commands_are_direct_and_collision_safe(tmp_path):
    root = tmp_path / "runtime"
    scripts = root / "venv" / "Scripts"
    scripts.mkdir(parents=True)
    for name in ("laya-codex", "laya-for-codex"):
        (scripts / f"{name}.exe").write_bytes(b"stub")
    destination = tmp_path / "commands"
    launchers = bootstrap.install_commands(root, destination, windows=True)
    assert [path.name for path in launchers] == ["laya-codex.cmd", "laya-for-codex.cmd"]
    assert str(scripts / "laya-codex.exe") in launchers[0].read_text()
    assert bootstrap.COMMAND_MARKER in launchers[0].read_text()
    launchers[0].write_text("unmanaged", encoding="utf-8")
    with pytest.raises(RuntimeError, match="unmanaged command"):
        bootstrap.install_commands(root, destination, windows=True)


def test_remove_commands_preserves_unmanaged_files(tmp_path):
    managed = tmp_path / "laya-codex.cmd"
    unmanaged = tmp_path / "laya-for-codex.cmd"
    managed.write_text(bootstrap.COMMAND_MARKER, encoding="utf-8")
    unmanaged.write_text("user command", encoding="utf-8")
    bootstrap.remove_commands(tmp_path, windows=True)
    assert not managed.exists()
    assert unmanaged.read_text() == "user command"


def test_unmanaged_registration_not_overwritten(tmp_path):
    (tmp_path / "config.toml").write_text('[mcp_servers.laya-for-codex]\ncommand = "custom"\n')
    with pytest.raises(RuntimeError, match="unmanaged"):
        bootstrap.register(tmp_path / "runtime", tmp_path, "direct", False)


def test_failed_plugin_registration_restores_configuration(tmp_path, monkeypatch):
    config = tmp_path / "config.toml"
    original = b'model = "original"\n'
    config.write_bytes(original)

    def fail(root, codex_home):
        config.write_text('model = "partially changed"\n')
        raise RuntimeError("Plugin installation failed")

    monkeypatch.setattr(bootstrap, "install_plugin", fail)
    with pytest.raises(RuntimeError, match="installation failed"):
        bootstrap.register(tmp_path / "runtime", tmp_path, "plugin", False)
    assert config.read_bytes() == original


def test_direct_mode_refuses_duplicate_plugin(tmp_path):
    (tmp_path / "config.toml").write_text('[plugins."laya-for-codex@laya-companion"]\nenabled = true\n')
    with pytest.raises(RuntimeError, match="plugin is enabled"):
        bootstrap.register(tmp_path / "runtime", tmp_path, "direct", False)


def test_cuda_setup_uses_disk_temp_and_requires_actual_gpu(tmp_path, monkeypatch):
    root = tmp_path / "runtime"
    python = bootstrap.python_at(root)
    python.parent.mkdir(parents=True)
    python.write_text("stub")
    calls = []
    monkeypatch.setenv("TMPDIR", "/tmp")
    monkeypatch.delenv("LAYA_COMPANION_DEVICE", raising=False)
    monkeypatch.setattr(bootstrap, "run", lambda args, **kwargs: calls.append((args, kwargs)))
    command_installs = []
    fake_launcher = tmp_path / "commands" / "laya-codex.cmd"
    monkeypatch.setattr(bootstrap, "install_commands",
                        lambda path: command_installs.append(path) or [fake_launcher])
    monkeypatch.setattr(sys, "argv", ["bootstrap", "install", "--home", str(root), "--mode", "none",
                                      "--torch-index", "cu128", "--device", "cuda"])
    bootstrap.main()
    pip_calls = [(args, kw) for args, kw in calls if "pip" in args]
    assert len(pip_calls) == 4
    for args, kwargs in pip_calls:
        assert kwargs["env"]["TMPDIR"] == str(root / "tmp")
        assert kwargs["env"]["TEMP"] == str(root / "tmp")
    assert calls[-1][0][-2:] == ["--require-device", "cuda"]
    assert command_installs == [root]
    assert bootstrap.os.environ["TMPDIR"] == "/tmp"
