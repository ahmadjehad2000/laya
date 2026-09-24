<p align="center"><img src="assets/laya-codex-banner.svg" alt="Laya for Codex" width="100%" /></p>

# Laya for Codex

**Local decisions. Focused context. Visible usage.**

Give **Astra and Sol** a local decision companion throughout the task. Laya for Codex combines the original [Laya/PyTorch](https://github.com/NandhaKishorM/laya) engine with a native Codex integration for approach selection, verification advice, reasoning effort, context selection, and reversible handoffs.

**0.4.0 preview** · CPU/CUDA · Eight MCP tools · Apache-2.0

```powershell
laya-for-codex                    # Astra + Laya
laya-for-codex -m laya-sol        # Sol + Laya
laya-for-codex exec "Fix the failing test, verify the change, and report the result."
```

[Install](#install-on-windows) · [Recipes](#recipes) · [How it works](#how-it-works) · [Verification](integrations/codex/docs/SESSION_RELEASE.md) · [Detailed setup](integrations/codex/README.md)

## Why use it?

- **Decisions throughout the task.** The native gate requires local Laya assessment before each supported generation. It supplies effort plus advice on the next approach, verification scope, and context handling.
- **Read less bulk data.** Select relevant local file excerpts before bringing them into cloud context. Keep source IDs and inspect omissions when they matter.
- **Continue with a smaller handoff.** Archive long tool output while preserving goals, instructions, failures, and recent messages. Recall originals when needed.
- **See what each task used.** A completion report shows provider input, cached input, output, reasoning output and total tokens, local assessment time, and task duration.
- **Reuse work safely.** Exact-evidence decisions use a bounded local cache. Changed evidence is reassessed; native failures and requirement changes invalidate old leases.
- **Keep control.** Codex owns generation, tools and permissions. Laya decisions are advisory and never authorize actions.

Laya is a typed decision model: it returns choices, scores and probabilities. It does **not** generate free-form code or prose. Use Codex to draft candidates and Laya to evaluate them against clear criteria.

## Install on Windows

You need Python 3.12, Git, and an installed/authenticated Codex CLI. The custom native build also needs Rust 1.95.0 with the MSVC toolchain and Visual Studio C++ Build Tools plus a Windows SDK. Allow time and disk space for compilation.

```powershell
git clone https://github.com/ahmadjehad2000/laya-for-codex.git
cd laya-for-codex

# Install the isolated runtime, prepared multilingual model, commands, and plugin.
py -3.12 integrations/codex/bootstrap.py install --torch-index cu128 --device cuda

# Build the separate native client. One build job reduces peak memory use.
$env:CARGO_BUILD_JOBS = "1"
py -3.12 integrations/codex/native/build.py --toolchain 1.95.0-x86_64-pc-windows-msvc

# Open a fresh terminal if the commands are not yet on PATH.
laya-for-codex
```

For a CPU installation, replace the install flags with `--torch-index cpu --device cpu`. Downloads happen during setup; prepared Laya inference runs locally. Astra/Sol still require normal provider access and consume normal provider usage.

The native launcher enables its controller and eight MCP tools automatically. `laya-codex` is a compatible command. Native build instructions and platform limitations are in the [native guide](integrations/codex/native/README.md).

## Linux Installation

Laya for Codex supports Linux with both:

- **CPU inference** using PyTorch CPU
- **NVIDIA CUDA inference** using PyTorch CUDA

The instructions below are intended for **Ubuntu 24.04 LTS / Debian-compatible x86_64 systems**.

### Requirements

Recommended:

- Ubuntu 24.04 LTS
- Python 3.12+
- Git
- 4 GB RAM minimum
- 8 GB+ RAM recommended for building native Codex
- Several GB of free disk space
- NVIDIA driver for CUDA installations

Check Python:

```bash
python3.12 --version
```

Expected:

```text
Python 3.12.x
```

---

### 1. Install Linux dependencies

```bash
sudo apt update

sudo apt install -y \
  git \
  curl \
  ca-certificates \
  build-essential \
  pkg-config \
  libcap-dev \
  musl \
  musl-dev \
  musl-tools \
  clang \
  lld \
  g++ \
  libc++-dev \
  libc++abi-dev \
  cmake \
  make \
  perl \
  xz-utils \
  file \
  python3 \
  python3-venv \
  python3-pip
```

---

### 2. Clone Laya for Codex

```bash
cd ~

git clone https://github.com/ahmadjehad2000/laya-for-codex.git

cd laya-for-codex
```

---

# CPU Installation

Use this path for:

- VMs without NVIDIA GPUs
- General-purpose Linux systems
- Cloud VMs using CPU-only inference
- Development and testing

Install Laya using the CPU PyTorch backend:

```bash
python3.12 integrations/codex/bootstrap.py install \
  --torch-index cpu \
  --device cpu
```

The installer will:

- Create the Laya virtual environment
- Install the pinned PyTorch CPU runtime
- Install Laya and the Codex companion
- Download and verify the configured checkpoint
- Register the Laya Codex plugin
- Install the `laya-for-codex` and `laya-codex` commands

Ensure the local binary directory is available:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

To make this permanent:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

Verify:

```bash
which laya-for-codex
laya-for-codex doctor
```

The doctor output should report:

```text
device: cpu
runtime: upstream-laya-pytorch
```

---

# NVIDIA CUDA Installation

Use this path only when the Linux host has a supported NVIDIA GPU and working NVIDIA drivers.

First verify the GPU:

```bash
nvidia-smi
```

You should see your GPU, driver version, memory usage, and supported CUDA version.

Then install Laya using the CUDA PyTorch backend:

```bash
python3.12 integrations/codex/bootstrap.py install \
  --torch-index cu128 \
  --device cuda
```

Ensure the local commands are available:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Persist the PATH:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

Verify:

```bash
laya-for-codex doctor
```

For an active CUDA runtime, the resulting runtime should use:

```text
device: cuda
```

You can also verify CUDA directly inside the Laya environment:

```bash
"$HOME/.laya-for-codex/venv/bin/python" - <<'PY'
import torch

print("PyTorch:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())
print("CUDA runtime:", torch.version.cuda)

if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
    print(
        "VRAM:",
        round(
            torch.cuda.get_device_properties(0).total_memory
            / 1024**3,
            2,
        ),
        "GiB",
    )
PY
```

Expected:

```text
CUDA available: True
GPU: <your NVIDIA GPU>
```

If CUDA reports `False`, fix the NVIDIA driver / CUDA environment before continuing.

---

# Build the Native Codex Client

The Laya runtime and Codex plugin can be installed independently, but the `laya-for-codex` launcher also requires the native Codex client to be built.

If running:

```bash
laya-for-codex
```

returns:

```text
Native Codex is not built.
```

install the Rust build environment.

### Install Rust

```bash
curl --proto '=https' \
  --tlsv1.2 \
  -sSf https://sh.rustup.rs | sh
```

Load Rust into the current shell:

```bash
source "$HOME/.cargo/env"
```

Ensure Rust binaries have priority:

```bash
export PATH="$HOME/.cargo/bin:$PATH"
```

Install the required Rust toolchain:

```bash
rustup toolchain install 1.95.0 --profile minimal
```

Set it as the default:

```bash
rustup default 1.95.0
```

Install the MUSL target required by the Codex Linux package:

```bash
rustup target add \
  x86_64-unknown-linux-musl \
  --toolchain 1.95.0
```

Verify:

```bash
cargo --version
rustc --version

rustup target list \
  --installed \
  --toolchain 1.95.0
```

Expected targets:

```text
x86_64-unknown-linux-gnu
x86_64-unknown-linux-musl
```

Verify that Rust can locate the MUSL standard library:

```bash
rustc +1.95.0 \
  --print target-libdir \
  --target x86_64-unknown-linux-musl
```

---

### Test the MUSL toolchain

Before compiling Codex, verify that a simple static Rust binary can be built.

```bash
cat >/tmp/laya-rust-musl-test.rs <<'EOF'
fn main() {
    println!("Rust MUSL toolchain works.");
}
EOF

rustc +1.95.0 \
  --target x86_64-unknown-linux-musl \
  /tmp/laya-rust-musl-test.rs \
  -o /tmp/laya-rust-musl-test
```

Run it:

```bash
/tmp/laya-rust-musl-test
```

Expected:

```text
Rust MUSL toolchain works.
```

Inspect it:

```bash
file /tmp/laya-rust-musl-test
```

---

### Build native Codex

Return to the repository:

```bash
cd ~/laya-for-codex
```

For machines with limited RAM, restrict Cargo parallelism:

```bash
export CARGO_BUILD_JOBS=1
```

Then build:

```bash
python3.12 integrations/codex/native/build.py
```

On larger systems you may increase build parallelism:

```bash
export CARGO_BUILD_JOBS=2
```

or remove `CARGO_BUILD_JOBS` entirely and allow Cargo to select the build concurrency.

---

# Final Verification

After installation:

```bash
cd ~/laya-for-codex
```

Check the launcher:

```bash
which laya-for-codex
```

Expected:

```text
/home/<user>/.local/bin/laya-for-codex
```

Run diagnostics:

```bash
laya-for-codex doctor
```

Then launch:

```bash
laya-for-codex
```

---

# CPU Quick Install

For an Ubuntu CPU-only system:

```bash
sudo apt update

sudo apt install -y \
  git \
  curl \
  ca-certificates \
  build-essential \
  pkg-config \
  libcap-dev \
  musl \
  musl-dev \
  musl-tools \
  clang \
  lld \
  g++ \
  libc++-dev \
  libc++abi-dev \
  cmake \
  make \
  perl \
  xz-utils \
  file \
  python3 \
  python3-venv \
  python3-pip

cd ~

git clone https://github.com/ahmadjehad2000/laya-for-codex.git

cd laya-for-codex

python3.12 integrations/codex/bootstrap.py install \
  --torch-index cpu \
  --device cpu

echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
export PATH="$HOME/.local/bin:$PATH"

laya-for-codex doctor
```

---

# CUDA Quick Install

For an NVIDIA Linux system:

```bash
nvidia-smi

sudo apt update

sudo apt install -y \
  git \
  curl \
  ca-certificates \
  build-essential \
  pkg-config \
  libcap-dev \
  musl \
  musl-dev \
  musl-tools \
  clang \
  lld \
  g++ \
  libc++-dev \
  libc++abi-dev \
  cmake \
  make \
  perl \
  xz-utils \
  file \
  python3 \
  python3-venv \
  python3-pip

cd ~

git clone https://github.com/ahmadjehad2000/laya-for-codex.git

cd laya-for-codex

python3.12 integrations/codex/bootstrap.py install \
  --torch-index cu128 \
  --device cuda

echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
export PATH="$HOME/.local/bin:$PATH"

laya-for-codex doctor
```

---

# Common Linux Issues

### `cargo: command not found`

Install Rust using `rustup`:

```bash
curl --proto '=https' \
  --tlsv1.2 \
  -sSf https://sh.rustup.rs | sh

source "$HOME/.cargo/env"
```

---

### `can't find crate for core`

The MUSL Rust target is missing.

Run:

```bash
rustup target add \
  x86_64-unknown-linux-musl \
  --toolchain 1.95.0
```

Verify:

```bash
rustup target list \
  --installed \
  --toolchain 1.95.0
```

---

### `file: command not found`

Install the Linux `file` utility:

```bash
sudo apt install -y file
```

---

### `Native Codex is not built`

Build the native client:

```bash
cd ~/laya-for-codex

source "$HOME/.cargo/env"

export PATH="$HOME/.cargo/bin:$PATH"

python3.12 integrations/codex/native/build.py
```

---

### Build terminated or killed

This is usually caused by insufficient RAM during the Rust build.

Limit Cargo to one build job:

```bash
export CARGO_BUILD_JOBS=1
```

Then retry:

```bash
python3.12 integrations/codex/native/build.py
```

On very small VMs, adding swap or temporarily increasing VM memory is recommended.

---

### CUDA is not detected

Check:

```bash
nvidia-smi
```

Then:

```bash
"$HOME/.laya-for-codex/venv/bin/python" -c \
'import torch; print(torch.cuda.is_available()); print(torch.version.cuda)'
```

If the result is:

```text
False
```

the NVIDIA driver / CUDA environment is not ready for Laya CUDA inference. Fix the GPU environment before reinstalling or switching Laya to CUDA.

### Update an existing installation

From your checkout:

```powershell
git pull --ff-only
& "$env:USERPROFILE/.laya-for-codex/venv/Scripts/python.exe" -m pip install --no-deps . ./integrations/codex
py -3.12 integrations/codex/bootstrap.py register
$env:CARGO_BUILD_JOBS = "1"
py -3.12 integrations/codex/native/build.py --toolchain 1.95.0-x86_64-pc-windows-msvc
```

Restart native sessions after upgrading. Existing processes continue using the code they loaded. The native builder retains the previous package and `build.previous.json` for rollback; it updates the active receipt only after a successful build. See [rollback and removal](integrations/codex/README.md).

### Stock Codex desktop

The plugin provides local tools and a prompt-submission hook. To enable the local hook after reviewing it:

```powershell
py -3.12 integrations/codex/scripts/enable_hooks.py --enable
```

Start a new thread with `gpt-6-astra` or `gpt-6-sol`. Desktop hooks assess submitted prompts; the custom native CLI provides generation-by-generation gating, the status display, and task stats. A disabled or crashed stock hook host can fail open; the plugin cannot change that host behavior.

## Recipes

### 1. Fix and verify code

```powershell
laya-for-codex -m laya-sol exec "Find the cause of the failing tests, make the smallest complete fix, and run relevant checks. Use Laya advice at major milestones. Report unresolved failures."
```

In the native TUI, normal progress appears as `Laya · xhigh · step 6`, without a warning icon. Genuine inference failures remain warnings or blocking errors.

### 2. Review a large evidence file

Store records as a JSON array of `{"id":"record-1","state":"source evidence"}`. Ask Codex:

> Use laya_context_file to select evidence relevant to <question> from <path> before reading the full collection. Preserve IDs and check omitted records that might affect the conclusion.

For repeated classifications, use `laya_classify_file` with shared explicit labels. Keep credentials and hidden reasoning out of model inputs.

### 3. Resume with less context

```powershell
$json = laya-for-codex compact-file --workspace "$PWD" --input conversation.json --keep-recent 2
if ($LASTEXITCODE -ne 0) { throw "Handoff failed" }
$handoff = $json | ConvertFrom-Json
laya-for-codex continue --workspace "$PWD" --context ($handoff.context) --target laya-codex --lean --model laya-sol --prompt "Continue the task, preserving restrictions and unresolved checks."
```

Use an explicit message export. The archive is reversible and hash-checked. This workflow preserves source evidence; it does not replace encrypted native Codex compaction or create a larger model context window.

### 4. Evaluate candidate plans or drafts

> Draft two to four candidate approaches. Give Laya concise public evidence and an explicit choice rubric covering correctness, missing evidence, effort, and verification. Validate its recommendation before implementing the selected approach.

This combines Codex generation with local Laya selection. It does not turn Laya into a text generator.

### 5. Reuse a domain prompt

Start with the [universal domain task prompt](integrations/codex/SESSION_PROMPT.md). Fill in the domain, task, constraints, and acceptance criteria. It includes coding, security, research, document, and data-review criteria. Prompts guide workflow; native runtime checks enforce inference participation.


## Original Laya safeguards

This fork also hardens the original PyTorch engine: direct inference rejects evidence or rubric truncation and invalid numeric outputs. Optional choice-order verification flags unstable answers for review while preserving the primary prediction. Enable `"verify_choice_order": true` in the local runtime config when the additional inference cost is justified; see the [verification guide](integrations/codex/docs/SESSION_RELEASE.md).

## What is measured, and what is not

Local inference adds overhead, especially on a cold checkpoint. Context selection and handoffs can reduce provider input when source content can be omitted safely. **Faster end-to-end work, lower billing, and higher accuracy are task-dependent and are not guaranteed.** See the [release evidence](integrations/codex/docs/SESSION_RELEASE.md) for actual results and scope.

| Model | Full input tokens | Handoff input tokens | Reduction | Full elapsed | Handoff elapsed |
|---|---:|---:|---:|---:|---:|
| laya-astra | 20,653 | 13,122 | 36.5% | 17.19s | 16.00s |
| laya-sol | 20,204 | 12,673 | 37.3% | 16.70s | 16.39s |

One synthetic task per model and arm; both retained the required answer. This illustrates context reduction, not general speed or accuracy.

Enforcement covers supported Astra/Sol standard single-agent main-loop generations. Guardian, subagents, internal compaction calls and stock desktop internal generations are outside this native gate. Missing inference blocks the enforced native path. `LAYA_ENFORCE=0` explicitly opts into legacy advisory behavior.

## Documentation and credit

- [Setup, configuration, devices and removal](integrations/codex/README.md)
- [Native client, enforcement and build details](integrations/codex/native/README.md)
- [Context and cost controls](integrations/codex/docs/COST_CONTROL.md)
- [Verification history](integrations/codex/docs/VERIFICATION.md)
- [Original upstream README](UPSTREAM_README.md)

This fork integrates **NandhaKishorM/laya** with Codex using its original PyTorch runtime. It is a community integration, not an official OpenAI product. See [LICENSE](LICENSE).
