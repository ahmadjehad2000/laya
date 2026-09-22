"""Bounded workspace files; no implicit network reads or arbitrary output paths."""
import hashlib
import json
from pathlib import Path


def workspace_file(workspace, filename, limit=16 * 1024 * 1024):
    root = Path(workspace).resolve(strict=True)
    path = (root / filename).resolve(strict=True)
    if not root.is_dir() or not path.is_relative_to(root) or not path.is_file():
        raise ValueError("Input must be a regular file inside the explicit workspace")
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError(f"Input exceeds {limit} bytes")
    return root, path, raw


def artifact_dir(root, kind):
    target = root / ".laya" / kind
    if not target.resolve().is_relative_to(root):
        raise ValueError("Artifact directory resolves outside workspace")
    target.mkdir(parents=True, exist_ok=True)
    return target


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")


def write_new(path, raw):
    # Never overwrite user files or follow an existing output symlink.
    try:
        with path.open("xb") as stream:
            stream.write(raw)
    except FileExistsError:
        if path.is_symlink() or path.read_bytes() != raw:
            raise ValueError(f"Existing artifact does not match: {path}")
