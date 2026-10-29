# Demonstration evidence: live Meta verification batch, 2026-10-29

**These are hackathon demonstration records, not production data.** Every rider, address, clinic, appointment and curb measurement in them is fictional. The curb measurements are simulated fixtures. No real person, vehicle, dispatch or payment is involved.

## What is here

| File | Contents |
|---|---|
| `run_12a2f40929a7424aa9a70b9b391f4217.json` | Appointment-card scenario. Ends `awaiting_signoff`; 22 Muse Spark turns |
| `run_bc6f128432534209b34bd08d0f29a8ac.json` | Card-contradiction scenario. Ends `needs_input`; only the card check fails; 24 turns |
| `run_1f9f09924a9c46ea9f6e2f3fe1319216.json` | Spoken-request scenario, transcribed by Meta Muse Voice Transcribe. Ends `awaiting_signoff`; 19 turns |
| `run_183e40e119234a9c867e86877b39a493.json` | Authentication-failure scenario (no key, network blocked). Pauses with no receipts |
| `batch_report.json` | Batch totals, spending cap, per-scenario acceptance checks |
| `probe_image.json`, `probe_speech.json` | The single-call image and speech probes run before the batch |

Each run file is the application's **public record**: every Meta receipt (response ID, model, status, token usage, latency), every tool call with its arguments and observed result, recorded facts, independent check results, the memo, and timestamps. Matching the audit fingerprints in [`../../LIVE_EVIDENCE.md`](../../LIVE_EVIDENCE.md) shows the files have not changed since the runs. The fingerprint is the SHA-256 of the record as compact JSON with sorted keys.

## What was removed

- **Credentials:** none were ever stored. The key was injected by the network proxy and never entered the container. A scan for `Bearer`, `LLM_` and `proxy-injected` finds nothing. `MODEL_API_KEY` appears only inside the no-key error message.
- **Model reasoning and prompts:** the public record leaves out the raw conversation (`messages`). That covers Meta's encrypted reasoning items, the system instructions and the image bytes. What remains is what the model chose to do (tool calls and their arguments), what the application observed, and reasoning **token counts** for billing.

## How to check it yourself

```bash
python3 - <<'PY'
import hashlib, json, pathlib
for f in sorted(pathlib.Path('docs/evidence/live-batch-2026-10-29').glob('run_*.json')):
    print(f.name, hashlib.sha256(json.dumps(json.loads(f.read_text()), sort_keys=True).encode()).hexdigest())
PY
```

Compare the output with the audit SHA-256 column in `docs/LIVE_EVIDENCE.md`. The independent checks in each record can be recomputed from the case files with `agent_kit.evidence.inspect(root, case, record['run_documents'], record['card_extraction'])`.

Response IDs come from Meta's responses as saved by the application. They have not been verified against Meta's servers by a third party.
