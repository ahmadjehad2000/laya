# Linux CUDA and Debian WSL2

Laya uses the original PyTorch backend on Linux. CUDA requires a compatible NVIDIA GPU,
driver, and CUDA-enabled PyTorch build. Successful driver detection alone is not an
inference test: validate the actual device in a model result.

## Native Linux or a Linux Codex client

Use 64-bit Python 3.12 or 3.13, a functioning `venv` module, and a local Codex CLI for
plugin registration. Clone the complete repository, then run:

```sh
git clone https://github.com/ahmadjehad2000/laya-for-codex.git
cd laya/integrations/codex
python3 bootstrap.py install --torch-index cu128 --device cuda
```

The installer puts the Linux runtime and checkpoint files under `~/.laya-for-codex`.
An explicitly requested CUDA setup must perform a real CUDA prediction before successful
registration; a silent CPU fallback is not accepted as GPU setup success. Ordinary
inference can still report device fallback when resource conditions later change.

For a compute-only environment without a local Codex CLI, add `--mode none`. This
prepares and verifies the runtime without registering a plugin. To use a local client
that needs direct MCP, choose `--mode direct` instead of the plugin mode.

## Debian under WSL2

From Windows PowerShell, verify the distro and GPU:

```powershell
wsl --list --verbose
wsl -d Debian -- /usr/lib/wsl/lib/nvidia-smi
```

Use the Windows NVIDIA driver exposed to WSL2. **Do not install a Linux NVIDIA display
driver inside WSL**; NVIDIA documents that it can overwrite the WSL driver mapping.
See [NVIDIA's CUDA on WSL guide](https://docs.nvidia.com/cuda/wsl-user-guide/index.html).
The PyTorch install above supplies its user-space CUDA dependencies. It does not install
or replace system display drivers.

Run the Linux setup commands inside Debian. Keep the virtual environment and prepared
weights on the Linux filesystem (`$HOME`), rather than reusing a Windows venv or Windows
DLLs. A Windows Python environment cannot serve as the Linux runtime. Checkpoint files
are portable, but reuse requires the same pinned revision and verified hashes.

If Codex runs on Windows while inference should run inside Debian, first prepare the
Linux runtime with `--mode none`. A direct MCP entry in the **Windows** Codex config can
launch WSL (replace `/home/YOUR_LINUX_USER` with the actual Linux home):

```toml
[mcp_servers.laya-linux-cuda]
command = "C:\\Windows\\System32\\wsl.exe"
args = ["-d", "Debian", "--", "/home/YOUR_LINUX_USER/.laya-for-codex/venv/bin/python", "-m", "laya_codex_companion", "serve"]
startup_timeout_sec = 60
tool_timeout_sec = 300
```

The child reads Debian's `~/.laya-for-codex/config.json`, where `device` should be `cuda`.
Choose the Windows runtime or the WSL runtime as your regular integration; avoid leaving
two inference servers loaded unintentionally. The supplied installer does not silently
replace a Windows plugin with WSL. Open a new Codex session after changing registration.
File tools running in WSL require Linux paths such as `/mnt/c/Users/.../project`,
not Windows `C:\...` paths. Keep private `.laya` artifacts with that workspace.

From Windows, verify the same stdio transport before registering it:

```powershell
& "$HOME/.laya-for-codex/venv/Scripts/python.exe" integrations/codex/scripts/smoke_wsl.py --python /home/YOUR_LINUX_USER/.laya-for-codex/venv/bin/python --output dist/windows-to-wsl.json
```

## Verify actual GPU inference

Run from the repository root inside Linux after setup:

```sh
. "$HOME/.laya-for-codex/venv/bin/activate"
python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
python integrations/codex/scripts/smoke_mcp.py --device cuda --require-device cuda --output dist/linux-cuda-smoke.json
python integrations/codex/scripts/verify_models.py --device cuda --require-device cuda --output dist/linux-cuda-checkpoints.json
python integrations/codex/benchmarks/ag_news.py
python integrations/codex/benchmarks/run.py --device cuda --output dist/linux-cuda-benchmark.json
```

The smoke test's exit code is 0 for all fixture labels matching, 2 for prediction
disagreements with transport/device checks passing, and 1 for an integration failure.
The benchmark keeps quality disagreements as data and fails on runtime or device errors.
Do not treat a classifier disagreement as a broken CUDA installation, or CPU fallback
as a passing CUDA test.

For automatic device selection, run the checkpoint check with `--device auto
--require-device cuda`. This tests CUDA selection and English/Arabic routing, including
an explicitly reported smaller-model fallback if automatic routing encounters RAM pressure.

## Memory and failure diagnosis

The installer gives pip a disk-backed temporary directory at
`~/.laya-for-codex/tmp`. This matters on Debian systems where `/tmp` is a small RAM
filesystem: large CUDA wheels can otherwise exhaust both temporary space and host RAM
before inference even starts. These temporary-directory environment variables apply
only to installer subprocesses; global shell settings are unchanged.

- WSL's memory limit is separate from total physical Windows RAM. Check `free -h` inside
  Linux, `nvidia-smi` for device memory, and Laya's own preflight details.
- The new checkpoint-aware policy applies to CPU, CUDA, MPS, and automatic modes.
  Defaults estimate about 2.55 GiB free host RAM for multilingual and 3.10 GiB for the
  two larger pinned checkpoints; CUDA VRAM is checked independently.
- If `torch.cuda.is_available()` is false, resolve driver visibility or the PyTorch
  wheel before declaring GPU setup complete. On WSL, start with the mapped Windows
  driver and the WSL guide, not a Linux display-driver installation.
- If the library import succeeds but a prediction fails, retain the complete error and
  actual device result. Close unused model processes or reduce question batch size when
  activation memory is the issue. Do not hide a host RAM shortage by lowering safeguards.
- After changing runtime source, rerun installation to update the isolated package;
  editing the repository alone does not update the installed wheel.

Linux CPU CI is a separate check from GPU acceptance. The repository's hosted runners
do not provide an NVIDIA GPU. GPU claims must refer to real device reports, and WSL2
results must be identified as WSL2 rather than bare-metal Linux measurements.
