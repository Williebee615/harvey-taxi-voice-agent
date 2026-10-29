# Live model evidence and live test plan

This file records what has actually run against Meta's API. Configuration, a configured key, the console's simulation mode and the offline tests are **not** evidence of inference.

## Status (2026-10-29 UTC)

| Capability | Status | Evidence |
|---|---|---|
| Muse Spark tool calling (Responses API) | **Verified by entrant exports, 2026-10-28**, on earlier code | Two runs in [LIVE_ACCEPTANCE.md](LIVE_ACCEPTANCE.md) |
| Muse Spark image input (appointment card) | **Verified live, 2026-10-29** (one probe call, fictional card) | Probe result below; full card runs (steps 2–3) not yet run |
| Card cross-check, receipts panel, spoken request | **Built and tested offline** (fake Meta transport) | `./helper test` |
| Browser speech recognition | **Not Meta.** Runs in the reviewer's browser | Labeled in the console and docs |
| SAM 3.1 segmentation | **Not integrated.** `sam-3.1` is listed for this account; no request sent | Model list, 2026-10-29 |
| Meta speech-to-text | **Not integrated.** `muse-voice-transcribe-1.0` is listed for this account; no request sent | Model list, 2026-10-29 |

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
