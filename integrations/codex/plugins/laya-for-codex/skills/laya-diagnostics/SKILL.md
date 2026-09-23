---
name: laya-diagnostics
description: Check Laya for Codex readiness, troubleshoot local PyTorch inference, and guide explicit model preparation. Use for setup or runtime failures, not as a prerequisite to every prediction.
---

Start with `laya_status`. An empty loaded list and null device mean no checkpoint is loaded, not that CPU or GPU inference has failed. Status does not probe PyTorch. Model preparation and package installation are separate setup actions; follow the user's authorization.

The source installer is `integrations/codex/bootstrap.py` in ahmadjehad2000/laya-for-codex. It provides install, prepare, doctor, register, uninstall, and rollback. The isolated runtime defaults to `~/.laya-for-codex`; on Windows its Python is `venv/Scripts/python.exe`, elsewhere `venv/bin/python`. Never confuse this with the previous `~/.laya-codex` installation.

Missing checkpoint: use the installed runtime's `-m laya_codex_companion prepare --model multilingual|english|typed-decisions|all` when preparation is authorized. It downloads pinned weights; prediction remains offline. Automatic routing needs both English and multilingual checkpoints.

Use `laya_predict` for a small real inference and report actual backend, device, fallback reason, and timings. The backend is original Laya/PyTorch only. CPU, CUDA, and MPS are distinct verification targets. A passing CPU run does not establish GPU support.

For model memory pressure, `laya_release` unloads resident weights and clears caches. Separate Codex processes can each hold a model. Native inference may continue after client cancellation; avoid repeatedly retrying a timed-out load.

Read each checkpoint's `memory_estimate` in status. Cold-load RAM is estimated from the checkpoint file, FP32 parameter construction, and reserve across CPU/CUDA/MPS/auto; an explicit `min_free_ram_gib` remains a lower bound. Warm calls use the reserve. CUDA VRAM has its own preflight. Do not assume English is smaller: the pinned multilingual checkpoint needs less memory than English or typed-decisions. Old versions used a blanket 4.5 GiB check; update the isolated runtime and open a new session rather than blindly lowering a threshold. A batch `memory_pressure` error is retryable after resources change, includes available/required RAM, and has no prediction. Report which items actually succeeded. Do not silently switch to a different checkpoint or claim an evidence-based fallback was a Laya result.

Use `laya_benchmark` only when tuning is relevant or requested. Its short synthetic fixture is neither application-quality evidence nor an end-to-end Codex speed test. Distinguish model errors from MCP transport failures. Report exact errors and useful corrective steps without claiming a broader platform is verified.
