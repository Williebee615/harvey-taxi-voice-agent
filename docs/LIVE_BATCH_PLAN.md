# Full live verification batch: plan, cost and acceptance criteria

Prepared 2026-10-29 (UTC). **Not yet run.** Each run below needs the owner's approval before it starts.

## Prices used (Meta's published pay-as-you-go rates, read 2026-10-29)

Source: dev.meta.ai/docs/pricing-rate-limits and dev.meta.ai/docs/speech-to-text.

| Model | Standard-mode price | Notes |
|---|---|---|
| `muse-spark-1.3` | $1.25 per 1M input tokens · $0.15 per 1M cached input tokens · $4.25 per 1M output tokens | Images count as input tokens (the live probe used about 310 for the card). Reasoning is assumed to bill as output tokens; this is not confirmed against an invoice. |
| `muse-spark-1.3-contributor` | $0.10 input · $0.002 cached · $0.20 output (per 1M) | Cheaper, but Meta may use the content to train its models. Not used in this plan. |
| `muse-voice-transcribe-1.0` | $0.18 per hour of audio, whole seconds | Failed and rate-limited (429) requests are not billed. |
| `sam-3.1` | $2.50 per 1,000 images | Not used in this plan. |

**Credits:** the dashboard showed **$147.77** in free credits on 2026-10-29 (owner screenshot), before the image probe (about $0.003). The dashboard notes that content sent while free credits are in use may be used for product improvement. Every case in this plan is fictional.

## Runs

| # | Run | Command | Meta calls (estimate) | Estimated cost |
|---|---|---|---|---|
| 1 | Appointment card | `./helper run --case healthcare-appointment-card --mode live --turns 30` | 10–30 | $0.12–$0.88 |
| 2 | Card contradiction | `./helper run --case healthcare-card-contradiction --mode live --turns 30` | 6–18 | $0.05–$0.38 |
| 3 | Spoken request, Meta speech-to-text | `./helper run --case healthcare-clinic-visit --mode live --turns 30 --spoken-audio cases/demo-spoken-request/spoken_request.wav` | 1 transcription + 10–30 | $0.11–$0.85 (speech is about $0.0007) |
| 4 | Failure path | Run 1 with an invalid key: `MODEL_API_BASE` unchanged, `MODEL_API_KEY=invalid`, outside the proxy | 0 billed | $0.00 |
| | **Total** | | **about 27–79 calls** | **about $0.30 minimum, $1.00 typical, $2.10 high** |

How the estimate was made: each run's actual request (instructions, tool definitions, documents, earlier turns, and the card image once attached) was measured offline by replaying the scripted path through a fake connection. That gives the minimum path. "Typical" assumes the live model takes twice as many turns, as the 2026-10-28 clinic run did (24 turns). "High" assumes three times. Input cost grows faster than turn count because each turn re-sends the conversation. Cached-input discounts would lower the real cost; they are not counted.

**Recommended spending cap: $5.00** for the whole batch, about 2.4 times the high estimate. Set an email alert in the Meta dashboard (Billing → Spend limits) if desired.

## Stop rules

- Run at most 30 turns per run. If a run pauses at the limit, report it rather than continuing automatically.
- If any run fails with an API error, stop the batch and report. Do not retry without approval.
- If cumulative token usage (from receipts) exceeds the equivalent of $5.00, stop.
- No changes to case files, checks or instructions between runs.

## Acceptance criteria

A run passes only if every item holds, checked from its saved record (`./helper show --run-id ...`):

| Check | Run 1 (card) | Run 2 (contradiction) | Run 3 (spoken audio) | Run 4 (failure) |
|---|---|---|---|---|
| Final status | `awaiting_signoff` | `needs_input` | `awaiting_signoff` | `paused` with `api_error` |
| Labeled live | `inference_mode` = `LIVE_META_API` and one receipt per model turn | same | same | not live; no receipts |
| Card read by Meta | `card_extraction.extracted_by` = `LIVE_META_API`; all four fields valid | extraction recorded | n/a | n/a |
| Independent checks | all pass, including `appointment_card_check` | **only** `appointment_card_check` fails, citing the date difference | all pass, including `spoken_request_check` | none run |
| Memo | cites the card fields, rider intake, policy and curb evidence | no memo | quotes `spoken_request.txt` | no memo |
| Speech provenance | n/a | n/a | `speech_source.model` = `muse-voice-transcribe-1.0`, with a session ID | n/a |
| Safety | `dispatch_enabled` false; no approval, dispatch or payment tool used | same | same | same |
| Human gate | sign-off only through `./helper approve`, done separately | approval refused | as Run 1 | n/a |

Tool order may vary between live runs. The independent checks decide the outcome, not the model's wording.

## Evidence to record afterwards

Add a row per run to `docs/LIVE_EVIDENCE.md`: run ID, status, number of receipts, first and last response IDs, total input and output tokens, estimated cost, failed checks, and the SHA-256 of the exported audit JSON. No keys, no full transcripts of model reasoning.
