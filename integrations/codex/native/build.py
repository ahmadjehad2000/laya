"""Build a separate pinned native Codex; never replace the stock codex binary."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


def run(args, cwd=None):
    subprocess.run([str(a) for a in args], cwd=cwd, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=REPO / "dist/codex-native-source")
    parser.add_argument("--home", type=Path,
                        default=Path(os.environ.get("LAYA_COMPANION_HOME", Path.home() / ".laya-for-codex")) / "native")
    parser.add_argument("--toolchain", help="Explicit rustup toolchain; otherwise use upstream pin")
    parser.add_argument("--profile", choices=["dev-small", "release"], default="dev-small")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--export-patch", action="store_true", help="Developer: capture reviewed source changes")
    args = parser.parse_args()
    pin = json.loads((HERE / "upstream.json").read_text())
    source = args.source.resolve()
    patch = HERE / "laya-native.patch"
    if args.export_patch:
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()
        if head != pin["commit"]:
            raise ValueError("Patch export requires the pinned upstream commit")
        # Include only these reviewed implementation/tests, never generated local files.
        paths = ["codex-rs/core/src/session/laya_controller.rs",
                 "codex-rs/core/src/session/laya_controller_tests.rs"]
        run(["git", "add", "--intent-to-add", "--", *paths], source)
        paths += ["codex-rs/core/src/session/mod.rs", "codex-rs/core/src/session/turn.rs",
                  "codex-rs/core/src/session/step_activation.rs", "codex-rs/models-manager/src/manager.rs",
                  "codex-rs/core/src/session/step_activation_tests.rs",
                  "codex-rs/models-manager/src/manager_tests.rs", "codex-rs/Cargo.lock",
                  "scripts/codex_package/cargo.py", "codex-rs/tui/src/config_update.rs",
                  "codex-rs/tui/src/config_update_tests.rs", "codex-rs/tui/src/chatwidget/model_popups.rs",
                  "codex-rs/tui/src/chatwidget/tests/popups_and_settings.rs",
                  "codex-rs/tui/src/chatwidget/snapshots/codex_tui__chatwidget__tests__model_picker_filters_hidden_models.snap"]
        raw = subprocess.check_output(["git", "diff", "--binary", "--", *paths], cwd=source)
        patch.write_bytes(raw)
        (HERE / "laya-native.patch.sha256").write_text(hashlib.sha256(raw).hexdigest() + "\n")
        return
    raw = patch.read_bytes()
    if hashlib.sha256(raw).hexdigest() != (HERE / "laya-native.patch.sha256").read_text().strip():
        raise ValueError("Native patch checksum mismatch")
    if not source.exists():
        source.parent.mkdir(parents=True, exist_ok=True)
        run(["git", "clone", "--filter=blob:none", "--no-checkout", pin["repository"], source])
        run(["git", "-c", "core.longpaths=true", "checkout", "--detach", pin["commit"]], source)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()
    if head != pin["commit"]:
        raise ValueError(f"Source must be at {pin['commit']}; existing checkout was left untouched")
    applied = subprocess.run(["git", "apply", "--reverse", "--check", str(patch)], cwd=source,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    if not applied:
        dirty = subprocess.check_output(["git", "status", "--porcelain"], cwd=source)
        if dirty.strip():
            raise ValueError("Source has unrelated/unrecognized changes; use a new --source directory")
        run(["git", "apply", "--check", patch], source)
        run(["git", "apply", patch], source)
    for relative in ("codex-rs/core/src/session/laya_controller.rs",
                     "codex-rs/core/src/session/laya_controller_tests.rs"):
        run(["git", "add", "--intent-to-add", "--", relative], source)
    actual_diff = subprocess.check_output(["git", "diff", "HEAD", "--binary"], cwd=source)
    if actual_diff != raw:
        raise ValueError("Source differs from the reviewed patch; export intended edits or use a fresh --source")
    if subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard"], cwd=source).strip():
        raise ValueError("Source contains untracked files; existing checkout was left untouched")
    if args.prepare_only:
        print(f"Pinned source and Laya patch ready: {source}")
        return
    # Use upstream's canonical packager: code-mode host, rg and platform sandbox
    # helpers are required too. Installing only codex.exe is not a complete client.
    env = {**os.environ, "CODEX_REPO_ROOT": str(source)}
    if args.toolchain:
        if os.name == "nt" and not args.toolchain.endswith("pc-windows-msvc"):
            raise ValueError("Windows packages require an MSVC toolchain (including the V8 host)")
        env["RUSTUP_TOOLCHAIN"] = args.toolchain
    root = args.home.resolve()
    destination = root / "packages" / (hashlib.sha256(raw).hexdigest()[:12] + "-" + str(time.time_ns()))
    subprocess.run([sys.executable, str(source / "scripts/build_codex_package.py"),
                    "--package-dir", str(destination), "--cargo-profile", args.profile],
                   cwd=source, env=env, check=True)
    binary = destination / "bin" / ("codex.exe" if os.name == "nt" else "codex")
    for name in ("LICENSE", "NOTICE"):
        if (source / name).is_file():
            shutil.copy2(source / name, destination / name)
    receipt = {**pin, "patch_sha256": hashlib.sha256(raw).hexdigest(),
               "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
               "profile": args.profile, "package": str(destination.relative_to(root)),
               "toolchain": subprocess.check_output(["rustc", "--version"], cwd=source / "codex-rs",
                                                    env=env, text=True).strip()}
    pointer = root / "build.json"
    if pointer.exists():
        shutil.copy2(pointer, root / "build.previous.json")
    temporary = root / "build.pending.json"
    temporary.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    temporary.replace(pointer)
    print(f"Installed {binary}. Launch laya-codex; stock codex is unchanged.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f"Native build failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
