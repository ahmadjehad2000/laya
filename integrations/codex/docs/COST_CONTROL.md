# Cost control: local work before cloud context

## Native cost audit and automatic handoffs (2026-09-22)

The [six-turn live pilot](../evidence/native-cost-refresh.json) uses one installed
native binary, two synthetic tasks, fresh ephemeral threads, ignored user config,
the same response schema and no tools. Order rotates across tasks. This is one
sample per arm/task, not a statistically reliable coding benchmark.

| Arm | Correct | Input tokens | Cached input | Output tokens (includes reasoning) | API-equivalent estimate | Total elapsed |
|---|---:|---:|---:|---:|---:|---:|
| Fixed low | 2/2 | 28,082 | 0 | 59 | $0.283770 | 12.739 s |
| Fixed medium | 2/2 | 28,082 | 0 | 61 | $0.283870 | 11.334 s |
| Adaptive | 2/2 | 24,878 | 0 | 70 | $0.252280 | 38.473 s |

Rates verified against the [official Astra model page](https://developers.openai.com/api/docs/models/gpt-6-astra)
on September 22: $10 input, $1 cache read, $12.50 cache write and $50 output per
million tokens for Standard requests at or below 272k input. Estimates subtract
cached/write tokens from ordinary input, and never count reasoning output twice.
They exclude local power/hardware and do not predict subscription quota or billing.

**Confounder:** the alias used 1,602 fewer input tokens per task. The pilot compares
the complete alias path, not an isolated reasoning policy. Arithmetic used medium;
Python alias tracing used xhigh, with 30 reasoning tokens versus 19 on fixed-low.
The apparent 11.1% reduction is driven by input differences and does not prove
Laya reduces reasoning cost. Two correct trivial answers do not establish quality
on repository work. Cold local loading dominates these short turns.

Reproduce (six cloud turns consume usage):

```powershell
& "$env:USERPROFILE/.laya-for-codex/venv/Scripts/python.exe" integrations/codex/benchmarks/native_cost.py --output dist/native-cost.json
```

Exact evidence and question definitions now use the runtime's existing bounded TTL
cache in the controller. Changed evidence, criterion ordering or checkpoint use
different keys; native identity and lease validation still run. Cache hits expose
the source device/timings in `original_runtime`. No model weights or probabilities
were changed. The observed 42.62 ms to 0.12 ms improvement applies only to an exact
repeat within one warm worker; the worker still exits at the end of a turn.

`continue --input conversation.json` now automatically creates a local handoff
before starting a new CLI thread; `--context` still accepts an existing handoff.
Use `--keep-recent` to set retention (default 8). The input must be an explicit
workspace export. Invalid exports fail before cloud launch, archives retain exact
source bytes, and a JSON preparation report goes to stderr. Short exports can
grow; byte reduction is not a token/cost guarantee. The feature does not monitor
private live sessions, reconstruct hidden reasoning, or take over native compaction.

Next useful experiments are representative coding tasks with equal instruction
prefixes, multiple repetitions, quality checks and total usage including retries.
Model quantization, cross-turn workers and learned effort policies remain unimplemented
until their quality, isolation and memory behavior can be validated.

The useful boundary is **before bulk data reaches Codex**. A plugin that asks Codex to
read every record, repeat it in MCP arguments, and consume verbose results can cost
more than answering directly. Laya now supports file-reference classification and
reversible local conversation handoffs. Both local operations use zero cloud calls.
Codex planning, MCP invocation and continuation still consume usage.

## File classification

Store a JSON array of `{id,state}` records inside the workspace. Supply choice
questions separately; keep criteria explicit and use an unknown label when needed.

```sh
laya-for-codex classify-file --workspace /work/project --input tickets.json --questions questions.json
```

In Codex, ask: “Use Laya to classify tickets.json by file reference. Return counts
and review exceptions; avoid loading the whole dataset into chat.” The
`laya_classify_file` MCP tool returns a compact summary and a `.laya/results/` artifact
with full per-record answers. It supports 1–1000 records and up to 16 MiB per source
file, with the existing per-record model limits. Symlink/path escapes outside the
explicit workspace are rejected. Inputs are never modified.

Default review thresholds are top probability 0.95 and margin 0.5. Missing answers,
errors, uncertain scores and unknown labels need review. These scores are **not
calibrated accuracy guarantees**. Rubric scoring is deliberately excluded from this
shortcut because the existing evaluation found weak rubric quality. No prediction
authorizes changing files, tickets, payments, permissions or external systems.

## Local conversation handoff

```sh
laya-for-codex compact-file --workspace /work/project --input conversation.json
laya-for-codex continue --workspace /work/project --context /work/project/.laya/handoffs/HASH.json --prompt "Continue the tests"
```

`conversation.json` is an array of `{role,content}` messages. Explicit, uncompacted
Codex JSONL exports are also accepted for supported response item types. The rollout
format is not a stable public interface: unknown response types and already compacted
exports are rejected. Hidden reasoning is not exported or reconstructed.

The operation retains every user, assistant, system and developer message, the last
eight messages, and tool output containing explicit failure/permission markers.
Older tool output over 1,200 characters becomes a reference with a short preview.
This is conservative extraction, not a semantic summary. Errors without recognized
markers and important facts inside old output can still be omitted from the working
context. The original bytes remain in a SHA-256-verified `.source` archive. Retrieve
an exact message when needed:

```sh
laya-for-codex recall --workspace /work/project --archive /work/project/.laya/handoffs/HASH.source --index 5
```

`continue` starts a **new Codex CLI thread**, using the configured Codex model and
normal permissions. It does not modify the running thread, copy authorization from
history, or upload the archive automatically. All preserved context is passed as
historical user-level data. Keep `.laya/` private and ignored by Git: it contains
original conversation contents. Short histories can become larger due to references;
inspect byte counts before continuing. Byte counts are not token counts.

## Why native compaction is not silently rerouted

[Codex hooks](https://learn.chatgpt.com/docs/hooks) expose `PreCompact`, but its
supported output can stop compaction, not replace the compacted context. Blocking
it alone can strand a full-context thread. `UserPromptSubmit` adds context or blocks
a prompt; it is not a replacement-model API. The
[compact_prompt setting](https://learn.chatgpt.com/docs/config-file/config-reference)
changes instructions, not the computation provider. OpenAI's
[native compaction](https://developers.openai.com/api/docs/guides/compaction) can
carry opaque encrypted reasoning state that Laya cannot recreate.

Consequently, no global interception hook, credential proxy, transcript mutation,
or native-compaction disable switch is installed. The separate 0.2.0
[native client](../native/README.md) maintains a pinned Codex patch for **reasoning
effort**, not replacement compaction. It uses the upstream native configuration-update
path, invalidates leases after a context-window change, and leaves Codex compaction
in charge of its own state. The new-thread handoff remains an explicit alternative.

Use `continue --target laya-codex --model laya-astra` after building that client.
Optional `compact-file --controller-log decisions.jsonl` carries a deliberately
supplied native log inside the workspace as historical provenance. It records the
checkpoint, evidence hash, coverage and captured effort, archives the original log,
and never resumes an old lease. It does not read your private Codex history automatically.

The pilot below measured the original handoff and classification workflows. It does
**not** establish native adaptive-effort cost savings, task quality or a speedup.

## Measured pilot

On 2026-09-22, Codex CLI 0.155.1, `gpt-5.6-sol`, low reasoning, three fresh ephemeral
turns with user config ignored:

| Workload | Codex control | Local-first path | Quality observed |
|---|---:|---:|---|
| Synthetic long-history recall | 84,355 input / 49 output tokens | 17,001 input / 49 output tokens | Same five facts retained; 3 exact strings, 2 equivalent wordings |
| 20 pinned AG News records | 14,980 input / 197 output tokens | 0 cloud calls for local classification | Both 19/20; Laya flagged its one wrong answer for review |

The handoff used **79.8% fewer total input tokens**. Both calls reported zero cached
input tokens. Latency was about 11 seconds in both arms: this pilot did not establish
a speedup. The classification figure excludes a Codex orchestration/review turn and
therefore does not claim zero-cost use from the Codex chat UI. Local electricity,
GPU memory, installation and human review are not free.

One synthetic history and 20 records are a feasibility test, not a general coding
benchmark. The saved fixture emphasizes redundant tool output; user/assistant-heavy
histories will shrink less. Equal aggregate accuracy does not imply identical errors
or general equivalence. No dollars or subscription-quota percentage are inferred.
Token accounting depends on model, cache state, tools and task context.

The normal-profile plugin acceptance test was much heavier: 126,092 total input
tokens, including 84,480 cached input tokens, for two MCP operations and their
orchestration. It validates native tool discovery, **not savings**. Unrelated loaded
instructions/plugins and repeated model turns can dominate small jobs. For an
explicit lean CLI handoff, add `--lean --model gpt-5.6-sol` to `continue`; this skips
user config for that invocation and uses a read-only sandbox. It is opt-in because
user-configured preferences and integrations will not load. No persistent config
is changed, and this is not a blanket recommendation for coding workflows.

[Raw usage and predictions](../evidence/cost-pilot-windows.json) ·
[Reproducible pilot](../benchmarks/cost_pilot.py)

```sh
# Opt-in: this runs three cloud Codex turns and consumes usage.
python integrations/codex/benchmarks/cost_pilot.py --model gpt-5.6-sol --output dist/cost-pilot.json
```

The larger fixed benchmark remains 191/200 AG News classifications (95.5%) and only
4/12 rounded rubric levels. Use selective local offload with source validation,
not blanket rerouting of coding or arbitrary reasoning to this small classifier.
