import sys
from types import SimpleNamespace

import pytest

from laya_codex_companion.backend import Backend
from laya_codex_companion.config import Config


def make_backend(tmp_path, monkeypatch, device, available, memory=10):
    events = []

    class Router:
        def __init__(self, **kwargs):
            self.device = kwargs["device"]
            self.loaded = []
            assert not kwargs["auto_task_detection"]

        def unload(self):
            events.append("unload")
            self.loaded = []

        def load(self, name):
            events.append("load:" + name)
            self.loaded = [name]
            return SimpleNamespace(device=self.device)

    torch = SimpleNamespace(set_num_threads=lambda n: None,
                            cuda=SimpleNamespace(is_available=lambda: available, mem_get_info=lambda: (memory * 2**30, 12 * 2**30), empty_cache=lambda: None),
                            backends=SimpleNamespace(mps=SimpleNamespace(is_available=lambda: False)))
    monkeypatch.setitem(sys.modules, "torch", torch)
    monkeypatch.setitem(sys.modules, "laya", SimpleNamespace(Router=Router))
    monkeypatch.setattr("laya_codex_companion.backend.ready", lambda *args: True)
    backend = Backend(tmp_path, Config(device=device))
    return backend, events


def test_cuda_memory_fallback(tmp_path, monkeypatch):
    backend, _ = make_backend(tmp_path, monkeypatch, "cuda", True, memory=1)
    assert backend.load("multilingual").device == "cpu"
    assert backend.fallback_reason == "Insufficient free CUDA memory"


def test_unload_before_model_switch(tmp_path, monkeypatch):
    backend, events = make_backend(tmp_path, monkeypatch, "cpu", False)
    backend.load("multilingual")
    backend.load("english")
    assert events == ["unload", "load:multilingual", "unload", "load:english"]


def test_missing_weights_never_call_loader(tmp_path, monkeypatch):
    backend, events = make_backend(tmp_path, monkeypatch, "cpu", False)
    monkeypatch.setattr("laya_codex_companion.backend.ready", lambda *args: False)
    with pytest.raises(FileNotFoundError, match="prepare"):
        backend.load("english")
    assert events == []
