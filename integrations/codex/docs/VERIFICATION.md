# Verification and release gates

Version 0.1.0 is a preview until each platform is exercised with real inference.
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
- A separate Codex configuration successfully installed the native plugin from the
  generated local marketplace. Fresh model-driven Codex use is a separate pending check.
- GitHub Actions bridge tests passed on Windows, Linux and macOS in run 35716547757.
  A separate real-inference run passed on Linux CPU; Windows exposed an upstream
  README encoding bug and macOS hit the conservative 4.5 GiB free-RAM check. The
  source encoding is now explicit, and the constrained CI profile uses a 2.5 GiB
  floor. Retesting is required before claiming these two CI paths passed.

Reports: [Windows CUDA](../evidence/windows-cuda.json),
[Windows CPU](../evidence/windows-cpu.json). These are synthetic cases, not universal
accuracy or latency claims. Platform checks below remain open until evidence is recorded.

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
