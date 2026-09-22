# Verification and release gates

## September 22 native refresh

- Local Windows companion suite: **101 passed**; upstream contracts: **106 routing
  and 34 criteria checks passed**. Python compilation and whitespace checks passed.
- Reinstalled the companion wheel into the managed runtime and tested a fresh
  isolated worker: [cached-worker report](../evidence/native-worker-cached.json).
- Actual native binary, real Laya CUDA inference and local provider fixture:
  [wire test after caching](../evidence/native-wire-cached.json),
  [missing-worker fallback](../evidence/native-fallback-refresh.json).
- Installed MCP: [report](../evidence/native-companion-refresh.json), zero integration
  failures, **17/24** correct decisions. Smoke exits 2 for these seven recorded
  prediction disagreements; this is not a clean accuracy pass.
- Installed automatic export handoff and real Astra generation:
  [live acceptance](../evidence/native-auto-handoff.json). Constraints and unresolved
  status retained; no real-test success fabricated by the answer.
- [Six real cloud turns](../evidence/native-cost-refresh.json) compare fixed-low,
  fixed-medium and adaptive. The alias has a smaller input prefix; do not attribute
  the lower estimate to effort selection. See [cost analysis](COST_CONTROL.md).

Known visibility mismatch: the live answer says "Laya was not used" while its
native audit records an applied Laya decision. The model's tool-call view does not
establish whether the internal controller ran. Use the native audit for that fact.
No new model weights, cross-platform native verification or general cost-savings
claim is included in this refresh.

Version 0.2.0 adds an experimental, separately built native Astra + Laya client.
The stock companion's real CPU inference was previously exercised on all three desktop platforms.
Checked-in automated tests cover bridge behavior with a fake model backend; they are
not evidence of model accuracy. The MCP smoke test uses a real child server and weights.

## 0.2.0 native controller and installed companion (2026-09-22)

The native client is based on Codex `rust-v0.155.1`, commit
`be2951ea34f0d295ed0becf97079f92fa5f6950e`. Windows x64 MSVC, Rust 1.95.0 and
the `dev-small` profile were used. This is a complete upstream-layout package,
including code-mode host, ripgrep and Windows sandbox helpers, not just a copied
CLI executable. The separate launcher leaves the stock Codex binary intact.
The final exported patch also applied cleanly to a fresh checkout of the pinned commit.

- **Companion:** 89 Python tests passed, including quiet interrupt handling,
  actionable missing-context errors, typed controller abstention, essential-evidence
  preservation, handoff decision provenance, lease reset, and collision-safe managed
  direct commands.
- **Installed runtime:** the non-editable 0.2.0 companion passed seven-tool MCP
  discovery and runtime checks with real Windows CUDA inference. The synthetic model
  labels remain **17/24**, not 24/24. See [installed evidence](../evidence/windows-020-installed-mcp.json).
- **Stock Codex plugin:** after cache-busted reinstall, a fresh Codex session called
  status, classified English/Arabic billing records with CUDA, and released the model.
  See [completed MCP events](../evidence/codex-native.json). A new session is required
  to load an updated plugin; source changes alone do not update a running session.
- **Private worker:** two real decisions passed through the installed package in
  Python isolated mode with the native worker's restricted environment. The second
  request reused the loaded CUDA model. See [worker evidence](../evidence/windows-controller-worker.json).
- **Native generation loop:** the real packaged CLI and real Laya worker exercised
  three generations against a local OpenAI-compatible Responses fixture. The report
  checks provider model normalization, captured effort, request-level effort pinning,
  native `configuration_update` payloads and tool-error lease invalidation. Provider
  responses are fixtures, not real Astra answers. See [wire evidence](../evidence/windows-native-controller.json).
- **Fallback:** the same packaged CLI completed three fixture generations with a
  deliberately missing worker and an explicit audited fallback. See
  [fallback evidence](../evidence/windows-native-fallback.json).
- **Live Astra handoff:** a separate authenticated call retained `feat/tutorial`,
  the 250 MiB budget, the deployment prohibition, and fictional unresolved status,
  without a tool call or claiming the fictional export proved real tests ran.
  [Live evidence](../evidence/windows-native-live-handoff.json) records actual usage
  and the native Laya decision. This is one recall case, not a quality or savings
  benchmark. Model prose about whether "Laya was used" is not authoritative: the
  controller runs below model-visible MCP calls; native decision audit is the evidence.

The changed core/models-manager library run executed 2,430 tests: 2,420 initially
passed and ten failed because the default temporary directory was inside an unrelated
parent Git repository. All ten passed when rerun with an isolated non-Git temporary
directory; three platform/fixture tests were skipped. Six Laya-focused Rust tests
also passed, including stale-settings rejection and model alias normalization.
These results are scoped library checks, not the entire upstream Codex test suite.

The broader terminal-UI library run was **not fully green**: 4,504/4,543 passed,
39 failed and six were skipped. Many inspected snapshot differences are the pinned
release's `0.155.1` banner versus upstream `0.0.0` expectations. The remaining
image-attachment/cursor and other snapshot failures are not resolved or silently
accepted as part of this integration. All six focused config-update and alias-picker
tests passed separately; the picker snapshot explicitly shows **Astra + Laya**.

The native [build and verification guide](../native/README.md) provides reproducible
commands. Linux/macOS native packages, the optimized release profile, full upstream
Codex tests, and the new manually dispatched native CI workflow remain unverified.
Historical cross-platform companion results below do not establish native-client
support. Full-workspace `just fmt` hit Windows command-length/missing DotSlash
limitations; scoped Rust formatting is used for the changed crates.
Scoped `just fix`/Clippy for core, models-manager and TUI completed without warnings.
Python Ruff and local documentation-link checks passed as well.

Controller inference is advisory, bounded and independently implemented with original
Laya/PyTorch. There is no Jev/Ares runtime dependency and no claim about idea ownership.
It does not intercept every stock desktop, subagent or internal compaction call,
replace Codex permissions, or reconstruct encrypted reasoning. Existing handoff/token
benchmarks below must not be attributed to the native effort controller.

## Earlier 0.1.1 local evidence, 2026-09-22

- 71 companion tests passed locally; upstream routing 106/106 and criteria 34/34 passed.
  New coverage includes all device-selection branches, checkpoint-aware RAM estimates,
  retryable resource errors, automatic smaller-model fallback, strict device validation,
  and benchmark metrics. Simulated MPS branches do not establish real MPS hardware support.
- Portable/compatibility plugin and all four skill files passed their validators.
- Original multilingual checkpoint ran on Windows PyTorch CUDA and CPU through actual
  MCP stdio sessions. Both had zero integration failures: five-tool discovery,
  choice/score/noul, cache, per-item truncation errors, and release were exercised.
- Both initial model runs matched 14/20 labeled decisions. File-role classification
  matched only 1/4 and is excluded from recommended workflows. Ticket decisions matched
  9/12, including errors on sales/billing and refund negation. Documents matched 4/4.
- Fixture version 2 adds four natural-language software issues: 3/4 labels matched,
  making the combined result 17/24. Empty/insufficient inputs also need source review.
- A fresh Codex CLI session passed native plugin acceptance: status, an English/Arabic
  batch prediction with source-supported billing labels, and release completed using
  PyTorch/CUDA. [Completed tool events](../evidence/codex-native.json) are recorded
  separately from the MCP SDK tests. The installed compatibility manifest is verified.
- All three original checkpoints loaded and produced valid predictions on Windows CUDA.
  Automatic English/Arabic selection also passed: [five recorded runs](../evidence/windows-checkpoints.json).
- Explicit GPU-default configuration was verified in another fresh Codex session on
  an RTX 4060 Laptop GPU: configured `cuda`, actual `cuda`, no fallback, source-supported
  billing classification, and successful release. See [GPU-default evidence](../evidence/windows-cuda-default.json).
- GitHub Actions fresh installation and real CPU inference passed on Windows, Linux,
  and macOS ARM64 in [run 35717300148](https://github.com/ahmadjehad2000/laya/actions/runs/35717300148).
  This follows fixes for Windows README encoding and a small macOS runner's RAM floor.
  That historical CI run used a 2.5 GiB floor. The current workflow now exercises the
  normal checkpoint-aware estimate rather than overriding a blanket 4.5 GiB floor.
  CI accepts model disagreements only when runtime/transport checks all pass.

Reports: [Windows CUDA](../evidence/windows-cuda.json),
[Windows CPU](../evidence/windows-cpu.json),
[Windows CPU CI](../evidence/windows-cpu-ci.json),
[Linux CPU CI](../evidence/linux-ci/ubuntu-latest.json),
[macOS ARM64 CPU CI](../evidence/macos-cpu-ci.json),
[version 2 fixture](../evidence/windows-cuda-v2.json). These are synthetic cases, not
universal accuracy or latency claims. Apple MPS, bare-metal Linux CUDA, and Intel macOS remain
unverified. Debian WSL2 CUDA is now separately verified below. Python 3.12 is covered on all three desktop platforms; the companion bridge
also passed Ubuntu Python 3.13 in [run 35721329713](https://github.com/ahmadjehad2000/laya/actions/runs/35721329713).

## Benchmark and resource-policy evidence

The fixed 200-record AG News subset matched 191 labels on both Windows CPU and CUDA.
The synthetic fixture stayed at 17/24; the new 12-case rubric matched 4 rounded scores.
Read [the benchmark protocol](../benchmarks/README.md) for selection, exact denominators,
timing boundaries, limitations, and reproducible commands. These are separate claims.

Recorded CUDA cold loads began with 3.67–3.96 GiB available host RAM and used a 2.55 GiB
estimate. CPU cold loads also succeeded below the former 4.5 GiB threshold. All estimates
include checkpoint bytes, FP32 parameter construction, and reserve. A genuine shortage
still rejects admission and produces no answer; retained pressure reports demonstrate
that behavior rather than hiding unsuccessful attempts.

The earlier feature-branch CI failure in run 35719734058 was a timing-sensitive idle
release test on macOS. The test now checks the deadline deterministically, avoiding a
three-second thread-scheduling assumption. The workflow also covers Python 3.13 on Linux,
compiles/lints the companion, and prevents overlapping stale jobs on the same branch/event.

The release gate requires real CPU inference on Windows, Linux, and macOS and separate
evidence for each advertised CUDA/MPS path. A failed or unavailable hardware path remains
unverified. GitHub Actions provides a cross-platform bridge suite and an explicit
real-inference workflow. See generated reports in `evidence/` when available.

The labeled evaluation in `examples/evaluation.json` covers developer and general-work
records, English, Arabic, mixed-language and insufficient-evidence cases. Each expected
label includes an evidence explanation. The script records predictions and disagreements
separately from transport/runtime failures. It is a small synthetic acceptance set and
cannot establish broad real-world accuracy or confidence calibration.

A fresh Codex-session check is separate from the SDK transport test. Report its result
explicitly; do not infer tool discovery merely from configuration or manifest validation.

## Cost-control acceptance (2026-09-22)

The installed 0.1.1 Windows CUDA package passed seven-tool discovery and real MCP
inference, including file-reference classification and a local handoff. The existing
model evaluation remains 17/24; integration success does not erase those disagreements.
A fresh Codex CLI session discovered and called both new tools successfully.

- [Installed MCP evidence](../evidence/windows-cost-installed-mcp.json)
- [Fresh native Codex acceptance](../evidence/cost-native-acceptance.json)
- [Controlled token pilot and quality](../evidence/cost-pilot-windows.json)
- [Cost interpretation and supported integration boundary](COST_CONTROL.md)

All three checkpoints and both automatic-language routes also passed actual Windows
CUDA inference under the adaptive memory policy: [report](../evidence/windows-checkpoints-adaptive-cuda.json).
The prior fixed 4.5 GiB admission floor is no longer used by default.

## Debian WSL2 CUDA (2026-09-22)

Debian 13.6, WSL2 kernel 6.6.114.1, Python 3.13.5, PyTorch 2.11.0+cu128,
RTX 4060 Laptop GPU 8 GiB, Windows driver 616.92. The VM exposed four virtual CPUs
and 7.69 GiB RAM. No Linux NVIDIA display driver was installed.

- Isolated Linux installation and installed seven-tool MCP smoke: zero integration
  errors; synthetic decisions 17/24. [Report](../evidence/linux-wsl-cuda.json).
- All three checkpoints and automatic English/Arabic routing ran on actual CUDA,
  without a CPU fallback or lowered memory guards. [Report](../evidence/linux-wsl-checkpoints.json).
- The Windows MCP client also launched the Linux server through wsl.exe, discovered
  seven tools, obtained a correct CUDA prediction, and released the model.
  [Transport evidence](../evidence/windows-to-wsl-cuda.json).
- The same pinned 200-record benchmark completed with zero harness/record errors:
  191/200 labels, macro-F1 0.9547, short-request median 21.9 ms, batch throughput
  46.8 records/s. [Full measurements](../evidence/benchmark-linux-wsl-cuda.json).

The installer now isolates pip temporary files on disk; Debian's small /tmp tmpfs
previously exhausted space and reduced Windows host RAM during CUDA-wheel downloads.
The manual wheel prefetch encountered HTTP 403 on the PyTorch R2 host; the same
official wheel was obtained from download.pytorch.org and verified against the
index SHA-256 before installation. These setup details do not change model weights.

Windows CUDA remains the installed Codex plugin default. The WSL runtime is installed
as a separately tested compute environment; instructions for selecting it are in
the [Linux CUDA guide](LINUX_CUDA.md).
