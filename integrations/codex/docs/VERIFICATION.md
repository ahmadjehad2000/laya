# Verification and release gates

Version 0.1.1 is a preview with real CPU inference exercised on all three desktop platforms.
Checked-in automated tests cover bridge behavior with a fake model backend; they are
not evidence of model accuracy. The MCP smoke test uses a real child server and weights.

## Local evidence, 2026-09-22

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
