# Harvey Taxi — Accessible Voice-Booking & Verification Agent

A rider says what they need. Meta's models listen, read the appointment card and investigate the booking. Deterministic code then checks every fact, and a person signs off before anything happens.

Built for the Meta Global AI Developer Hackathon (Startup track, *Build for Your World*) by Willie Harvey IV, founder of Harvey Taxi Service LLC in Nashville. **This is a contest prototype.** It has not been used with real riders, and no operating scale or production readiness is claimed. All riders, clinics and appointments in it are fictional, curb measurements are simulated, and it never dispatches a vehicle or takes a payment.

## What it does

```text
 Rider speaks ──► Meta muse-voice-transcribe-1.0 ──► transcript the rider confirms
                                                              │
 Appointment card image ──► Meta muse-spark-1.3 reads it ─────┤  (untrusted evidence)
                                                              ▼
      Muse Spark runs the review, choosing one tool per turn:
      list documents → set checklist → analyze documents → submit memo
                                                              │
      Independent code checks, which the model cannot override:
      intake · tariff quote · fare arithmetic · $0 accessibility fee ·
      curb bay · counter-evidence · healthcare transport fields ·
      card fields vs request · spoken needs vs intake ·
      spoken dates and times vs booking and card · exact citations
                                                              ▼
            awaiting_signoff (human reviewer)  or  needs_input (blocked)
```

1. **Spoken request.** The console records only after the rider clicks Record. The audio goes to the console's own server, which sends it to Meta Muse Voice Transcribe, so the API key never reaches the browser. The rider confirms the transcript before it is used.
2. **Appointment card.** A photo of the card is attached for Muse Spark, which records the date, times and clinic it reads. Code cross-checks those fields against the written booking. If they disagree, or a field can't be read, the booking stops at `needs_input`.
3. **Investigation.** Muse Spark picks each tool itself, quotes the source files exactly, and must cite evidence for every checklist question.
4. **Independent checks.** Fare (`$2.50 + $1.50/mile`, accessibility fee always `$0.00`), curb clearance, intake completeness, contradictions and the card are all checked by code, not by the model.
5. **Human sign-off.** A passing review stops at `awaiting_signoff`. Only a named reviewer can acknowledge it, and acknowledgment never dispatches anything.

## Verified live on Meta (2026-10-29)

| Capability | Result | Evidence |
|---|---|---|
| Muse Spark tool-calling review | 3 live runs, 65 model turns, every turn with a Meta response ID | [Live batch](docs/LIVE_EVIDENCE.md#live-batch-2026-10-29) |
| Appointment-card image understanding (`muse-spark-1.3`) | Date, times and clinic read correctly in the probe and both card runs | [Image probe](docs/LIVE_EVIDENCE.md#probe-result-image-input-2026-10-29) |
| Card contradiction blocked | Ended `needs_input`; only the card check failed ("Card date 2026-11-02 differs from request date 2026-11-03"); approval refused | `run_bc6f1284…` |
| Meta speech-to-text (`muse-voice-transcribe-1.0`) | All 5 key facts survived; word error rate 2.9% with numbers spelled out (14.7% raw), 2.7–3.2 s per 13 s clip | [Speech probe](docs/LIVE_EVIDENCE.md#probe-result-speech-to-text-2026-10-29) |
| Spoken request through the full review | Ended `awaiting_signoff`; the memo quotes Meta's transcript | `run_1f9f0992…` |
| Console **Record** button with a real microphone | Meta transcribed the owner's voice on the hosted console (session `harvey-28562413d62d`, 17.0 s, about $0.0008) | [Hosted console](docs/LIVE_EVIDENCE.md#hosted-console-2026-10-29) |
| Spoken request with a real microphone through a full review | Hosted console: Meta transcript confirmed by the reviewer; 27 live turns; all 7 checks pass; memo quotes the transcript; signed off | [`run_0e228025…`](docs/evidence/hosted-console-2026-10-29/README.md) |
| Spending | 66 paid batch calls; about $0.20 at cached-input prices ($0.59 on a deliberately high basis), against a $5 cap enforced before every call | [Batch report](docs/evidence/live-batch-2026-10-29/batch_report.json) |

The complete run records are in [`docs/evidence/live-batch-2026-10-29/`](docs/evidence/live-batch-2026-10-29/README.md). They contain every receipt, tool call, observation, fact, check and memo, along with audit fingerprints that can be recomputed.

**Hosted console:** a password-protected copy runs on Modal at `https://williebee615--harvey-healthcare-review-console.us-east.modal.run` (sign-in shared privately with reviewers). It was last deployed from `main` at `fc49119` (PR #8, the live/simulation, curb and sign-off labels) on 2026-10-29, according to the owner's deploy output; 143 tests passed on the deploying machine at that commit. Changes merged after that, including session reliability and the spoken date/time check, need a redeploy (pending owner approval) before they appear there.

## How it meets the judging criteria

| Criterion | What this project shows |
|---|---|
| **Impact (30%)** | Missed medical appointments often come down to transport details: the wrong day, no wheelchair-capable vehicle, no way home. A voice-first intake helps riders who find apps hard to use, and the review catches contradictions before a car is sent. Built by the founder of a Nashville taxi company as a contest prototype. Benefits such as fewer missed appointments are pilot hypotheses, not measured results. |
| **Meta AI tooling (25%)** | Three Meta capabilities working together: Muse Voice Transcribe for the rider's voice, Muse Spark image understanding for the appointment card, and Muse Spark agentic tool-calling for the investigation. Each is verified live with response IDs. |
| **Technical execution (20%)** | The model interprets; code decides. Exact-quote citations, independent checks it cannot override, contradictions that force `needs_input`, a human gate, an audit-integrity check on every final state, a server-held Meta transcript, a spending cap, and 163 offline tests including prompt-injection, model-failure, console-label and spoken date/time cases. |
| **Demo (25%)** | One spoken request, one card read by Meta, independent checks shown in the console, a human sign-off, then a deliberately contradictory card that is blocked. See [docs/DEMO.md](docs/DEMO.md). |

## Run it

Python 3.10+ is enough; the core has no third-party dependencies.

```bash
./helper test     # 163 offline tests; no keys, no paid calls
./helper serve    # console at http://127.0.0.1:8765
```

Offline simulation needs no key and is labeled as scripted everywhere. For live Meta, create a local `.env` (never commit it):

```dotenv
MODEL_API_KEY=replace_locally_with_your_key
MODEL_API_MODEL=muse-spark-1.3
```

Credentials are only ever sent to `https://api.meta.ai/v1`, and redirects are refused. Every live call is paid; use fictional data only.

| Command | What it does | Paid Meta calls |
|---|---|---|
| `./helper probe --no-image` | Lists the models your key can use | 0 |
| `./helper probe` | Reads the fictional appointment card once | 1 |
| `./helper probe-speech` | Transcribes the fictional 13 s clip once | 1 |
| `./helper run --case healthcare-appointment-card --mode live --turns 30` | Full live review of the card case | about 10–30 |
| `./helper run --case healthcare-clinic-visit --mode live --spoken-audio cases/demo-spoken-request/spoken_request.wav` | Meta transcription, then a full live review | 1 + about 10–30 |
| `./helper live-batch --cap 5` | The verified batch: four scenarios with acceptance checks and a spending cap | about 27–79 |

Runs can be paused, resumed (`./helper resume --run-id …`), inspected (`./helper show`) and acknowledged (`./helper approve --run-id … --signature 'Name'`). Approval re-checks the current evidence and never dispatches.

## Cases

| Case | Expected result | Why |
|---|---|---|
| `healthcare-appointment-card` | `awaiting_signoff` | Card agrees with the booking |
| `healthcare-card-contradiction` | `needs_input` | Card says Nov 2; booking says Nov 3 |
| `healthcare-clinic-visit` | `awaiting_signoff` | Complete trip, vehicle, fare and return plan |
| `healthcare-missing-return-plan` | `needs_input` | No return coordination |
| `healthcare-clinical-support` | `needs_input` | Outside transportation-only scope |
| `harvey-taxi-unsafe-curb-boarding` | `needs_input` | Selected bay fails the demo clearance rule |
| `harvey-taxi-wrong-fare-drift` | `needs_input` | Quote includes a forbidden accessibility surcharge |
| `harvey-taxi-contradictory-evidence` | `needs_input` | Override note conflicts with the evidence |
| `harvey-taxi-incomplete-intake` | `needs_input` | Pickup and time missing |

## Safety and privacy boundaries

- **Credentials stay on the server.** The browser receives only `key_configured: true/false`. Transcription goes through the console's server.
- **Evidence is never instructions.** Documents, transcripts and follow-ups are untrusted. A transcript that tries to bypass review fails the spoken-request check. Spoken dates and times are read by code, not the model: a date or time that disagrees with the booking or card, or one that can't be pinned down ("Monday", "tomorrow", "11/2", "around nine", another time zone, an unlabeled time), stops the review at `needs_input` and asks the rider to clarify. A date spoken without a year takes the booking's year; see [VERIFICATION.md](VERIFICATION.md). No tool exists for approval, dispatch or payment.
- **No silent fallback.** Model or network errors pause the run. A run is labeled live only after a successful Meta response.
- **Headline labels.** A run shows **LIVE META INFERENCE — N RECORDED RESPONSES** only after Meta has answered (response IDs are recorded, not authenticated with Meta), or **OFFLINE SIMULATION — NO META API CALLS**. Curb data is labeled **SIMULATED CURB MEASUREMENTS**, and a sign-off shows **HUMAN ACKNOWLEDGMENT RECORDED — No vehicle dispatched** (stored as `DEMO_HUMAN_SIGNOFF_NO_DISPATCH`; runs signed earlier keep `SIMULATED_DISPATCHER_SIGNOFF`). The console remembers the chosen mode, labels the Start button with paid API calls in live mode, and never starts a review on its own.
- **Provenance per result.** The console's *Where each result came from* panel separates live Meta reasoning, the source of the spoken request, who read the appointment card, and the curb measurements. Curb measurements are always a simulated fixture, even in a live Meta run. `LIVE_META_API` describes the reasoning only.
- **Audit integrity.** When a run reaches `needs_input`, `awaiting_signoff` or sign-off, the app checks that its record is consistent: one receipt per model turn, verbatim quotes against unchanged evidence, no memo on a blocked run, dispatch off, and sign-off fields matching the state. It is a record check, not a booking approval. It confirms that a Meta response ID was recorded for every model turn; it does not query Meta to authenticate those IDs.
- **Local by default.** The console binds to loopback and checks host, origin, a session token and request sizes. An optional password-protected Modal deployment is described in [docs/MODAL.md](docs/MODAL.md); it is not deployed for this submission.
- **Fictional data only.** While free credits are in use, Meta's dashboard notes that content may be used for product improvement. No real patient or rider data belongs in this prototype. No HIPAA compliance is claimed.

## Completed vs future work

| Completed and tested | Future development, not built |
|---|---|
| Meta speech-to-text intake with rider confirmation | Phone-call (IVR) intake; Meta realtime streaming |
| Card image reading with code cross-checks | Other documents (discharge papers, insurance cards) |
| Muse Spark investigation with exact citations | Spoken requests in other languages |
| Code cross-check of spoken dates and times against the booking and card | Resolving relative dates ("tomorrow", "next Friday") automatically; today they ask the rider to confirm |
| Deterministic fare, $0 accessibility fee, curb rule | SAM 3.1 curb analysis (model available, not integrated); calibrated measurements |
| Human sign-off gate; contradiction blocking | Real dispatch, payments, staff identity, EHR or clinic integrations |
| Live verification batch with spending cap | Clinic pilot with consent, privacy agreements and outcome measurement |

## More detail

- [docs/LIVE_EVIDENCE.md](docs/LIVE_EVIDENCE.md): every live result, with prices and costs
- [docs/LIVE_BATCH_PLAN.md](docs/LIVE_BATCH_PLAN.md): batch plan, cap and acceptance criteria
- [VERIFICATION.md](VERIFICATION.md): the invariants the tests enforce
- [SUBMISSION.md](SUBMISSION.md) and [docs/DEMO.md](docs/DEMO.md): submission text and 3-minute script

A historical Fireworks receipt from before this version is kept in [`archive/`](archive/README.md) as provenance only; it is not evidence of current inference.
