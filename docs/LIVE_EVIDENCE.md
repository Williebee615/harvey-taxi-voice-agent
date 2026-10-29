# Live model evidence and live test plan

This file records what has actually run against Meta's API. Configuration, a configured key, the console's simulation mode and the offline tests are **not** evidence of inference.

Response IDs below are the ones Meta returned, as saved by the application. The audit-integrity check confirms one is recorded for every model turn; neither it nor this file authenticates them with Meta.

## Status (2026-10-29 UTC)

| Capability | Status | Evidence |
|---|---|---|
| Muse Spark tool calling (Responses API) | **Verified by entrant exports, 2026-10-28**, on earlier code | Two runs in [LIVE_ACCEPTANCE.md](LIVE_ACCEPTANCE.md) |
| Muse Spark image input (appointment card) | **Verified live, 2026-10-29**: probe, plus full card and contradiction runs | Probe result and live batch below |
| Card cross-check, receipts panel, spoken request | **Built and tested offline** (fake Meta transport) | `./helper test` |
| Console **Record** button (Meta speech-to-text through the console's server) | **Verified live with a real microphone, 2026-10-29**, on the hosted console. Also covered offline (fake microphone, stubbed Meta). Browser speech recognition was removed | [Hosted console](#hosted-console-2026-10-29) |
| SAM 3.1 segmentation | **Not integrated.** `sam-3.1` is listed for this account; no request sent | Model list, 2026-10-29 |
| Meta speech-to-text (file transcription) | **Verified live, 2026-10-29**: probe, plus one full spoken-request run (fictional synthetic clip) | Speech probe result and live batch below |

## Probe result: image input (2026-10-29)

Run with owner approval in a cloud session where the key is injected by the network proxy (the key was never in the container). Exactly one paid call.

| Item | Value |
|---|---|
| Time (UTC) | 2026-10-29T08:16:04Z |
| Command | `./helper probe` |
| Model (from response) | `muse-spark-1.3` (Standard mode) |
| Response ID | `resp_6ae300cae614f43acf314310` |
| Result | `PASSED`: all four fields matched |
| Tokens | 388 input (0 cached), 674 output (618 of them reasoning), 1,062 total |
| Estimated cost | about $0.0034 at the published Standard-mode Muse Spark rates ($1.25 / $4.25 per 1M input / output tokens, [pricing page](https://dev.meta.ai/docs/pricing-rate-limits), read 2026-10-29). Assumes reasoning tokens are billed as output. Not checked against the account's billing page. |
| Latency | Not recorded: the probe does not time the call |

| Field (fictional card) | Expected | Extracted | Match |
|---|---|---|---|
| appointment_date | 2026-11-02 | 2026-11-02 | Yes |
| appointment_time | 10:00 | 10:00 | Yes |
| arrive_by | 09:45 | 09:45 | Yes |
| destination | Demo Community Clinic | Demo Community Clinic, Suite 200, Nashville, TN | Yes (contains the expected name; the model also returned the suite and city printed on the card) |

Models listed for this account on 2026-10-29: `muse-image-1.0`, `muse-spark-1.1`, `muse-spark-1.2`, `muse-spark-1.2-contributor`, `muse-spark-1.3`, `muse-spark-1.3-contributor`, `muse-voice-transcribe-1.0`, `muse-wonder-1.0`, `sam-3.1`.

An earlier cloud session the same day was blocked: first by network policy, then by an invalid key (401). The owner replaced the key before this run.

## Probe result: speech-to-text (2026-10-29)

Run with owner approval in the same cloud session (key injected by the network proxy). Exactly one paid call, no retry.

| Item | Value |
|---|---|
| Time (UTC) | 2026-10-29T08:25:09Z |
| Command | `./helper probe-speech` |
| Endpoint and model | `POST /v1/asr/transcribe`, `muse-voice-transcribe-1.0` |
| Session ID | `harvey-d1ca30a59fce` |
| Audio | `cases/demo-spoken-request/spoken_request.wav`: synthetic voice (espeak-ng) reading a fictional script; 13.1 s locally, 13.2 s reported by Meta |
| Latency | 3,221 ms |
| Result | `PASSED`: all five key facts survived |
| Billed audio (estimate) | 13 s |
| Estimated cost | about $0.00065 at the published $0.18 per audio hour ([pricing page](https://dev.meta.ai/docs/pricing-rate-limits), read 2026-10-29). Not checked against the account's billing page. |
| Word error rate | 0.147 (14.7%) against the script |

Script: "Hi, this is Jordan Ellis. I need a wheelchair accessible ride with my service dog to Demo Community Clinic on Monday, November second. I need to arrive by nine forty-five in the morning."

Transcript: "Hi, this is is Jordan Ellis. I need a wheelchair accessible ride with my service dog to Demo Community Clinic on Monday, November 2nd. I need to arrive by 9:45 in the morning."

Most of the word error rate comes from number formatting ("2nd" for "second", "9:45" for "nine forty-five"), which counts as an error but keeps the meaning. The one real error is a repeated "is".

| Key fact | Survived |
|---|---|
| wheelchair | Yes |
| service dog | Yes |
| destination (Demo Community Clinic) | Yes |
| date (Monday, November 2) | Yes |
| arrive by (9:45 a.m.) | Yes |

## Live batch (2026-10-29)

Owner-approved batch (spending cap $5, at most 30 model turns per scenario), run once with `./helper live-batch --cap 5 --max-turns 30`. The key was injected by the network proxy and never entered the container. Nothing was rerun, resumed or retried, and no run was approved: human sign-off stays with the owner. No dispatch, no payments.

| Batch total | Value |
|---|---|
| Ran (UTC) | 2026-10-29T08:31:17Z to 08:33:19Z (about 2 minutes). Corrected 2026-10-29: this row first gave the report's completion time as the start time. |
| Result | All 4 scenarios passed acceptance; stopped early: no |
| Paid calls | 66 (65 Muse Spark turns + 1 Meta transcription) |
| Tokens | 408,875 input (354,398 cached), 17,962 output |
| Estimated cost (cap basis) | $0.5881. Deliberately high: cached input charged at the full input rate, and reasoning tokens charged as output |
| Estimated cost (with cache pricing) | about $0.20, if Meta bills cached tokens at the published $0.15 per 1M. Not checked against the account's billing page |

| Scenario | Run ID | Final status | Receipts | First / last response ID | Input (cached) / output tokens | Est. cost | Failed independent checks | Audit SHA-256 |
|---|---|---|---|---|---|---|---|---|
| authentication failure (no key) | `run_183e40e119234a9c867e86877b39a493` | `paused` | 0 | — | 0 (0) / 0 | $0.0000 | none | `315a1c37bcb8515ebd644d1ed1ac48e4d8d7bd94c307324f0b399b68ba098829` |
| appointment card | `run_12a2f40929a7424aa9a70b9b391f4217` | `awaiting_signoff` | 22 | `resp_6ae3045bc34fd456c9cb480a` / `resp_6ae30487d0c18a2718b543c5` | 148,336 (125,524) / 5,971 | $0.2108 | none | `703b06fe83af4881ae18cfa74276cd9ab983ff196f50ac78f41d536b5abec1bc` |
| card contradiction | `run_bc6f128432534209b34bd08d0f29a8ac` | `needs_input` | 24 | `resp_6ae30488144599e26c164958` / `resp_6ae304b3a02f70027bb74c1d` | 156,120 (137,639) / 7,053 | $0.2251 | `appointment_card_check` | `9f711014533391ece5c0a0540480b3fc967712c683bac1f2e47f601725d71937` |
| spoken request (Meta speech-to-text) | `run_1f9f09924a9c46ea9f6e2f3fe1319216` | `awaiting_signoff` | 19 | `resp_6ae304b70a32bfd982f44009` / `resp_6ae304cfcbb0721915a44280` | 104,419 (91,235) / 4,938 | $0.1522 | none | `3f6f0ead040fd8d498b0e40c5d23f49e154b732b9b5e4ab1303d08610887e1c5` |

Audit SHA-256 is computed over each run's public record (sorted-key JSON) at the end of the batch.

Spoken-request transcription: `muse-voice-transcribe-1.0`, session `harvey-9872c5b35b85`, 13.2 s audio, 2,746 ms latency, about 13 s billed (est. $0.00065). Same fictional clip as the speech probe.

The authentication-failure scenario tests a **missing** key with the network blocked (zero network calls, zero cost). A real Meta 401 could not be produced in this session, because the proxy injects the valid key.

The card-contradiction scenario's "human approval refused" check calls the approval function with a test signature and confirms that it is refused. No run was approved.

### authentication failure (no key): acceptance checks

| Check | Result |
|---|---|
| run paused on the API error | Pass |
| never labeled live | Pass |
| no receipts, no memo | Pass |
| zero network calls | Pass |

### appointment card: acceptance checks

| Check | Result |
|---|---|
| labeled live only after Meta answered | Pass |
| one receipt per model turn | Pass |
| no API error | Pass |
| dispatch disabled, no authorization | Pass |
| final status awaiting_signoff | Pass |
| card fields recorded by the live model | Pass |
| all independent checks pass | Pass |
| card check present and passed | Pass |
| memo cites the card image | Pass |

### card contradiction: acceptance checks

| Check | Result |
|---|---|
| labeled live only after Meta answered | Pass |
| one receipt per model turn | Pass |
| no API error | Pass |
| dispatch disabled, no authorization | Pass |
| final status needs_input | Pass |
| card fields recorded by the live model | Pass |
| only the card check fails | Pass |
| card check cites the date difference | Pass |
| no memo accepted | Pass |
| human approval refused | Pass |

### spoken request (Meta speech-to-text): acceptance checks

| Check | Result |
|---|---|
| labeled live only after Meta answered | Pass |
| one receipt per model turn | Pass |
| no API error | Pass |
| dispatch disabled, no authorization | Pass |
| final status awaiting_signoff | Pass |
| transcript produced by Meta speech-to-text | Pass |
| spoken request check passed | Pass |
| all independent checks pass | Pass |
| memo quotes the spoken request | Pass |

## Hosted console (2026-10-29)

The owner ran these on the password-protected Modal console, deployed from `main` at `c7c1f1a`, within the approved demo budget.

| Item | Result | How it was checked |
|---|---|---|
| Real-microphone transcription | Meta `muse-voice-transcribe-1.0`, session `harvey-28562413d62d`, 17.0 s audio, estimated $0.0008. Transcript "Testing went as planned A1" (not used in a review) | Owner's screen photo |
| `run_b2023b2da615466fba74a611b17ec923` (Standard ride, `healthcare-clinic-visit`) | Live: 24 Muse Spark turns, 24 unique response IDs (`resp_6ae30fa987606135f9f44a9c` to `resp_6ae30fefa5a04e9ad88e47b8`). All 6 independent checks pass when recomputed from the case files; 17 facts quoted verbatim; memo cites the rider request, policy and curb evidence; one refused quote corrected by the model. Signed off by Willie Harvey IV at 09:21:09 UTC; dispatch disabled. Tokens: 141,421 in (105,044 cached), 4,455 out; about $0.08 at cached prices ($0.20 on the high basis). Audit SHA-256 `3ef9b71dde864d5ad85997013318e1110b241763d412c2af992866d4a8ff5465` | Audit JSON exported by the owner, independently re-verified |
| `run_8406197deff449489b2a55b85d4f8de6` (missing return plan) | Reported by the owner: correctly ended `needs_input` on the missing return plan | Audit JSON not yet received for independent checking |

### Note on `run_integrity` in records saved before this fix

Up to `c7c1f1a`, `run_integrity` was only written when a memo was accepted. A run that correctly stopped at `needs_input` therefore kept the initial value `{"passed": false, "errors": ["Not verified yet"]}`. That covers the batch run `run_bc6f128432534209b34bd08d0f29a8ac` and the owner's `run_8406…`. It was an unfinished integrity step, not an audit failure. The new final-state integrity check passes `run_bc6f1284…` when applied to its preserved record. Saved records are left unchanged so their audit fingerprints still match.

## Live test plan (owner approval needed for each paid step)

Use only the fictional cases in this repository. Each live turn is one Meta call. The conversation is replayed every turn, so after the card is attached, the image is re-sent with each later call. Expect token usage to be noticeably higher in card runs.

| Step | Command | Meta calls (estimate) | Pass condition |
|---|---|---|---|
| 1. Probe | `./helper probe` | 1 | `image_input.status` is `PASSED`. Save the JSON. |
| 2. Card case | `./helper run --case healthcare-appointment-card --mode live --turns 30` | about 10–30 | `awaiting_signoff`; `card_extraction.extracted_by` is `LIVE_META_API`; card check passed; one receipt per turn |
| 3. Card contradiction | `./helper run --case healthcare-card-contradiction --mode live --turns 30` | about 6–30 | `needs_input`; only `appointment_card_check` failed; no memo |
| 4. Spoken request | `./helper run --case healthcare-clinic-visit --mode live --turns 30 --spoken-request "I need a wheelchair accessible ride with my service dog to my clinic appointment on Monday."` | about 10–30 | `awaiting_signoff`; memo cites `spoken_request.txt`; spoken request check passed |
| 5. Failure path | Repeat step 2 with an invalid key in a separate shell | 0–1 | Run pauses with `api_error`; no memo; not labeled live |

If a run pauses at the turn limit, continue it with `./helper resume --run-id <id> --turns 20`. Do not start a new run to hide a pause.

**If step 1 fails** (`REQUEST_REJECTED_OR_FAILED`), stop. Do not run steps 2–3, and do not present the card as read by Meta. Record the HTTP status hint here and report the limitation. Any alternative, such as a different request format from Meta's documentation or a typed card transcription, needs a separate decision.

**If step 1 returns `MODEL_RESPONDED_FIELDS_MISMATCH`**, inference worked but the reading was wrong. Record which field was wrong. In the full run, the card check is designed to block the booking, which is itself a valid demonstration of the safeguard.

## What to record after each run

For each run, export the audit JSON from the console (**Download audit JSON**) or use `./helper show --run-id <id>`, then add a row below:

- run ID, case, final status;
- number of receipts, the first and last response IDs, the model;
- which independent checks passed or failed;
- SHA-256 of the exported file (`shasum -a 256 <file>`).

Do not publish full transcripts, keys or account pages.

| Date (UTC) | Step | Run ID | Status | Receipts | Notes |
|---|---|---|---|---|---|
| | | | | | |

## Running the probe

```bash
./helper probe --no-image   # model list only; no inference call
./helper probe              # also one Muse Spark call with the fictional appointment card
```

The result is saved to `workspace/probes/probe_<timestamp>.json`. It contains the endpoint, the listed model IDs, and the image call's response ID, model, token usage, extracted fields and per-field pass/fail. It contains no key and no remote error bodies.

For SAM and speech, `LISTED` only means a model ID appeared. Each still needs its documented request format and a successful call before the project can say it is integrated.
