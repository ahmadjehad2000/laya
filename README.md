<p align="center">
  <img src="assets/laya-codex-banner.svg" alt="Laya for Codex — local, typed decisions inside your workflow" width="100%" />
</p>

<p align="center">
  <a href="https://github.com/ahmadjehad2000/laya/actions/workflows/codex-companion.yml"><img src="https://github.com/ahmadjehad2000/laya/actions/workflows/codex-companion.yml/badge.svg?branch=main" alt="Cross-platform checks" /></a>
  <img src="https://img.shields.io/badge/Python-3.12%E2%80%933.13-3776AB?logo=python&logoColor=white" alt="Python 3.12–3.13" />
  <img src="https://img.shields.io/badge/runtime-PyTorch-EE4C2C?logo=pytorch&logoColor=white" alt="PyTorch runtime" />
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-5e72e4" alt="Apache 2.0 license" /></a>
  <a href="https://github.com/ahmadjehad2000/laya/releases"><img src="https://img.shields.io/badge/release-0.1.0_preview-38bda9" alt="0.1.0 preview" /></a>
</p>

<p align="center">
  <strong>Give Codex a local decision engine for repeated classification, routing, and rubric scoring.</strong><br />
  Built directly on the original <a href="https://github.com/NandhaKishorM/laya">Laya</a>, with PyTorch, a Codex plugin, and MCP.
</p>

<p align="center">
  <a href="#quickstart">Quickstart</a> ·
  <a href="#workflows">Workflows</a> ·
  <a href="#tuning-and-practical-recipes">Tuning recipes</a> ·
  <a href="integrations/codex/docs/API.md">API</a> ·
  <a href="integrations/codex/docs/VERIFICATION.md">Test evidence</a> ·
  <a href="UPSTREAM_README.md">Original Laya docs</a>
</p>

---

Laya for Codex brings small, typed decisions into your existing Codex session. Codex gathers the relevant evidence, sends related questions to a local model, and checks the results against your sources. You get structured labels, rubric scores, and yes/no probabilities without running a separate model service.

**Preview:** the integration passed real inference tests on Windows, Linux, and macOS CPU, plus Windows CUDA. Model accuracy has clear limits: our small synthetic evaluation matched **17 of 24 decisions**. Read [what is verified](#verification) before choosing a workflow.

## Workflows

| Bring to Codex | Ask Laya to help with | Keep Codex responsible for |
| :--- | :--- | :--- |
| Natural-language issues and log summaries | Repeated category or team routing | Checking labels against the original issue |
| English, Arabic, or mixed-language tickets | Topic and intent classification | Resolving ambiguity, negation, and missing evidence |
| Document excerpts and research records | Consistent tagging across a collection | Preserving evidence and reviewing outliers |
| Comparable records and an explicit rubric | Ordered rubric scoring | Explaining scores and validating consequential decisions |

Four included skills cover **developer triage**, **record triage**, **rubric scoring**, and **diagnostics**. Laya is optional; ordinary coding and reasoning continue normally. Raw-code role classification performed poorly in testing and is excluded from recommended workflows.

## Quickstart

You need a local Codex client, **64-bit Python 3.12** (3.13 is supported by the package but not the tested CI version), several GB of free disk, and preferably **16 GB+ RAM**. The default cold-load check requires 4.5 GiB of available RAM. Setup downloads packages and weights; prepared inference runs offline.

```sh
git clone https://github.com/ahmadjehad2000/laya.git
cd laya/integrations/codex
```

<details open>
<summary><strong>Windows · NVIDIA GPU</strong></summary>

```powershell
py -3.12 bootstrap.py install --torch-index cu128 --device cuda
```

Uses PyTorch CUDA when available and reports the actual device. A compatible NVIDIA driver is required for CUDA; the runtime can fall back to CPU.

</details>

<details>
<summary><strong>Windows · CPU</strong></summary>

```powershell
py -3.12 bootstrap.py install --torch-index cpu --device cpu
```

</details>

<details>
<summary><strong>Linux · CPU</strong></summary>

```sh
python3 bootstrap.py install --torch-index cpu --device cpu
```

Use a Python 3.12 interpreter. NVIDIA users can choose `--torch-index cu128`; Linux CUDA has not been exercised in this release.

</details>

<details>
<summary><strong>macOS · CPU</strong></summary>

```sh
python3 bootstrap.py install --device cpu
```

Use native ARM64 Python 3.12 on Apple Silicon. ARM64 CPU inference is verified. Apple MPS is selectable with `--device mps`, but remains experimental and unverified.

</details>

The installer creates an isolated environment under `~/.laya-for-codex`, prepares the pinned multilingual checkpoint, runs a real prediction, and installs the Codex plugin with an absolute executable path. No model API key is needed.

Open a **new Codex session**, then try:

> Use Laya to classify these two tickets as billing, technical, or other: “I was charged twice” and “تم خصم المبلغ مرتين”. Show the actual device and verify each label against the text.

If you already have an older managed Laya integration, first install with `--mode none`, then run `python3 bootstrap.py register --mode plugin --migrate-existing` (`py -3.12` on Windows). The installer backs up the configuration and preserves unrelated settings. See [setup, repair, direct MCP, and rollback](integrations/codex/README.md).

The verified plugin path uses Codex CLI 0.155.1's compatibility manifest. Local clients without plugin support can use `--mode direct`. Hosted Codex cannot access this desktop installation. The portable plugin ZIP is an alternate distribution for compatible hosts; it is not the verified installation path and still needs the prepared CLI on PATH.

## How it fits into Codex

```mermaid
flowchart LR
    A[Your source evidence] --> B[Codex + workflow skills]
    B --> C[Local MCP over stdio]
    C --> D[Original Laya / PyTorch]
    D --> E[Labels · scores · probabilities]
    E --> F[Codex checks against sources]
```

| Tool | Purpose |
| :--- | :--- |
| `laya_status` | Inspect readiness, actual device, loaded model, and resource counters |
| `laya_predict` | Ask related `choice`, `score`, or `noul` questions over one state |
| `laya_predict_batch` | Apply shared questions to up to 32 independent records |
| `laya_release` | Unload the model and clear in-memory caches |
| `laya_benchmark` | Run an explicitly requested synthetic performance diagnostic |

Requests are validated, bounded, and checked for tokenizer truncation. Repeated identical requests can use a bounded memory cache. Batch processing preserves record order and reports individual failures. It reduces tool round trips; model inference remains sequential.

See the [API contract](integrations/codex/docs/API.md) and [example request](integrations/codex/examples/quickstart.json). A `score` result is a zero-based expected rubric index, potentially fractional, from 0 to N−1 for N entries; it is not automatically a percentage. Probabilities and confidence never authorize actions.

## Original Laya, with explicit model selection

| Selection | Checkpoint behavior |
| :--- | :--- |
| `multilingual` | Default; English, Arabic, and mixed-language workflows |
| `english` | Original English checkpoint |
| `typed-decisions` | Explicit opt-in to the upstream typed-decisions checkpoint |
| `auto` | Upstream language routing between prepared English and multilingual models |

Prepare every checkpoint when needed:

```sh
python3 bootstrap.py prepare --model all
```

Checkpoint revisions and SHA-256 hashes are [pinned](integrations/codex/laya_codex_companion/models.json). Preparation verifies weights; inference never downloads missing files. Each MCP server keeps at most one model resident, unloads before switching models, and releases idle model memory. Separate Codex processes can each hold a model.

This fork uses the **original Laya Router and Agent with PyTorch**. It contains no Laya-MLX runtime or dependency. The upstream Python API remains available; its documentation is preserved in [UPSTREAM_README.md](UPSTREAM_README.md).

## Verification

| Check | Result |
| :--- | :--- |
| Companion validation, cache, batch behavior, setup, and rollback | 29 automated tests passed |
| Upstream routing / criteria contracts | 106 / 34 checks passed |
| Fresh installation and real MCP inference | Windows CPU, Linux CPU, macOS ARM64 CPU passed |
| Local GPU inference | Windows CUDA passed |
| Actual plugin use in a fresh Codex session | Status → English/Arabic batch → release passed |
| Checkpoint loading and routing | All three checkpoints + automatic English/Arabic selection passed |
| Apple MPS / Linux CUDA / Intel macOS | Not verified |

[Cross-platform real-inference run](https://github.com/ahmadjehad2000/laya/actions/runs/35717300148) · [Detailed reports and methodology](integrations/codex/docs/VERIFICATION.md)

**Transport correctness and model accuracy are separate.** The version 2 synthetic fixture matched **17/24** expected decisions: software issues 3/4, raw-code roles 1/4, ticket decisions 9/12, and document categories 4/4. Failures included sales-versus-billing ambiguity, explicit refund negation, and insufficient evidence. Raw-code roles remain in the fixture to expose the weakness, not to endorse the use case.

These are small, manually labeled acceptance cases, not broad accuracy, calibrated confidence, or speed claims. Review consequential predictions against source evidence.

## Tuning and practical recipes

These are the actual settings and implementation lessons behind this companion. The
defaults and platform results above are tested; alternative tuning values below are
starting points to measure on your own workload, not hidden switches or promised speedups.

### Make the GPU the default in Codex

The Windows NVIDIA install command above installs the CUDA 12.8 PyTorch build and writes
`"device": "cuda"` to `~/.laya-for-codex/config.json`. The installed plugin reads that
configuration automatically. On an existing GPU installation, change just `device` in
that file, preserving your other settings, and open a new Codex session. No model
redownload or plugin rebuild is needed for a device-only change.

```json
{
  "device": "cuda",
  "model": "multilingual"
}
```

Unspecified settings use the defaults below. `LAYA_COMPANION_DEVICE` and
`LAYA_COMPANION_MODEL` override the file when present **in the server process's
environment**; changing a terminal variable does not reconfigure an already running
Codex app. `LAYA_COMPANION_HOME` selects a separate runtime/configuration directory.

Verify the prepared Windows runtime directly:

```powershell
& "$env:USERPROFILE/.laya-for-codex/venv/Scripts/python.exe" -c "import torch; print(torch.__version__, torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU only')"
```

Then ask Codex:

> Use Laya status, classify “I was charged twice” as billing, technical, or other, and report the configured device, actual runtime.device, and fallback_reason. Release the model afterward.

`laya_status.device` is null before inference; it does not prove GPU failure. Read the
prediction's `runtime.device`. CUDA selection remains a preference: unavailable CUDA or
insufficient free VRAM can cause CPU fallback, which is reported. Our local validation
used an RTX 4060 Laptop GPU with 8 GB VRAM and PyTorch `2.11.0+cu128`; this is an observed
working setup, not a universal minimum requirement.

### Know the knobs before changing them

Edit `~/.laya-for-codex/config.json`, retaining the fields you need, then start a new
server/session. Values outside the supported ranges are rejected.

| Setting | Default | Supported range / practical effect |
| :--- | :--- | :--- |
| `device` | `auto` | `auto`, `cuda`, `cpu`, `mps`; installer `--device` sets your preference |
| `model` | `multilingual` | `multilingual`, `english`, `typed-decisions`, `auto` |
| `question_batch_size` | `4` | 1–16 related questions per upstream call; try 1–2 if memory is tight |
| `max_questions` | `16` | 1–32 questions per request; this is a validation limit |
| `max_items` | `32` | 1–128 independent records per batch; records still run sequentially |
| `max_request_bytes` | `131072` | 1024–1048576 serialized UTF-8 bytes; does not expand model context |
| `cache_entries` | `128` | 0–1024; zero disables storing answers |
| `cache_ttl_sec` | `120` | 0–3600 seconds; zero disables storing answers |
| `idle_unload_sec` | `600` | 1–86400 seconds; shorter frees memory sooner, longer keeps the model warm |
| `min_free_ram_gib` | `4.5` | 0.5–128 GiB; cold-load RAM preflight, not a RAM allocation |
| `min_free_vram_gib` | `2.5` | 0.5–128 GiB; CUDA preflight, not a model-size guarantee |
| `threads` | `4` | 1–32 PyTorch CPU threads; more threads are not always faster |

For a GPU desktop, start with `device: cuda`, the multilingual model, and the other
defaults. For shared or constrained hardware, try `question_batch_size: 1` and
`idle_unload_sec: 120`, then check actual memory use and timings. These alternative
values have not been benchmarked as a faster preset. Raising `max_items` increases work
per tool call, not GPU parallelism.

Do not lower memory floors just to bypass a failure. CI used an explicit 2.5 GiB RAM
floor on constrained runners and passed its small CPU workload; the normal default
remains 4.5 GiB. Even with CUDA, checkpoint loading needs system RAM. Closing unused
model sessions or calling `laya_release` is often the first useful step.

### Spend fewer tool calls and avoid unnecessary loads

1. Put related `choice`, `score`, and `noul` questions over the **same evidence** in one
   `laya_predict` call. Use short instructions and clear label descriptions.
2. Use `laya_predict_batch` for independent records with shared questions. Keep stable
   item IDs and map source references outside the model state. Do not combine unrelated
   tickets into one evidence block.
3. Keep the same checkpoint through a run when appropriate. A server retains only one
   model; changing models unloads the previous one before loading the next. Grouping
   English and Arabic records can reduce switching when using `auto`; using the
   multilingual checkpoint throughout avoids language-driven switches.
4. Keep the model warm during a batch of work. Release it when finished; calling
   `laya_release` between every record forces repeated cold loads and clears the cache.

The answer cache matches the exact state, ordered questions, selected checkpoint, and
pinned revision. It is memory-only. Changed wording or question order can miss the
cache. Use `use_cache: false` when checking fresh inference. A cache hit reports zero
new load/inference time and keeps the earlier measurements under `original_runtime`;
it does not mean the model performed a zero-millisecond forward pass.

### Better labels come from better evidence and criteria

> Use Laya for the repeated labels in these records. Preserve IDs, batch shared questions, use concise source excerpts, and return the supporting evidence with each label. Review negation, ambiguous billing/sales cases, and insufficient information yourself. Do not treat confidence as proof.

Include enough context to support the decision, but avoid pasting a whole repository
or long document. The tokenizer checks the combined state, instructions, and options;
the pinned checkpoint's context is small. Increasing the byte limit does not increase
its token window. A truncation error means split the records or make an evidence-based
summary, preserving negations and qualifiers.

Use distinct label descriptions, and add an `unknown`/`needs_review` option when suitable.
This does not guarantee correct abstention: our insufficient-evidence case still failed.
For scores, order the rubric from low to high and interpret the returned index using
its legend. For `noul`, ask one explicit proposition. Raw-code role inference remains
outside the recommended workflows. High confidence and `act_probability` never grant
execution permission.

### Prepare models once, then work offline

Run these commands from `integrations/codex` (`py -3.12` instead of `python3` on Windows):

```sh
python3 bootstrap.py prepare --model all
python3 bootstrap.py doctor
```

The default model stays multilingual after preparing all checkpoints. Set `model` to
`auto` only when you want upstream language routing; it needs both English and
multilingual checkpoints prepared. `typed-decisions` is always explicit opt-in.

To reuse an existing Hugging Face cache without downloading, run the prepared CLI's
`prepare --model multilingual --source-cache <cache-directory>` command. For Windows:

```powershell
& "$env:USERPROFILE/.laya-for-codex/venv/Scripts/laya-for-codex.exe" prepare --model multilingual --source-cache "$env:USERPROFILE/.cache/huggingface/hub"
```

The exact pinned snapshot must already exist there. Setup copies it into the companion's
own checkpoint directory before tokenizer fixes and verifies the weight hash. Normal
preparation streams weights over HTTPS into a temporary file and only promotes a
checksum-verified download. This avoids the Xet downloader stall encountered during
development. Missing weights are never fetched by an inference call.

### Codex integration fixes worth keeping

| Symptom or constraint | What this companion does / what to check |
| :--- | :--- |
| Plugin appears installed but tools are absent | Uses the compatibility `.codex-plugin/plugin.json` entrypoint verified with CLI 0.155.1; the portable ZIP is a separate, unverified host path |
| Tools disappear after removal or configuration changes | Run `bootstrap.py register --mode plugin`, then open a new session; registration performs a real prediction first |
| Executable is missing from Codex's PATH | Installer materializes an absolute runtime path; no activated terminal is required |
| Old and new Laya registrations collide | Test with `--mode none`, then use deliberate `register --mode plugin --migrate-existing`; unmanaged collisions are refused |
| Slow first request | Cold loading is separate from warm inference; direct MCP registration sets a 300-second tool timeout, while the plugin uses host defaults |
| Windows native initialization or corrupted MCP messages | Server initializes NumPy before worker threads and routes upstream stdout to stderr, preserving protocol stdout |
| Windows package build cannot read Unicode README text | Upstream packaging reads README explicitly as UTF-8 |
| Multiple sessions consume GPU memory | Each MCP process can hold a model; use `laya_release` or finish unused sessions |
| Config changed after install | Guarded rollback refuses to overwrite later edits; retain the backup for a targeted restore |

For a local client requiring direct MCP, use `--mode direct` after disconnecting the
plugin to avoid duplicate servers. A new Codex session is the boundary for loading new
skills, plugin assets, and server configuration. The companion is a tool inside Codex;
it does not move Codex's main reasoning model onto your GPU.

For plugin metadata or skill development, edit the source files, run
`python3 scripts/build_plugin.py` when changing the shared manifest metadata, then
`python3 bootstrap.py register --mode plugin` from `integrations/codex`. Registration
copies the source plugin into the local marketplace and adds a fresh cache version so
Codex picks up the changes. Runtime Python changes require rerunning `install` to update
the isolated package; changing source files alone does not update that installed copy.

### Measure the part you are actually changing

Only request `laya_benchmark` when performance tuning is relevant. It runs 3–10 small
synthetic predictions with answer caching disabled. Compare cold `load_ms`, warm
`inference_ms`, actual device, and fallback reason separately. `elapsed_ms` excludes
lock waiting and MCP/Codex overhead, so it is not end-to-end conversation latency.
The bundled timing diagnostic does not establish model accuracy. Keep quality checks
separate using [the labeled fixture and recorded disagreements](integrations/codex/docs/VERIFICATION.md).

## Privacy and control

- Inference runs locally over stdio, with no listening network port.
- Setup downloads dependencies and public model weights. Prepared inference is offline.
- The companion does not write raw prompts to disk or upload them. Results returned to Codex enter its conversation and normal data handling.
- Configuration controls the device, model, request limits, cache, threads, and idle timeout.
- Uninstall disconnects the integration while retaining weights and backups. Guarded rollback restores the saved configuration when it has not subsequently changed.

## Develop and contribute

```sh
python -m pip install -r integrations/codex/requirements.lock
python -m pip install --no-deps -e .
python -m pip install -e 'integrations/codex[test]'
python -m pytest integrations/codex/tests -q
python tests/test_router.py
python tests/test_criteria.py
```

The companion lives in [`integrations/codex`](integrations/codex). Real-model checks, native Codex acceptance, plugin packaging, and the labeled evaluation are documented there. Report integration errors separately from prediction disagreements when opening an [issue](https://github.com/ahmadjehad2000/laya/issues).

## Credits and license

An independent integration by [ahmadjehad2000](https://github.com/ahmadjehad2000), built as a direct fork of [NandhaKishorM/laya](https://github.com/NandhaKishorM/laya). Credit for Laya, its models, and upstream research belongs to the original authors. This is not an official OpenAI or Convai Innovations product.

[Apache 2.0](LICENSE) · [Attribution notice](integrations/codex/NOTICE) · [Original project documentation](UPSTREAM_README.md)
