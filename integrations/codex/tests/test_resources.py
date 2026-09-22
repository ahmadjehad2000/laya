import json
import struct
from types import SimpleNamespace

import pytest

from laya_codex_companion.checkpoints import model_path
from laya_codex_companion.config import Config
from laya_codex_companion.resources import memory_plan
from laya_codex_companion.runtime import Runtime
from test_runtime import FakeBackend, QUESTIONS


def checkpoint(root, name, elements=100_000_000):
    path = model_path(root, name) / "model.safetensors"
    path.parent.mkdir(parents=True, exist_ok=True)
    header = json.dumps({"weight": {"dtype": "F16", "shape": [elements], "data_offsets": [0, elements * 2]}}).encode()
    # Sparse file avoids allocating test weights in RAM or writing their payload.
    with path.open("wb") as stream:
        stream.write(struct.pack("<Q", len(header)) + header)
        stream.truncate(8 + len(header) + elements * 2)
    return path


@pytest.mark.parametrize("device", ["cpu", "cuda", "mps", "auto"])
@pytest.mark.parametrize("name", ["english", "multilingual", "typed-decisions"])
def test_memory_estimate_supports_every_mode_and_checkpoint(tmp_path, device, name):
    path = checkpoint(tmp_path, name)
    plan = memory_plan(tmp_path, name, Config(device=device))
    expected = path.stat().st_size / 2**30 + 400_000_000 / 2**30 + .75
    assert plan["required_ram_gib"] == pytest.approx(expected)
    assert plan["fp32_parameters_gib"] == pytest.approx(400_000_000 / 2**30)


def test_explicit_memory_floor_is_respected(tmp_path):
    checkpoint(tmp_path, "english")
    assert memory_plan(tmp_path, "english", Config(min_free_ram_gib=4.5))["required_ram_gib"] == 4.5


def test_smaller_checkpoint_runs_below_old_blanket_floor(tmp_path, monkeypatch):
    checkpoint(tmp_path, "multilingual")
    monkeypatch.setattr("laya_codex_companion.runtime.psutil.virtual_memory", lambda: SimpleNamespace(available=2 * 2**30))
    instance = Runtime(tmp_path, Config(), FakeBackend)
    try:
        result = instance.predict("evidence", QUESTIONS)
        assert result["runtime"]["memory_preflight"]["required_ram_gib"] < 2
    finally:
        instance.close()


def test_pressure_is_retryable_and_never_returns_an_answer(tmp_path, monkeypatch):
    checkpoint(tmp_path, "multilingual")
    monkeypatch.setattr("laya_codex_companion.runtime.psutil.virtual_memory", lambda: SimpleNamespace(available=.8 * 2**30))
    instance = Runtime(tmp_path, Config(), FakeBackend)
    try:
        batch = instance.predict_batch([{"id": "asset", "state": "evidence"}], QUESTIONS)
        assert batch["succeeded"] == 0 and batch["failed"] == 1
        error = batch["items"][0]["error"]
        assert error["code"] == "memory_pressure" and error["retryable"]
        assert "No prediction was produced" in error["message"]
        assert instance.backend.predictions == 0
    finally:
        instance.close()


def test_old_model_released_before_switch_memory_check(tmp_path, monkeypatch):
    checkpoint(tmp_path, "english")
    instance = Runtime(tmp_path, Config(), FakeBackend)
    instance.backend = FakeBackend(tmp_path, instance.config)
    instance.backend.router.loaded = ["multilingual"]
    def available():
        return SimpleNamespace(available=(.8 if instance.backend.router.loaded else 2) * 2**30)
    monkeypatch.setattr("laya_codex_companion.runtime.psutil.virtual_memory", available)
    try:
        assert instance.predict("evidence", QUESTIONS, model="english")["runtime"]["memory_preflight"]["available_ram_gib"] == 2
    finally:
        instance.close()


def test_load_failure_releases_partial_backend(tmp_path):
    class Broken(FakeBackend):
        def load(self, name):
            self.router.loaded = [name]
            raise MemoryError("partial load")
    instance = Runtime(tmp_path, Config(min_free_ram_gib=.5), Broken)
    try:
        with pytest.raises(MemoryError):
            instance.predict("evidence", QUESTIONS)
        assert instance.backend.router.loaded == []
    finally:
        instance.close()
