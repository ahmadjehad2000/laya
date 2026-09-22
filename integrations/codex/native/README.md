# Native Astra + Laya (experimental)

`laya-codex` is a separate Codex CLI with a local Laya/PyTorch reasoning-effort
controller. The model picker calls it **Astra + Laya** (`laya-astra`); network requests
use the real `gpt-6-astra` model. Your existing stock Codex CLI/desktop installation
and its normal Laya plugin are not replaced.

## Install and launch

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
changes still persist normally; selecting the Laya alias saves `gpt-6-astra` as the
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
3. Two questions share the evidence: supported reasoning effort and duration (one or
   two generations). Inference uses the prepared multilingual checkpoint with actual
   tokenizer admission. Optional excerpts may be dropped, with omission counts;
   essential requests are never silently truncated. Oversized essential input abstains.
4. Codex checks the response identity/capabilities, atomically verifies the settings
   snapshot is still current, then applies effort through its native settings owner.
   An `APPLIED` notice/audit record is emitted only after a fresh step captures the
   expected effort. Normal permissions, approvals and tool dispatch remain native.

A two-generation lease avoids reloading/reassessing predictable adjacent steps; every
generation still checks invalidation. The worker stays warm within a turn and exits
when the turn ends. Multiple Codex/MCP processes can each hold their own model.
Manual/external setting changes pause adaptation for the remainder of that turn.
New accepted user input, tool failure markers or native compaction/window changes
invalidate the lease. Failure detection is a conservative text heuristic, not a proof
of tool success. Cancellation drops the child process.

Missing weights/worker, protocol mismatch, memory pressure, timeout, or essential
evidence overflow produce an explicit fallback to configured effort and stop retrying
for that turn. Cold inference has a 120-second deadline; warm inference 30 seconds.
Cold imports/loading can dominate a short task. Confidence is not calibrated accuracy.

Only Astra standard single-agent mode with native reasoning-effort support is enabled.
The auto-delegating `ultra` option is excluded from the Laya alias and decision rubric.
This does not intercept subagent/guardian/internal compaction calls or stock desktop
generations. It does not replace Astra, read its private chain of thought, authorize
actions, or guarantee lower costs/better answers. Existing benchmark claims concern
classification/handoffs, not this controller.

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

See [verification evidence](../docs/VERIFICATION.md) for what actually ran. Reproduce
the no-cloud, three-generation native wire test with the installed package's `bin/codex.exe`:

```powershell
$Python = "$env:USERPROFILE\.laya-for-codex\venv\Scripts\python.exe"
$root = "$env:USERPROFILE\.laya-for-codex\native"
$build = Get-Content -Raw "$root\build.json" | ConvertFrom-Json
$binary = Join-Path (Join-Path $root $build.package) "bin\codex.exe"
& $Python integrations/codex/native/verify_native.py --binary "$binary" --output dist/native-fixture.json
& $Python integrations/codex/native/verify_native.py --binary "$binary" --missing-worker --output dist/native-fallback.json
```

This fixture validates actual CLI generations, applied settings and request payloads
against a local Responses server. The normal arm uses real Laya inference; provider
responses are deterministic fixtures, so it does not establish real Astra task quality.
No Jev key, proxy, listening inference service or Ares code is required.

The [native Windows workflow](../../../.github/workflows/laya-native.yml) is manually
dispatched because source builds are expensive. It always checks explicit fallback;
the optional `real_laya` input additionally prepares weights and exercises real CPU
inference. The ordinary companion CI does not establish native-client coverage.
