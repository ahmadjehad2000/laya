# Native Astra / Sol + Laya (experimental)

`laya-for-codex` opens the native Codex CLI by default with a local Laya/PyTorch
reasoning-effort controller and eight MCP tools. `laya-codex` remains a compatible
launcher. The model picker offers **Astra + Laya** (`laya-astra`) and **Sol + Laya** (`laya-sol`); network requests
use the corresponding real `gpt-6-astra` or `gpt-6-sol` model. Your existing stock Codex CLI/desktop installation
and its normal Laya plugin are not replaced.

## Install and launch

Version 0.3.0 passes native flags, prompts, exec and resume through the unified CLI.
`laya-for-codex chat --help` shows native options. Local `serve`, `doctor`, `predict`
and other utility subcommands remain available. MCP defaults are invocation-only,
use isolated Python, and work with `--ignore-user-config`; user CLI overrides follow
these defaults. Same-name config registration wins over plugin registration in the
pinned native client. No global config rewrite or additional activation is required.

`laya_context_file` adds local relevance selection over explicit workspace evidence
records. Server instructions encourage this and other suitable workflows proactively;
tool choice is model-dependent. Neither context selection nor effort steering changes
permissions or creates a larger cloud context window.

Select Sol explicitly with `laya-for-codex -m laya-sol` (or `laya-codex -m laya-sol`).
To make it the native launcher's default, save `{"model":"laya-sol"}` in
`~/.laya-for-codex/native/model.json`. With no preference file, Astra remains the
default. Explicit `-m` arguments override this preference. The shared desktop
configuration should use the real `gpt-6-sol` name; desktop Laya tools are provided
by its plugin, while automatic effort steering runs only in this custom CLI.
Restart existing sessions after installing an updated companion/native package.

Sol's bundled metadata was refreshed from the local Codex model catalog on
2026-09-23. Authenticated catalog refreshes can update its advertised capabilities;
Laya chooses only among the current advertised efforts (excluding multi-agent Ultra).

First [install the companion](../README.md#install) and prepare its multilingual
checkpoint. You still need normal Codex authentication/access to Astra for real
conversations. Local Laya does not provide OpenAI access.

From the repository root, Windows PowerShell:

```powershell
# Prerequisites: Git, Rust/rustup, Python 3.12+, PowerShell 7,
# Visual Studio 2022 C++ Build Tools including a Windows SDK.
py -3.12 integrations/codex/native/build.py --toolchain 1.95.0-x86_64-pc-windows-msvc
py -3.12 integrations/codex/bootstrap.py command
laya-codex -C "$PWD"
```

The upstream toolchain pin is Rust 1.95.0. Windows requires MSVC; GNU Rust can check
the core but has no matching prebuilt V8 code-mode host. The default `dev-small`
profile is a development build. `--profile release` requests an optimized build.
Native source builds require substantial free disk/RAM and can take many minutes.
Linux/macOS builds are not established by Windows validation.

`build.py` clones the exact commit in [upstream.json](upstream.json), verifies and
applies [the patch](laya-native.patch), then runs upstream's canonical package builder.
The package includes the CLI, code-mode host, ripgrep and platform sandbox helpers.
Upstream source/dependency/helper downloads happen during setup, not Laya inference.
The release tag has workspace version 0.155.1 but lockfile workspace versions 0.0.0;
the patch normalizes those workspace versions without changing dependency resolutions.

Packages live under `~/.laya-for-codex/native/packages/`. `build.json` selects the
completed package and records source/patch/binary hashes and toolchain. A failed build
does not replace the working pointer; `build.previous.json` preserves the previous
receipt and older packages are retained. The launcher changes only its child process
environment/options. It does not edit your global Codex config, credentials or PATH.
The native CLI reuses normal Codex authentication and settings. Interactive settings
changes still persist normally; selecting the Laya alias saves the corresponding real model as the
shared default so stock Codex never receives an unknown `laya-astra` model name.

```powershell
# Automatic mode is the default in this separate launcher.
laya-codex exec -C "$PWD" "Inspect the failing tests. Do not deploy."
# Explicitly selecting another model leaves the controller inactive.
laya-codex -m gpt-5.6-sol
```

## What happens before each generation

1. Native Codex checks the current model, settings snapshot, accepted user input,
   failure markers and context-window identity. It expires stale decisions.
2. A private child pipe sends explicit user-request text plus bounded recent public
   assistant/tool excerpts to the persistent-within-turn Laya worker. Hidden reasoning,
   encrypted state and injected developer instructions are not serialized. Provider
   credential environment variables are not passed to the worker.
   Python isolated mode prevents a workspace module or `PYTHONPATH` from shadowing
   the installed companion entrypoint.
3. Effort questions share the evidence: supported reasoning effort and duration (one or
   two generations). Inference uses the prepared multilingual checkpoint with actual
   tokenizer admission. Optional excerpts may be dropped, with omission counts;
   essential requests are never silently truncated. Oversized essential input is split and every request character is assessed; admission-limit or inference failures still abstain.
4. Codex checks the response identity/capabilities, atomically verifies the settings
   snapshot is still current, then applies effort through its native settings owner.
   An `APPLIED` notice/audit record is emitted only after a fresh step captures the
   expected effort. Normal permissions, approvals and tool dispatch remain native.

Enforcement is enabled by default for aliases and regular `gpt-6-astra` and
`gpt-6-sol` names. Every supported main-loop generation obtains a validated Laya
decision; strict mode does not reuse two-generation leases. The worker stays warm
within the turn. If inference fails, times out, lacks required evidence, cannot
apply its effort, or encounters incompatible settings, generation stops with an
explicit error. Manual setting changes stop the current enforced turn rather than
being overwritten; submit a new turn to reassess.

Cold inference has a 120-second deadline; warm inference 30 seconds. Set
`LAYA_ENFORCE=0` explicitly only to opt into the older advisory lease/fallback mode.
The standard single-agent restriction and exclusion of auto-delegating `ultra`
apply to Astra and Sol. Guardian, subagent, internal compaction, and stock desktop
generation calls are outside this native gate. See the root README for desktop
prompt-hook enforcement and its host-failure limits.

## Compaction, handoffs and audit

The controller uses Codex's existing `configuration_update` machinery. Request-level
effort remains pinned for cache continuity; native trusted history carries changes.
Codex owns compaction. Laya does not reconstruct encrypted reasoning or silently
replace a full conversation with a smaller model's summary. See the official
[reasoning update restrictions](https://developers.openai.com/api/docs/guides/reasoning#change-reasoning-mid-conversation).

Per-thread decision logs in `~/.laya-for-codex/native/logs/` contain checkpoint/device,
coverage, evidence hash, probabilities, timing and captured settings, not raw prompts.
Treat logs and Codex's own transcripts as private. Explicit handoffs continue to retain
branch constraints, memory budgets, deployment restrictions and unresolved status when
they are present in the exported messages; they do not invent missing facts.

```powershell
$Workspace = "$PWD"
$json = laya-for-codex compact-file --workspace "$Workspace" --input integrations/codex/examples/tutorial/conversation.json --keep-recent 2
if ($LASTEXITCODE -ne 0) { throw "Handoff creation failed" }
$handoff = $json | ConvertFrom-Json
if (-not $handoff.context -or -not (Test-Path -LiteralPath $handoff.context)) { throw "Missing context artifact" }
laya-for-codex continue --workspace "$Workspace" --context ($handoff.context) --target laya-codex --lean --model laya-astra --prompt "Without tools, list the retained restrictions and unresolved status."
```

Optional `--controller-log decisions.jsonl` on `compact-file` accepts only a log you
explicitly place inside that workspace. It archives the bytes/hash and carries recent
provenance with `active_lease: null`. The new native thread reassesses current evidence.

`serve` is the MCP stdio entrypoint, not this interactive CLI. Normally Codex launches
it; an idle foreground server is waiting, not necessarily broken. Ctrl+C exits quietly
with code 130. `--context: expected one argument` usually means `$handoff` was unset
or creation failed; `$handoff.context` itself is valid PowerShell syntax.

## Verification

September 22 refresh: installed CUDA worker and three-generation wire checks pass,
including missing-worker fallback. Companion tests now pass 101 cases locally.
The installed MCP fixture still has zero integration failures and seven prediction
disagreements (17/24 correct). These model limitations are not fixed by caching.

Exact-evidence controller reuse is now enabled through the bounded runtime TTL
cache. Request identities remain fresh and native lease checks remain authoritative.
Cache hits retain original device provenance in `original_runtime`.
Explicit attached model arguments such as `-mgpt-6-astra` are now respected by the
launcher, and text after `--` is treated as positional input.

See the [live cost audit](../docs/COST_CONTROL.md#native-cost-audit-and-automatic-handoffs-2026-09-22):
the adaptive alias was slower on two small tasks; its lower input count confounds
the apparent savings. The existing classifier benchmarks do not establish effort-policy quality.

See [verification evidence](../docs/VERIFICATION.md) for what actually ran. Reproduce
the no-cloud, three-generation native wire test with the installed package's `bin/codex.exe`:

```powershell
$Python = "$env:USERPROFILE\.laya-for-codex\venv\Scripts\python.exe"
$root = "$env:USERPROFILE\.laya-for-codex\native"
$build = Get-Content -Raw "$root\build.json" | ConvertFrom-Json
$binary = Join-Path (Join-Path $root $build.package) "bin\codex.exe"
& $Python integrations/codex/native/verify_native.py --binary "$binary" --output dist/native-fixture.json
& $Python integrations/codex/native/verify_native.py --binary "$binary" --missing-worker --expect-blocked --output dist/native-blocked.json
```

This fixture validates actual CLI generations, applied settings and request payloads
against a local Responses server. The normal arm uses real Laya inference; provider
responses are deterministic fixtures, so it does not establish real Astra task quality.
No Jev key, proxy, listening inference service or Ares code is required.

The [native Windows workflow](../../../.github/workflows/laya-native.yml) is manually
dispatched because source builds are expensive. It always checks required-worker blocking;
the optional `real_laya` input additionally prepares weights and exercises real CPU
inference. The ordinary companion CI does not establish native-client coverage.

## Version 0.4.0 session support

Each supported generation also requires validated approach, verification and context
choices. These choices are supplied to the next provider request as advisory context.
The milestone packet uses explicit partial public excerpts with source hashes and
coverage counts. It is not a semantic summary or a permission grant.

The TUI renders normal Laya application as a status header, without a warning icon.
Normal task completion emits provider token deltas and local assessment timing.
Early aborts or fatal gate errors may exit before this footer; the explicit error and
audit records remain the source of truth. JSON exec retains machine-readable usage.

See [0.4.0 verification](../docs/SESSION_RELEASE.md).
