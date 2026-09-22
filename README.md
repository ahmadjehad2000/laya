<p align="center"><img src="assets/laya-codex-banner.svg" alt="Laya for Codex" width="100%" /></p>

# Laya for Codex

**Astra reasoning, local Laya decisions, one CLI.** Version **0.2.1 preview**.

Built on the original [Laya/PyTorch](https://github.com/NandhaKishorM/laya), this integration combines a native Astra effort controller with local MCP tools for classification, context selection and reversible conversation handoffs.

```powershell
laya-for-codex
laya-for-codex exec "Inspect the failing tests and report what remains unresolved."
```

Once the runtime, checkpoint and native package are installed, the CLI starts with **Astra + Laya** and its **eight MCP tools enabled by default**. No plugin registration or activation prompt is needed for this native path, including with `--ignore-user-config`. `laya-codex` remains a compatibility launcher. Stock `codex` and its settings remain separate.

## How they work together

| Responsibility | Laya | Codex / Astra |
|---|---|---|
| Before supported generations | Selects reasoning effort and a short lease from bounded public evidence | Validates and applies the decision; generates the answer |
| Repeated judgments | Classifies independent records and evaluates explicit rubrics locally | Defines criteria and checks consequential labels against sources |
| Extra working context | Selects bounded relevant excerpts from workspace JSON evidence | Reasons over those excerpts and retrieves omitted evidence when needed |
| Large datasets | Reads files locally and returns counts, exceptions and artifact paths | Avoids importing whole datasets into cloud context |
| Continuation | Creates an exact archive and a smaller working handoff from an explicit export | Starts a new thread and preserves normal permissions |

Tool instructions encourage suitable local workflows without the user naming Laya. Tool choice remains model-dependent; the generation-loop controller runs automatically where supported. Laya does not generate Astra's answers, change execution permissions, or replace encrypted native compaction.

## Install

Use 64-bit Python 3.12 or 3.13. Model preparation needs internet and several GB of disk; prepared inference is offline. A 16 GB or larger host is recommended. Native Astra conversations require normal Codex authentication and model access.

```powershell
git clone https://github.com/ahmadjehad2000/laya.git
cd laya
py -3.12 integrations/codex/bootstrap.py install --torch-index cu128 --device cuda
py -3.12 integrations/codex/native/build.py --toolchain 1.95.0-x86_64-pc-windows-msvc
py -3.12 integrations/codex/bootstrap.py command
laya-for-codex
```

The native Windows build requires Git, Rust, PowerShell 7 and Visual Studio C++ Build Tools with a Windows SDK. It is a source build and may take substantial time and disk. See the [native guide](integrations/codex/native/README.md).

For a CPU runtime, use `--torch-index cpu --device cpu`. Companion CPU inference has been verified on Windows, Linux and macOS ARM64; native-client execution is verified separately on Windows. Apple MPS and Linux/macOS native builds are not established by these results.

**Existing managed installation:** pull the latest source and update the companion package without downloading weights again:

```powershell
git pull --ff-only
& "$env:USERPROFILE/.laya-for-codex/venv/Scripts/python.exe" -m pip install --no-deps ./integrations/codex
py -3.12 integrations/codex/bootstrap.py command
laya-for-codex --version
laya-for-codex doctor
```

An existing compatible native build remains usable. If it is missing, the CLI reports the build command; it does not download or build native code during a normal launch. Restart running CLI/MCP sessions after upgrading. Older plugin skills need separate re-registration only when using the stock-client plugin path.

## Daily commands

```powershell
# Interactive native CLI, or one task.
laya-for-codex -C "$PWD"
laya-for-codex exec -C "$PWD" "Review this repository. Do not deploy."

# Inspect native options or resume a thread.
laya-for-codex chat --help
laya-for-codex resume --last

# Local utilities keep their existing explicit commands.
laya-for-codex doctor
laya-for-codex predict integrations/codex/examples/quickstart.json --require-device cuda
laya-for-codex prepare --model all

# Explicit model override. Other models do not activate the Astra controller.
laya-for-codex -m gpt-5.6-sol
```

`--help` describes the unified CLI; `chat --help` shows native options. Bare prompts and native flags pass through unchanged. Names such as `doctor` and `predict` are reserved utility commands; use `chat` or `--` to pass a conflicting word as a native prompt.

## Local context and tools

Put evidence in a workspace JSON array with unique IDs:

```json
[
  {"id":"incident-42","state":"Payment API returns HTTP 503; retry queue stopped."},
  {"id":"release-note","state":"The dashboard color scheme changed."}
]
```

Ask the CLI: **“Find relevant evidence about the payment outage in records.json. Return source IDs and a concise explanation.”** The context tool applies local relevance criteria, returns original excerpts within a character budget, and saves a full relevance report. Uncertain and failed classifications remain review candidates. Omission counts and excerpt truncation are explicit.

This makes larger evidence collections practical to inspect; it does **not** enlarge Astra's model window or guarantee exhaustive retrieval. Selected text remains untrusted task data. Retrieve originals before consequential conclusions.

| Tool | Purpose |
|---|---|
| `laya_context_file` | Select relevant source excerpts from workspace `{id,state}` JSON |
| `laya_classify_file` | Classify a local file; return counts, review IDs and an artifact |
| `laya_predict` | Multiple typed questions over one state |
| `laya_predict_batch` | Shared criteria over independent records |
| `laya_compact_file` | Reversible handoff from an explicit conversation export |
| `laya_status` | Readiness, actual runtime state and resource counters |
| `laya_release` | Unload weights and clear answer caches |
| `laya_benchmark` | Explicitly requested synthetic timing diagnostic |

The launcher configures the installed Python executable directly for MCP, with offline inference and a 300-second tool timeout. Its per-invocation configuration takes precedence over a same-name plugin server, preventing duplicate managed Laya servers. User CLI overrides remain available. Workspace files and global Codex configuration are not rewritten at launch.

## Automatic handoffs

```powershell
laya-for-codex continue --workspace "$PWD" --input conversation.json --keep-recent 8 --prompt "Continue; check unresolved failures."
```

This automatically archives the supplied export and launches the unified native CLI. `--context` reuses an existing handoff; `--target codex` explicitly chooses stock Codex. `--lean` skips user configuration while retaining the native Laya defaults.

Extraction preserves instruction/user/assistant messages, recent messages and recognized failure markers. Exact original bytes remain available through `recall`. Short exports can grow; inspect the preparation report. This is an explicit new-thread workflow, not background interception of your active chat. Keep `.laya/` private and out of version control.

## Performance, cost and limitations

- **Exact repeated controller evidence:** one installed-worker comparison measured 42.62 ms for a warm forward pass versus 0.12 ms for an exact cache hit. This is not a speedup for new evidence. Cold controller loading still took about 11 seconds.
- **Earlier handoff pilot:** 79.8% fewer input tokens on one synthetic long-history recall task, retaining five requested facts. It does not establish general coding savings.
- **Native six-turn cost pilot:** adaptive estimated $0.25228 versus $0.28377 fixed-low and $0.28387 fixed-medium across two small tasks; every arm answered 2/2 correctly. Adaptive took 38.47 seconds versus 12.74 and 11.33 seconds. The alias sent fewer input tokens, confounding any claim that effort selection saved money.
- **Classification quality:** the 200-record AG News subset scored 191/200, but the synthetic workflow fixture scored 17/24 and rubric scoring only 4/12 rounded levels. Confidence is not a correctness guarantee.
- Default MCP tools and context selection add overhead. The older pilot predates this default integration and must not be treated as its measured cost. Quantization, new trained weights, universally cheaper reasoning and cross-turn persistent controllers are not claimed.

[Cost evidence and protocol](integrations/codex/docs/COST_CONTROL.md) · [Benchmark protocol](integrations/codex/benchmarks/README.md) · [Verification and hardware coverage](integrations/codex/docs/VERIFICATION.md)

## Development and references

```powershell
python -m pytest integrations/codex/tests -q
python tests/test_router.py
python tests/test_criteria.py
```

Local utilities and server tests are distinct from real model accuracy and native-client acceptance. Reports under `integrations/codex/evidence/` preserve individual failures and measurements.

[Installation / repair](integrations/codex/README.md) · [Native architecture](integrations/codex/native/README.md) · [API](integrations/codex/docs/API.md) · [Original Laya documentation](UPSTREAM_README.md)

Independent integration by [ahmadjehad2000](https://github.com/ahmadjehad2000), based on original Laya by its upstream authors. Not an official OpenAI product. [Apache 2.0](LICENSE) · [Attribution](integrations/codex/NOTICE).

## Tweaks and configuration

The verified development machine uses an RTX 4060 Laptop GPU (8 GiB), the pinned
multilingual checkpoint and these conservative local settings. They are a measured
working configuration, not a universal fastest preset:

```json
{
  "device": "cuda",
  "model": "multilingual",
  "threads": 4,
  "question_batch_size": 4,
  "cache_entries": 128,
  "cache_ttl_sec": 120,
  "idle_unload_sec": 600,
  "min_free_ram_gib": 1.0,
  "min_free_vram_gib": 2.5,
  "memory_reserve_gib": 0.75
}
```

Edit `~/.laya-for-codex/config.json` and restart CLI/MCP processes to apply changes.
Checkpoint-aware cold-load estimates still apply above the RAM floor. Do not lower
memory guards just to pass a GPU check. `--require-device cuda` rejects CPU fallback.

| Tweak | When useful | Tradeoff |
|---|---|---|
| Keep multilingual pinned | English/Arabic mixed work and lower model-loading footprint | Automatic language routing may switch and reload checkpoints |
| Batch related questions | Multiple judgments about one record | Larger question batches consume more memory |
| Use file/context tools | Large workspace evidence collections | Relevance errors require source review |
| Shorten idle timeout | Many concurrent CLI/MCP sessions | More cold loads; controller workers already exit at turn end |
| Keep answer caching enabled | Exact repeated states and criteria | Novel states do not benefit; cache expires and release clears it |
| `continue --lean` | Explicit new-thread handoff with fewer configured integrations | User configuration is skipped only for that invocation |
| `-c mcp_servers.laya-for-codex.enabled=false` | Diagnose the native controller separately | Local MCP tools are unavailable for that invocation |
| `-m gpt-6-astra` | Compare fixed effort against the adaptive alias | Explicit real-model selection leaves adaptive alias mode inactive |

Normal launches preserve user configuration, including the existing Astra medium
baseline. The ignored-config acceptance test only proves self-contained startup;
it is not a global setting. The launcher adds local MCP defaults per invocation and
respects later command-line overrides. No universal speed or savings claim follows
from these knobs; compare matched tasks, correctness, cache state and total latency.
