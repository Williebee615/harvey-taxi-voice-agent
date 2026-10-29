# Harvey Taxi — Accessible Voice-Booking & Verification Agent

## Submission status (2026-10-29)

| Item | Status |
|---|---|
| Source | https://github.com/Williebee615/harvey-taxi-voice-agent, branch `main`. PRs #4–#8 merged 2026-10-29; later fixes arrive by pull request with owner approval |
| Hosted console | https://williebee615--harvey-healthcare-review-console.us-east.modal.run. Password-protected (username `reviewer`; password shared privately). Deployed from `main` at `fc49119` (PR #8) on 2026-10-29, per the owner's deploy output |
| Live Meta evidence | Complete: [docs/LIVE_EVIDENCE.md](docs/LIVE_EVIDENCE.md), [docs/evidence/live-batch-2026-10-29/](docs/evidence/live-batch-2026-10-29/README.md) |
| Three-minute video | **Not recorded yet.** Script: [docs/DEMO.md](docs/DEMO.md) |
| Event form | **Not submitted yet** |
| Track and theme | Startup track · Build for Your World. Confirm in the event platform |
| Representative | Willie Harvey IV, Harvey Taxi Service LLC. Confirm team members against the registration |
| Deadline | November 4, 2026, 9 PM Eastern, per the participant guide supplied. Check organizer announcements |

## Short description

Harvey Taxi turns a spoken ride request and a photo of an appointment card into a verified, human-approved booking for an accessible trip to a healthcare appointment. Meta's speech-to-text transcribes the rider, Muse Spark reads the card and investigates the booking, and deterministic checks validate the fare, the accessibility rules and every cited fact. Contradictions are blocked, and nothing proceeds without a person's sign-off.

## Problem and impact (Impact, 30%)

For a wheelchair user, getting to a clinic depends on details that are easy to get wrong: the date, the arrival time, a vehicle with a ramp, a fair price, a way home. A booking for the wrong day is as bad as no booking. Harvey Taxi Service operates in Nashville and sees these failures firsthand.

This prototype lets the rider simply say what they need, reads the appointment card they already have, and refuses to move forward when the evidence disagrees. That is the right default when the alternative is a missed appointment.

Demonstrated: fictional cases where the system books a consistent trip and blocks a contradictory one. **Not yet measured:** reduced coordinator time, better rider experience and fewer missed appointments. Those are goals for a future clinic pilot.

## How Meta's models are used (Meta AI tooling, 25%)

| Meta model | Role | Verified live |
|---|---|---|
| `muse-voice-transcribe-1.0` | Transcribes the rider's spoken request (file endpoint) | Yes: probe and one full spoken-request run; all key facts preserved |
| `muse-spark-1.3`, image understanding | Reads the appointment card image: date, appointment time, arrive-by time, clinic | Yes: probe and two full card runs, all fields correct |
| `muse-spark-1.3`, agentic tool calling | Chooses each investigation step, records exact quotations, requests evidence and writes the cited memo | Yes: 65 live turns, a response ID for each |

Models available but **not** used: `sam-3.1` (curb segmentation is future work), `muse-wonder-1.0`, and the contributor-mode variants.

## Engineering (Technical execution, 20%)

- **The model interprets; code decides.** The model reads and cites. Independent checks it cannot override decide the outcome: intake, tariff quote, fare arithmetic, a $0 accessibility fee, curb bay, counter-evidence, healthcare transport fields, card fields against the booking, and spoken needs against the intake.
- **Four review stages, enforced.** List documents, set the checklist, analyze documents, submit a memo. A memo is accepted only after independent verification of the current evidence, with an exact-quote citation for every checklist item.
- **Contradictions force `needs_input`.** Success stops at `awaiting_signoff`, and only a named human can acknowledge it. Acknowledgment never dispatches.
- **Honest provenance.** A run is labeled live only after Meta answers. The Meta transcript is held on the server, so the browser cannot relabel edited text as Meta. Every turn keeps its response ID, token usage and latency.
- **Security.** The API key stays on the server and is sent only to `api.meta.ai`. Remote error bodies are hidden. The console checks host, origin, token, content type and size.
- **Unmistakable labels.** Each run is headed **LIVE META INFERENCE — N RECORDED RESPONSES** or **OFFLINE SIMULATION — NO META API CALLS**; curb data says **SIMULATED CURB MEASUREMENTS**; a sign-off says **HUMAN ACKNOWLEDGMENT RECORDED — No vehicle dispatched**.
- **Audit integrity and provenance.** Every final state, including a correct `needs_input` stop, gets an integrity check of the record itself. The console shows separately where the reasoning, spoken request, card reading and curb measurements came from.
- **Testing.** 143 offline tests, including prompt injection in documents, transcripts and follow-ups; model failure and resume; unsupported audio; the spending cap; both sign-off labels; and a headless-browser check of the console labels and remembered mode.

## Verified live results (Demo, 25%)

Owner-approved batch, 2026-10-29, $5 cap checked before every call:

| Scenario | Final state | Checks | Meta calls |
|---|---|---|---|
| Appointment card | `awaiting_signoff` | All independent checks pass; the memo cites the card image | 22 |
| Card contradiction | `needs_input` | Only the card check fails, on the date difference; approval refused | 24 |
| Spoken request (Meta speech-to-text) | `awaiting_signoff` | Spoken-request and all other checks pass; the memo quotes the transcript | 1 + 19 |
| Authentication failure | paused, no network | Never labeled live; no receipts | 0 |

Total: 66 paid calls, about $0.20 at cached-input prices ($0.59 on a deliberately high basis). Every record was independently re-verified against the case files, and the audit fingerprints are published.

## Work developed for this entry

During the event: live Meta orchestration and verification gates, exact citations, resumable audits, the connected console and healthcare cases (October 27–28); then the appointment-card image evidence, Meta speech-to-text intake, the inference receipts panel, the capped live batch and the preserved evidence (October 29). The pull request and dated commits show the contribution boundary. The earlier Harvey Taxi business, workshop starter concepts and a historical Fireworks receipt are not presented as new work.

## Boundaries

- Fictional riders, clinics and appointments; simulated curb measurements; a demo fleet clearance rule that is not a legal standard.
- No clinical advice, medical clearance, emergency service, dispatch, payment, EHR integration or production deployment. No HIPAA compliance is claimed.
- The Record button has been used live with a real microphone on the hosted console (2026-10-29, one transcription). The scripted demo takes are still to be recorded.
- Spoken dates and times are not yet cross-checked by code (accessibility needs are).
- Meta response IDs are recorded by the application from Meta's responses and checked for presence and uniqueness. They have not been independently authenticated with Meta or by a third party.

## How judges can run it

```bash
./helper test
./helper serve
```

Open http://127.0.0.1:8765. Offline simulation needs no key. Live Meta needs the judge's own `MODEL_API_KEY` in a local `.env`. The published evidence can be checked without any key; see [docs/evidence/live-batch-2026-10-29/README.md](docs/evidence/live-batch-2026-10-29/README.md).
