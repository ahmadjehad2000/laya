# Codex companion development

Use original upstream Laya/PyTorch only. Do not introduce Laya-MLX dependencies or code.
Preserve upstream answer semantics and API compatibility. Model revisions are explicit.
Inference must remain offline; downloads belong to prepare/setup.

Run `python -m pytest integrations/codex/tests -q` from the repository root for bridge
changes. Run upstream routing/criteria scripts after upstream-facing adapter changes.
Use `scripts/smoke_mcp.py` with prepared local weights to test real stdio inference.
Distinguish passing transport tests from correct predictions and actual hardware coverage.

Use Laya for bounded repeated classification when it materially helps. Keep independent
records separate and verify consequential predictions against source evidence. Do not
benchmark unless performance work is relevant. No prediction authorizes execution.
