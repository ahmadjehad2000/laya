# Laya for Codex 0.4.0 verification

## Delivered

- Native Astra and Sol require effort and milestone choices before supported generations.
- Approach, verification and context advice is validated and reaches provider input.
- Overflowing request evidence is split without dropping request characters. Short optional progress can be omitted with counts; milestone excerpts are explicitly partial.
- Cache identity covers the complete public evidence, including changes outside excerpts.
- TUI progress uses `Laya · <effort> · step <n>`; the task footer reports usage and timing.
- Desktop prompt gate rejects missing milestone choices.
- Native builds default to one Cargo job to reduce peak memory pressure.
- Original Laya inference rejects silent evidence/rubric truncation and invalid numeric logits/temperatures. Its low-level training sequence builder keeps explicit legacy truncation support.
- Optional `predict_checked` compares reversed choice order, retains the original answer, counts both passes, and flags disagreements for source review.

## Installed verification

Windows, Python 3.12, CUDA, original PyTorch runtime. Companion 0.4.0 and local Laya fork 0.3.4+codex.1 are installed. Native source and patch match the installed build receipt.

- 142 companion/core tests, 106 routing checks, and 34 criteria checks passed.
- Both models: three real Laya decisions across a local three-response provider fixture; all effort, milestone and wire assertions passed.
- Fixture token totals are exactly input=30, cached=0, output=15, reasoning=0, total=45.
- Both models: unavailable worker blocks before any provider request.
- Real cloud Astra and Sol both retained the deployment restriction and unresolved test ID in full and archived-context runs; all four runs emitted task stats.
- Long-request worker tests passed on both model identities, including warm reuse.

The UI change was compiled; no screenshot-based TUI visual verification was performed. The native fixture validates wire behavior using deterministic provider responses, separate from the four real cloud runs.

## Measured context pilot

| Model | Full input tokens | Handoff input tokens | Reduction | Full elapsed | Handoff elapsed |
|---|---:|---:|---:|---:|---:|
| laya-astra | 20,653 | 13,122 | 36.5% | 17.19s | 16.00s |
| laya-sol | 20,204 | 12,673 | 37.3% | 16.70s | 16.39s |

Source: [session-pilot.json](../evidence/session-pilot.json). One synthetic retrieval task, one sample per arm, full then handoff, same native client and provider model. Handoff creation is outside timed CLI execution. This is an illustration of context removal, not a controlled general speed benchmark; hardware load, cold starts, provider latency and selected effort can affect timing. It does not measure billing savings or coding accuracy. The source export was 47,210 bytes; the reversible handoff was about 1.6 KB. Provider input includes other context, so token reduction is smaller than byte reduction.

## Model quality remains a separate constraint

The multilingual fixture scored 17/24 with zero integration failures and seven prediction mismatches. Direct upstream inference reproduced every affected case, confirming these are model judgments rather than adapter conversion errors. The separately prepared typed-decisions checkpoint scored 21/24 on the same fixture; this small, reused fixture is insufficient to justify changing the global checkpoint default. Review missing-evidence, raw-code, pricing-versus-billing, and negation decisions against original sources.

The core fixes prevent hidden information loss and expose option-order instability. They do not retrain the checkpoint or prove that stable answers are correct. Raw-code understanding remains a Codex task.

For optional stability checking, set `"verify_choice_order": true` in `~/.laya-for-codex/config.json` and start a new runtime. This adds a second inference for choice questions and can be slower. MCP answers include per-question verification metadata. Enforced milestone assessment blocks on an unstable result, requiring source review. Default mode keeps the existing single-pass latency.

## Evidence and reproduction

- [Astra wire](../evidence/session-astra-wire.json), [Sol wire](../evidence/session-sol-wire.json)
- [Astra blocked](../evidence/session-astra-blocked.json), [Sol blocked](../evidence/session-sol-blocked.json)
- [MCP transport and model quality](../evidence/session-mcp.json)
- [Direct upstream parity](../evidence/session-prediction-parity.json)
- [Typed checkpoint comparison](../evidence/session-typed-comparison.json)
- [Core overflow and stability](../evidence/session-core-safeguards.json)

`native/verify_native.py` uses a local provider fixture. `native/verify_session.py --output <directory>` checks only the local worker. Add `--live` to make real Astra/Sol calls and consume normal provider usage. `scripts/smoke_mcp.py --installed` distinguishes transport failures from model disagreements.

## Scope and rollback

Native enforcement covers standard single-agent main-loop generations. Guardian, subagents and native internal compaction are outside the gate. Desktop hooks run at submission only. Laya does not generate free text or replace encrypted native compaction. Early fatal exits/aborts may occur before the completion footer.

The native installer retains old packages and `~/.laya-for-codex/native/build.previous.json`. Restore that receipt to `build.json` to select the earlier native package, then restart. Python packages can be rebuilt from the previous Git revision in an isolated checkout using `pip install --no-deps . ./integrations/codex`. Plugin registration keeps its separate rollback receipt. Do not replay old effort leases across sessions.
