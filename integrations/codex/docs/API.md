# MCP contract

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
prediction errors and preserve order. No source files are read by the server.

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

Predictions are advisory. The model's action and confidence fields remain upstream
outputs; no threshold is used to authorize commands or claim correctness.
