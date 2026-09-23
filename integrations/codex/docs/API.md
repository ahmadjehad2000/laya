# MCP contract

`laya_classify_file(workspace, input_path, questions, min_probability=0.95, min_margin=0.5)`
reads an explicit workspace JSON array of `{id,state}` records, writes full results under
`.laya/results`, and returns compact counts, up to 20 review IDs, and the artifact path.
It accepts choice questions only. Thresholds are advisory; errors and unknown labels
need review. Limits: 1,000 records, 16 MiB source file, existing per-record model limits.

`laya_compact_file(workspace, input_path, keep_recent=8)` creates a local handoff and
hash-verified archive under `.laya/handoffs`. It returns artifact paths and byte counts.
It never modifies the running conversation or replaces native compaction. The CLI
provides `compact-file`, `recall`, and `continue` for explicit new-thread continuation.
Both file tools reject resolved input/output paths outside the explicit workspace.
See [cost control](COST_CONTROL.md) for data formats, commands and measured limits.

`laya_predict(state, questions, use_cache=true, model=null)` accepts text, a JSON object,
or a list as state. Model null uses configuration (multilingual by default). Question
IDs are unique, 1–80 characters; there are at most 16 questions by default.

- `choice`: 2–16 unique label strings, or a label-to-description object.
- `score`: 2–16 ordered rubric entries. Output is a zero-based expected index, not a percentage.
- `noul`: proposition P(true); optional `false`/`true` criterion descriptions.

Every question requires nonempty string `instructions`. Unknown question fields and
non-finite JSON values are rejected. The selected tokenizer validates state, instructions,
and options before inference. Limits include the entire question and state.

`laya_predict_batch(items, questions, use_cache=true, model=null)` takes unique
`{id,state}` records, maximum 32 by default. The total serialized request is limited to
128 KiB. Structural batch errors reject the whole call; valid batches return per-item
prediction errors and preserve order. These prediction tools do not read source files;
the explicit file tools below do.

Predictions retain upstream `model`, `answers`, and `usage` fields. Additions are:

- `routing`: chosen model, upstream reason and detection metadata.
- `checkpoint`: variant, repository and pinned revision.
- `context_tokens`: actual input token count per question.
- `runtime`: actual device, fallback reason, cache hit and request timings.

On cache hits, current inference/load times are zero and original measurements are
under `original_runtime`. Cache keys include exact state, ordered questions, chosen
checkpoint and revision. Results are copied before return, so callers cannot mutate
cache entries. Caches are memory-only, bounded and expire after 120 seconds by default.

`elapsed_ms` excludes lock waiting and MCP/Codex overhead. `load_ms` measures model
construction; first-use framework import is included only in elapsed time. No timing
field establishes a complete conversation speedup. Cancellation may leave an active
native kernel running until it finishes; inference is serialized.

For isolated validation, `LAYA_COMPANION_DEVICE` and `LAYA_COMPANION_MODEL` override
their corresponding configuration fields without editing settings. Overrides are validated.

`laya_status` reports no actual device until inference runs. Checkpoint preparation is
checked without importing PyTorch. `laya_release` clears weights/cache. Benchmark is
explicit and bounded to 3–10 synthetic requests with answer caching disabled.

Status includes a per-checkpoint `memory_estimate`, computed from the safetensors header
without loading weights. Cold required RAM is the greater of `min_free_ram_gib` (default
1.0) and checkpoint file bytes + FP32 parameter bytes + `memory_reserve_gib` (default
0.75). All modes construct FP32 parameters on the host. Warm required RAM is at least
0.5 GiB or the configured reserve, whichever is larger. CUDA separately checks the
greater of `min_free_vram_gib` (default 2.5) and FP32 parameter bytes + reserve.
These are conservative estimates, not maximum-memory predictions or allocations.
Existing explicit RAM floors are respected. Model switching releases the previous
resident model before preflight. Results include `runtime.memory_preflight` with actual
available RAM and the estimate used. Batch admission failures include
`error.code: "memory_pressure"`, `retryable: true`, and `details`; they have no answer.
Retry only after resource conditions change. The smaller pinned model is multilingual,
not English. MPS inference remains a separate hardware verification target.

When automatic language routing selects English but its host estimate exceeds available
RAM, a prepared multilingual checkpoint may be used if its estimate fits. The selected
checkpoint/revision and cache key use the actual model. `routing.memory_fallback` records
the original model and preflight, and the routing reason explains the change. Explicit
`english`, `multilingual`, or `typed-decisions` requests never substitute a different
checkpoint. GPU-to-CPU device fallback is still reported separately in `runtime`.

Predictions are advisory. The model's action and confidence fields remain upstream
outputs; no threshold is used to authorize commands or claim correctness.

## Native controller and CLI changes (0.2.0)

The native controller uses a separate, private JSON-lines child process, not a new
MCP tool. Protocol 1 carries request identity, generation, provider model, advertised
efforts and evidence. Responses are `decided` (effort plus lease 1 or 2) or `fallback`
(reason, no inferred effort). Only the native parent applies settings and records
an acknowledgement after capturing the actual step. See [the native contract](../native/README.md).

`continue` defaults to the unified native launcher; `--target codex` explicitly selects stock Codex. Both create a
new thread and verify the content-addressed context artifact. Missing/empty context
arguments include handoff recovery guidance. `--lean` uses the native saved preference when no model is supplied and retains read-only sandboxing.

`compact-file --controller-log PATH` optionally archives an explicit workspace-local
native decision log as provenance; no active lease is carried into continuation.
Known native `configuration_update` rollout items are skipped as execution metadata,
not converted into user instructions. Already compacted exports remain unsupported.

## Local evidence context selection (0.2.1)

`laya_context_file(workspace, input_path, query, max_chars=6000, max_records=8)`
reads a workspace JSON array of unique `{id,state}` records and uses the pinned
local model to classify relevance to `query` (1–500 characters). It returns original
excerpts, source IDs/hash, a local relevance-report path, failed/review counts and
omitted-record count. Excerpt truncation is explicit. `max_chars` is 1–16000 and
`max_records` is 1–32; the character budget applies to excerpt text, not the JSON
envelope. Relevance is advisory and does not establish exhaustive retrieval.

The source path is confined to the explicit workspace. The source hash is checked
against the classification report to reject a source that changed during selection.
Uncertain, low-confidence and failed classifications remain candidate records.
Selected text remains task data; it cannot authorize tools or override instructions.
The complete report is written to `.laya/results`, so this tool has filesystem side
effects but makes no cloud calls itself. Excerpts returned to Codex enter cloud context.

## Required gates (0.3.0)

The native parent treats a missing/invalid Laya decision as a blocking error by default,
including for regular Astra/Sol model names. `LAYA_ENFORCE=0` opts into legacy behavior:
aliases remain advisory/adaptive and regular model names use configured fixed effort.
The `prompt-gate` utility consumes a Codex UserPromptSubmit JSON object on stdin and
emits hook JSON: additionalContext after valid local assessment, or decision=block on
worker failure. The trusted desktop hook gates task admission, not every generation.
See the root README for installation, trust, audit locations and host-failure limits.
