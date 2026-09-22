import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path

MODELS = json.loads(Path(__file__).with_name("models.json").read_text(encoding="utf-8"))
PATTERNS = ["model.safetensors", "rl_agent_config.json", "tokenizer/*", "encoder/config.json"]


def model_path(root, name):
    return root / "checkpoints" / name / MODELS[name]["revision"]


def ready(root, name):
    path = model_path(root, name)
    required = ["model.safetensors", "rl_agent_config.json", "tokenizer/tokenizer_config.json", "encoder/config.json", "prepared.json"]
    if not all((path / f).is_file() for f in required):
        return False
    try:
        receipt = json.loads((path / "prepared.json").read_text(encoding="utf-8"))
        return receipt["revision"] == MODELS[name]["revision"]
    except (ValueError, KeyError):
        return False


def prepare(root, name, source_cache=None):
    """Only setup may fetch weights; copy out of HF cache before tokenizer repairs."""
    from huggingface_hub import snapshot_download

    names = list(MODELS) if name == "all" else [name]
    result = {}
    for key in names:
        if key not in MODELS:
            raise ValueError(f"Unknown checkpoint {key}")
        destination = model_path(root, key)
        if not ready(root, key):
            spec = MODELS[key]
            cached = Path(snapshot_download(repo_id=spec["repo"], revision=spec["revision"],
                                            cache_dir=source_cache or root / "downloads",
                                            local_files_only=source_cache is not None,
                                            allow_patterns=PATTERNS if source_cache else PATTERNS[1:]))
            shutil.copytree(cached, destination, dirs_exist_ok=True)
            weights = destination / "model.safetensors"
            if not weights.exists():
                if source_cache:
                    raise FileNotFoundError(f"The supplied cache lacks {key} weights")
                download_weights(spec, weights)
            with weights.open("rb") as stream:
                actual = hashlib.file_digest(stream, "sha256").hexdigest()
            if actual != spec["weight_sha256"]:
                raise ValueError(f"Checkpoint {key} failed its pinned weight checksum")
            from laya.agent import _fix_tokenizer_config
            _fix_tokenizer_config(str(destination))
            hashes = {}
            for path in sorted(destination.rglob("*")):
                if path.is_file() and path.name != "prepared.json":
                    with path.open("rb") as stream:
                        hashes[path.relative_to(destination).as_posix()] = hashlib.file_digest(stream, "sha256").hexdigest()
            (destination / "prepared.json").write_text(json.dumps({**spec, "sha256": hashes}, indent=2), encoding="utf-8")
        if not ready(root, key):
            raise RuntimeError(f"Incomplete checkpoint {key}; setup cannot continue")
        result[key] = str(destination)
    return result


def download_weights(spec, destination):
    """Bounded HTTPS stream avoids platform-dependent Xet downloader stalls."""
    import httpx

    url = f"https://huggingface.co/{spec['repo']}/resolve/{spec['revision']}/model.safetensors?download=true"
    temporary = destination.with_suffix(".part")
    last_progress = time.monotonic()
    with httpx.Client(follow_redirects=True, timeout=httpx.Timeout(60, connect=20)) as client:
        with client.stream("GET", url) as response:
            response.raise_for_status()
            checksum, count = hashlib.sha256(), 0
            with temporary.open("wb") as stream:
                for chunk in response.iter_bytes(1024 * 1024):
                    stream.write(chunk)
                    checksum.update(chunk)
                    count += len(chunk)
                    if time.monotonic() - last_progress >= 20:
                        print(f"Preparing {spec['repo']}: {count / 2**20:.0f} MiB downloaded", file=sys.stderr)
                        last_progress = time.monotonic()
            if checksum.hexdigest() != spec["weight_sha256"]:
                raise ValueError("Downloaded weight checksum does not match the pinned model")
    os.replace(temporary, destination)
