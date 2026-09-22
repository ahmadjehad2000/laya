# Reproducible Laya benchmark protocol

This suite is portable across CPU, CUDA, and MPS environments with a prepared original
Laya checkpoint. "Portable" means the workload and measurement procedure can be rerun;
it does not mean one machine's speed or one dataset's accuracy applies universally.
Hardware paths are verified only where a report records real inference on that device.

## Run it

From the repository root, with the companion environment active:

```sh
python integrations/codex/benchmarks/ag_news.py
python integrations/codex/benchmarks/run.py --device cuda --output dist/benchmark-cuda.json
python integrations/codex/benchmarks/run.py --device cpu --output dist/benchmark-cpu.json
python integrations/codex/benchmarks/summarize.py dist/benchmark-cpu.json dist/benchmark-cuda.json
```

Windows activation: `& "$env:USERPROFILE/.laya-for-codex/venv/Scripts/Activate.ps1"`.
Linux/macOS activation: `. "$HOME/.laya-for-codex/venv/bin/activate"`.
Alternatively invoke that environment's Python by its absolute path.

Model preparation is separate: `python integrations/codex/bootstrap.py prepare --model all`.
The default fixed checkpoint is `multilingual`. Use `--model english` or
`--model typed-decisions` for a separate profile. Use `--device mps` only on suitable
Apple hardware. No benchmarking call silently downloads model weights or edits your
installed configuration. A requested/actual device mismatch fails the run, so CPU
fallback cannot be presented as a successful GPU benchmark.

The default profile is 3 fresh server processes, 3 warm-up calls per input length,
30 measured warm calls per length, 30 cache hits, 5 repetitions of each batch scenario,
and a deterministic 200-record public test subset. Run profiles sequentially on a
quiet machine; record power mode, competing applications, and thermal conditions when
comparing machines. Increasing sample counts is supported, but compare matched profiles.

## Workloads and provenance

| Workload | Protocol | What it establishes |
|---|---|---|
| Public classification | AG News test CSV; 50 records per class, seed 1729; title + description | Accuracy and macro-F1 on this fixed English news subset |
| Existing workflow fixture | All 24 labeled decisions from `examples/evaluation.json`, including known failures | Small synthetic developer/document/ticket checks; includes Arabic, mixed text, negation, and missing evidence |
| Rubric fixture | 12 manually labeled incidents, four ordered severity levels | Rounded-index accuracy and MAE for this synthetic rubric |
| Warm latency | One classification question; short, medium, and long authored inputs | Local MCP round-trip p50/p95, separately from server model timings |
| Cache | Prime one exact request, then measure 30 hits | Result-cache overhead; no model forward pass |
| Batch / related questions | 1 and 8 independent records; 3 related questions over one state | Measured throughput and question batching with caching disabled |

The AG News mirror and original test split are documented by
[PyTorch's dataset implementation](https://docs.pytorch.org/text/stable/_modules/torchtext/datasets/ag_news.html).
The source corpus and classification task are described in
[TensorFlow Datasets](https://www.tensorflow.org/datasets/catalog/ag_news_subset).
The download is pinned to Git commit `555590db4219b1243abb1918effd6a7425a2d75f` and
SHA-256 `521465c2428ed7f02f8d6db6ffdd4b5447c1c701962353eb2c40d548c3c85699`.
Its MD5 also matches the official PyTorch dataset entry. It contains 7,600 test records;
the default profile evaluates 200, **not the full test set**. `--per-class 1900` evaluates
all 7,600. Do not compare the default subset score directly with full-test leaderboards.

Selection uses Python `random.Random(1729)`: sample each class in the fixed label order,
then shuffle the combined sample. Zero-based row IDs, expected and predicted labels,
exact question definitions, and hashes are recorded. No training split, few-shot examples,
or post-result prompt tuning is used by this harness. Prior model exposure to this
public dataset is unknown. Dataset text is downloaded into ignored `dist/benchmark-data`;
reports record row IDs rather than redistributing news text. Dataset rights and provenance
remain with the source authors and are not relicensed by this project's Apache license.

## Metrics and failure policy

- Accuracy's denominator includes all selected examples. Failed predictions count as
  incorrect, remain in the report, and also fail the harness's exit status.
- Macro-F1 averages per-class F1 equally. Each class's support, TP, FP, and FN is saved.
- Synthetic `noul` uses a 0.5 threshold. Its valid-result Brier score is reported separately;
  six refund cases cannot establish general probability calibration.
- Rubric output is a zero-based expected index, not a percentage. Rounded accuracy uses
  nearest integer with half values rounded up. MAE is the mean absolute difference from
  the labeled index; normalized MAE divides by three. MAE is valid-result-only and the
  report separately lists failures; failures still count against rounded accuracy.
- Latency percentiles use linear interpolation over the saved raw samples. Thirty calls
  yield a descriptive p95, not a production tail-latency guarantee.
- Client timing wraps the actual MCP tool call, including JSON transport and model work.
  It excludes Codex reasoning, user interaction, and the cost of deciding to call a tool.
- Fresh-process timing records server initialization and the first prediction separately.
  The OS file cache is not flushed; these are process-cold, not guaranteed disk-cold runs.
- Warm prediction and throughput tests use `use_cache: false`. Cache-hit timings are
  labeled separately. Records execute sequentially; this is not heterogeneous tensor batching.
- The resident RSS value is a post-workload process snapshot, not a sampled peak or a
  VRAM measurement. Available host RAM is recorded at each cold-load preflight.
- `--device` overrides only the child process. The persistent GPU preference stays intact.
- Classifier disagreements do not fail the harness; transport failures, record errors,
  device fallback, and missing results do. Reports preserve all disagreements.

The JSON includes hardware, OS, Python/package versions, configuration, checkpoint
revision/hash, runtime source hashes, harness hashes, raw timings, and individual outcomes.
The summary script rejects mismatched models, fixture selections, and measurement counts.

## Interpretation

Strong news classification does not establish reliable code understanding, ticket intent,
rubric scoring, or autonomous actions. In the measured multilingual profiles, the
200-record news subset matched 191 labels while the synthetic workflow fixture remained
17/24 and the rubric matched only 4/12 rounded scores. These are distinct tasks and must
remain distinct claims. Always inspect failures relevant to your actual workflow.

Read the root [benchmark tables](../../../README.md#benchmarks) and the checked-in JSON
reports under `../evidence/`. Windows and WSL share the same physical GPU; differences
also include OS, Python version, memory limits, and background activity. WSL results
cannot establish performance on a native Linux workstation or a different GPU.
