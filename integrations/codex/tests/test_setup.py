import importlib.util
import json
from pathlib import Path
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
