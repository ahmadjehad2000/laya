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
