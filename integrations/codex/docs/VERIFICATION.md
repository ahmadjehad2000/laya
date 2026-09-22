# Verification and release gates

Version 0.1.0 is a preview with real CPU inference exercised on all three desktop platforms.
Checked-in automated tests cover bridge behavior with a fake model backend; they are
not evidence of model accuracy. The MCP smoke test uses a real child server and weights.

## Local evidence, 2026-09-22

- 29 companion tests passed; upstream routing 106/106 and criteria 34/34 passed.
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
- GitHub Actions fresh installation and real CPU inference passed on Windows, Linux,
  and macOS ARM64 in [run 35717300148](https://github.com/ahmadjehad2000/laya/actions/runs/35717300148).
  This follows fixes for Windows README encoding and a small macOS runner's RAM floor.
  CI explicitly uses a 2.5 GiB floor; normal installations retain the 4.5 GiB default.
  CI accepts model disagreements only when runtime/transport checks all pass.

Reports: [Windows CUDA](../evidence/windows-cuda.json),
[Windows CPU](../evidence/windows-cpu.json),
[Windows CPU CI](../evidence/windows-cpu-ci.json),
[Linux CPU CI](../evidence/linux-ci/ubuntu-latest.json),
[macOS ARM64 CPU CI](../evidence/macos-cpu-ci.json),
[version 2 fixture](../evidence/windows-cuda-v2.json). These are synthetic cases, not
universal accuracy or latency claims. Apple MPS, Linux CUDA, and Intel macOS remain
unverified. Python 3.12 was tested; the package also allows 3.13 without a CI claim.

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
