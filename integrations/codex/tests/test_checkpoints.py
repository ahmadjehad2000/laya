import hashlib

import httpx
import pytest

from laya_codex_companion.checkpoints import download_weights, ready


def test_download_verifies_hash_before_publishing(tmp_path, monkeypatch):
    payload = b"fake test fixture, not real model weights"
    original_client = httpx.Client
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=payload))
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: original_client(transport=transport, **kwargs))
    spec = {"repo": "example/test", "revision": "pinned", "weight_sha256": hashlib.sha256(payload).hexdigest()}
    destination = tmp_path / "model.safetensors"
    download_weights(spec, destination)
    assert destination.read_bytes() == payload
    assert not destination.with_suffix(".part").exists()


def test_bad_download_never_becomes_ready(tmp_path, monkeypatch):
    original_client = httpx.Client
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=b"corrupt"))
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: original_client(transport=transport, **kwargs))
    destination = tmp_path / "model.safetensors"
    with pytest.raises(ValueError, match="checksum"):
        download_weights({"repo": "example/test", "revision": "pinned", "weight_sha256": "0" * 64}, destination)
    assert not destination.exists()
    assert not ready(tmp_path, "multilingual")
