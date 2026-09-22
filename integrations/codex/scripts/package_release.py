"""Build a source ZIP and checksums from tracked files, excluding local runtime data."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import tomllib
import zipfile

root = Path(__file__).resolve().parents[3]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, default=root / "dist")
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
version = tomllib.loads((root / "integrations/codex/pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
archive = args.output / f"laya-for-codex-{version}-preview.zip"
files = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")
with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
    for name in files:
        if name:
            bundle.write(root / name, "laya-for-codex/" + name)
portable = args.output / f"laya-for-codex-{version}-portable.zip"
plugin = root / "integrations/codex/plugins/laya-for-codex"
with zipfile.ZipFile(portable, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
    for path in plugin.rglob("*"):
        if path.is_file():
            name = path.relative_to(plugin).as_posix()
            bundle.write(path, "plugin.json" if name == "plugin.portable.json" else name)
checksums = []
for artifact in (archive, portable):
    with artifact.open("rb") as stream:
        checksum = hashlib.file_digest(stream, "sha256").hexdigest()
    checksums.append(f"{checksum}  {artifact.name}")
(args.output / "SHA256SUMS.txt").write_text("\n".join(checksums) + "\n", encoding="utf-8")
print(archive)
