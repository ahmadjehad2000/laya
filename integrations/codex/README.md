# Laya for Codex

A local Codex companion built directly on [NandhaKishorM/laya](https://github.com/NandhaKishorM/laya).
Original Laya and PyTorch only. No Laya-MLX code or runtime is used.

**Preview 0.2.0.** Real companion inference passed on Windows CPU/CUDA, Linux CPU, and macOS
ARM64 CPU. See [verification](docs/VERIFICATION.md) for evidence and unverified paths.

## What you can do

- Categorize natural-language issues and summarized log records with source-backed labels.
- Triage English, Arabic and mixed-language tickets or document excerpts.
- Score comparable records against your own ordered rubric.
- Check readiness, inspect actual device/fallback information and release model memory.

The plugin packages five discoverable skills and seven MCP tools. Codex collects evidence
and reviews results; Laya supplies small typed decisions. It does not automatically see
your whole repository or conversation. Model predictions can be confidently wrong.

**Measured limits:** the version 2 multilingual CUDA fixture got 17/24 decisions correct.
Raw-code role classification failed 3/4 cases and is excluded from the recommended
workflow. Sales/billing and explicit refund negation also produced errors. The plugin
requires source review rather than treating confidence as a correctness guarantee.

## Native Astra + Laya

The separate [native client](native/README.md) adds an effort controller inside a
pinned Codex generation loop. Launch `laya-codex` or select **Astra + Laya** in that
client. Actual provider requests still use `gpt-6-astra`. This is an opt-in source
build, not a modification to the stock desktop app. The plugin remains available in
stock clients, without a claim of intercepting every model call.

## Install

Use a local Codex client, Python 3.12 (64 bit), several GB free disk, and preferably
16 GB+ RAM. Cold loading uses a checkpoint-aware estimate: about 2.55 GiB available
RAM for multilingual and 3.10 GiB for English/typed-decisions with default reserves.
These estimates apply to all device modes and do not guarantee peak usage. Model preparation
needs internet; inference is offline afterward. No model API key is required.

Clone the **complete fork**, then run:

```powershell
git clone https://github.com/ahmadjehad2000/laya.git
cd laya/integrations/codex
py -3.12 bootstrap.py install --torch-index cu128 --device cuda
```

For CPU-only Windows/Linux, use `--torch-index cpu --device cpu`.
On macOS use native Python (ARM64 on Apple Silicon):

```sh
python3 bootstrap.py install --device cpu
```

Apple MPS is selectable but remains experimental and unverified.

The installer creates `~/.laya-for-codex/venv`, prepares pinned multilingual weights,
tests a real prediction, then installs the plugin through a generated local marketplace.
It materializes absolute executable paths so Codex does not depend on an activated shell.
It also installs managed `laya-for-codex` and `laya-codex` user commands in
`~/.local/bin`. No per-shell launcher variable or virtual-environment activation is needed.
`Install.ps1` and `install.sh` are convenience wrappers.

For an existing installation, add or repair only the direct commands:

```powershell
py -3.12 bootstrap.py command
laya-for-codex doctor
laya-codex -C "$PWD"
```

If an older managed Laya server is installed, first use `--mode none` to test separately.
Then migrate deliberately:

```sh
python3 bootstrap.py register --mode plugin --migrate-existing
```

Configuration is backed up; unrelated settings are preserved. Open a **new Codex session**:

> Use Laya to categorize “I was charged twice and want a refund” and show the actual device.

Plugin support varies by Codex surface. For a local client requiring direct MCP, use
`--mode direct` instead. Direct registration sets a 300-second cold-load tool timeout.
The plugin uses host timeout defaults. Hosted Codex cannot read your desktop's local
configuration. Installing this package does not provide remote inference.

## Models and tools

For GPU defaults, every configuration knob, batching/cache recipes, offline model
reuse, and the integration fixes found during development, see the root README's
[tuning and practical recipes](../../README.md#tuning-and-practical-recipes).

The default checkpoint is `multilingual`. Explicit alternatives are `english`,
`typed-decisions`, and `auto` (upstream language routing). Auto needs both English and
multilingual checkpoints prepared. Typed-decisions is specialized and never selected
automatically by task-name heuristics.

```sh
python3 bootstrap.py prepare --model all
```

| Tool | Behavior |
|---|---|
| `laya_status` | Readiness, loaded checkpoints, resource and cache counters; no weight loading |
| `laya_predict` | One state and related choice/score/noul questions |
| `laya_predict_batch` | Up to 32 independent `{id,state}` records with shared questions |
| `laya_release` | Unload model and clear memory-only caches |
| `laya_benchmark` | Explicit synthetic diagnostic; not an accuracy evaluation |
| `laya_classify_file` | Workspace JSON records to local predictions and a compact report |
| `laya_compact_file` | Explicit reversible exported-conversation handoff |

See [the quickstart request](examples/quickstart.json) and [the API contract](docs/API.md).
Batch processing is sequential within one MCP request; it reduces tool round trips, not
the number of model forward passes. One model remains resident per server. Switching
models unloads the old model first. Multiple Codex processes can each hold a model.

Edit `~/.laya-for-codex/config.json` and restart the server to change model, device,
thread count, batch limits, cache limits, or idle timeout. Configuration is validated.

## Repair and remove

```sh
python3 bootstrap.py doctor
python3 bootstrap.py uninstall
python3 bootstrap.py rollback
```

Uninstall disconnects the integration and retains environments, checkpoints, and backups.
Rollback restores the saved configuration only if it has not changed since registration;
otherwise it points to the backup for a targeted restore. It does not erase model files.
Missing weights require explicit `prepare`; inference never downloads them.

`serve` is a stdio MCP process, not a web server. Normally Codex starts it. An idle
foreground invocation is waiting for protocol input; Ctrl+C exits with code 130
without a traceback. For `continue --context: expected one argument`, create a
successful handoff first and verify `$handoff.context` exists. The PowerShell member
expression is valid; an unset or failed `$handoff` yields no path. See the guarded
[PowerShell example](../../README.md#g-make-a-local-conversation-handoff-and-retrieve-omitted-output).

## Development

Install the upstream package from this checkout, followed by the companion:

```sh
python -m pip install -r integrations/codex/requirements.lock
python -m pip install --no-deps -e .
python -m pip install -e 'integrations/codex[test]'
python -m pytest integrations/codex/tests -q
python tests/test_router.py
python tests/test_criteria.py
python integrations/codex/scripts/smoke_mcp.py
```

The checked-in plugin uses `laya-for-codex` on PATH for developer use. The installer
renders a separate local copy with absolute paths. Run `scripts/build_plugin.py` after
changing shared plugin metadata. Never commit generated local executable paths.

`scripts/verify_codex.py` exercises the installed plugin in a fresh authenticated Codex
CLI session. It checks actual completed MCP calls and saves a filtered evidence report.
It uses your configured model and normal Codex permissions. `scripts/verify_models.py`
checks all prepared checkpoint selections and automatic English/Arabic routing.

Codex CLI 0.155.1 was tested with the compatibility `.codex-plugin/plugin.json` entrypoint.
In local testing, a root portable manifest installed successfully but did not expose MCP
tools. Therefore the installer and repository marketplace use the compatibility layout.
`plugin.portable.json` is packaged as root `plugin.json` in a separate portable ZIP for
compatible hosts; that ZIP needs the prepared CLI on PATH and is not the verified install path.

The evaluation fixture is manually labeled synthetic evidence, not an independent model
benchmark. Read the report's individual disagreements; schema-valid responses do not
prove the labels are correct. CPU tests do not establish CUDA or Apple MPS support.

## Privacy and attribution

Runtime inference uses local stdio with no listening network port. Setup downloads
packages and pinned model files. Raw prompts are not logged to disk or uploaded by the
companion. Results returned to Codex become part of its conversation and normal data handling.
`act_probability` and confidence are never execution permissions or a security boundary.

This is an independent integration by ahmadjehad2000, not an official OpenAI or Convai
Innovations product. Upstream license and attribution remain intact. See [NOTICE](NOTICE).
