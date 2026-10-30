# Harvey Taxi — Accessible Voice-Booking & Verification Agent

## Submission status (updated 2026-10-30 UTC)

| Item | Status |
|---|---|
| Source | https://github.com/Williebee615/harvey-taxi-voice-agent, branch `main`. Every change arrives by pull request with the owner's approval; the merge history is the record |
| Hosted console | https://williebee615--harvey-healthcare-review-console.us-east.modal.run. Password-protected (username `reviewer`; password shared privately). Deployed from `main` at `fc49119` (PR #8) on 2026-10-29, per the owner's deploy output. Session reliability and the spoken date/time check were merged later and **are not on the hosted console until a redeploy, which is pending owner approval** |
| Live Meta evidence | Complete: [docs/LIVE_EVIDENCE.md](docs/LIVE_EVIDENCE.md), [docs/evidence/live-batch-2026-10-29/](docs/evidence/live-batch-2026-10-29/README.md) |
| Three-minute video | **Not recorded yet.** Script: [docs/DEMO.md](docs/DEMO.md) |
| Event form | **Unresolved: records conflict.** On 2026-10-29 the owner referred to "the submitted Modal console"; this file previously said "not submitted yet". The portal ([submit page](https://cerebralvalley.ai/e/meta-ai-developer-hackathon/hackathon/submit)) can't be reached from the development environment. The owner should confirm the submission date, the links entered, and whether edits are allowed |
| Submitted version | Every commit on `main` is kept and none has been rewritten. Once the owner confirms when the form was submitted, the `main` commit current at that time will be tagged (candidates: `c7c1f1a`, which was `main` at 10:11 UTC on 2026-10-29 when the owner first called the console submitted; the later deployments `778b740` and `fc49119`) |
| Track and theme | Startup track · Build for Your World. Confirm in the event platform |
| Representative | Willie Harvey IV, Harvey Taxi Service LLC. Confirm team members against the registration |
| Deadline | November 4, 2026, 9 PM Eastern, per the participant guide supplied. Check organizer announcements |

## Short description

A contest prototype, built by the founder of Harvey Taxi Service LLC, that turns a spoken ride request and a photo of an appointment card into a verified, human-approved booking for an accessible trip to a healthcare appointment. Meta's speech-to-text transcribes the rider, Muse Spark reads the card and investigates the booking, and deterministic checks validate the fare, the accessibility rules and every cited fact. Contradictions are blocked, and nothing proceeds without a person's sign-off.

## Problem and impact (Impact, 30%)

For a wheelchair user, getting to a clinic depends on details that are easy to get wrong: the date, the arrival time, a vehicle with a ramp, a fair price, a way home. A booking for the wrong day is as bad as no booking.

This prototype was built for the hackathon by Willie Harvey IV, founder of Harvey Taxi Service LLC in Nashville. The problem framing reflects the founder's view of accessible transportation; it is not a measured study. No operating scale, rider volume or production use is claimed for this prototype.

This prototype lets the rider simply say what they need, reads the appointment card they already have, and refuses to move forward when the evidence disagrees. That is the right default when the alternative is a missed appointment.

Demonstrated: fictional cases where the system books a consistent trip and blocks a contradictory one. **Not yet measured:** reduced coordinator time, better rider experience and fewer missed appointments. Those are goals for a future clinic pilot.

## How Meta's models are used (Meta AI tooling, 25%)

Three Meta capabilities work in sequence on one booking. Each has its own job, and code checks each one's output.

| Meta capability | What it does here | How it is wired | Verified live |
|---|---|---|---|
| **Muse Voice Transcribe** (`muse-voice-transcribe-1.0`) | Turns the rider's spoken request into text | The browser records only after the rider clicks Record and sends 16 kHz WAV to the console's own server. That server calls Meta's file transcription endpoint with the key it holds, keeps the transcript server-side, and uses it only after the rider confirms it. Edited text is relabeled as typed, not Meta | Yes: probe (word error rate 2.9% with numbers spelled out), one batch run, and one real-microphone run on the hosted console |
| **Muse Spark image understanding** (`muse-spark-1.3`) | Reads the appointment card photo: date, appointment time, arrive-by time, clinic | When the model asks to analyze the card, the image goes back to it as `input_image`. The model records the fields with a dedicated tool, and code compares them with the booking | Yes: probe plus two full card runs, all fields correct |
| **Muse Spark agentic tool calling** (`muse-spark-1.3`, Responses API) | Runs the investigation | Nine custom function tools that our code executes: list and analyze documents, set a checklist, update the plan, record exact quotes, record card fields, verify the booking, request evidence, submit the memo. Exactly one tool per turn. Each result, including refusals such as "Quote must occur exactly in a source document", returns to the model as `function_call_output`. Meta's encrypted reasoning is carried between turns (`include: reasoning.encrypted_content`, `store: false`) | Yes: 65 batch turns plus 51 hosted-console turns, each with a recorded Meta response ID |

**What the model decides and what code decides.** In a live run Muse Spark chooses every tool and its arguments: which documents to read, what to check, what to quote, and when to verify, ask for evidence or submit. Code decides the outcome: fare arithmetic and the $0 accessibility fee, the curb rule, intake completeness, card and spoken-request cross-checks, exact-quote citations, `needs_input` versus `awaiting_signoff`, and the human sign-off. The model can't override a failed check. When it tries, the refusal goes back to it, and the run stops for a person.

**Not used:** `sam-3.1` (curb segmentation is future work), Meta's built-in `web_search`, Muse Image, `muse-wonder-1.0` and the contributor-mode variants. The dashboard counters for images, segmentation and web searches are therefore expected to read zero for this application. We did not add those tools just to raise usage.

### Live evidence, offline demonstrations and simulated data

| Kind | What it covers | Where |
|---|---|---|
| **Live Meta evidence** (paid calls with recorded response IDs) | Image and speech probes; the capped batch (card success, card contradiction, spoken request, authentication failure); two hosted-console runs, one with the owner's real microphone | [docs/LIVE_EVIDENCE.md](docs/LIVE_EVIDENCE.md), [docs/evidence/](docs/evidence/live-batch-2026-10-29/README.md) |
| **Offline demonstrations** (no network; Meta replaced by a scripted stand-in or a fixed script; the real tools and checks run) | Wrong fare, unmatched accessibility need and invented quotes blocked (`audit/safeguards_demo.py`); the spoken date/time check (`tests/test_spoken_schedule.py`, including Meta's real 2026-10-29 transcript); all regression tests; the console's **OFFLINE SIMULATION — NO META API CALLS** mode | [docs/AUDIT_2026-10-30.md](docs/AUDIT_2026-10-30.md), `./helper test` |
| **Simulated data** (fixtures, never measured) | Curb clearance and bay status, in every run, including live ones. Labeled **SIMULATED CURB MEASUREMENTS — Demonstration data, not camera measurements**. No camera, SAM or other model measured them. All riders, clinics, cards and appointments are fictional | `cases/*/inbox/curb_telemetry.json` |

A run labeled `LIVE_META_API` means the reasoning was live; the curb data in that same run is still simulated.

## Engineering (Technical execution, 20%)

- **The model interprets; code decides.** The model reads and cites. Independent checks it cannot override decide the outcome: intake, tariff quote, fare arithmetic, a $0 accessibility fee, curb bay, counter-evidence, healthcare transport fields, card fields against the booking, spoken needs against the intake, and spoken dates and times against the booking and the card (conflicting or ambiguous speech asks the rider to clarify).
- **Four review stages, enforced.** List documents, set the checklist, analyze documents, submit a memo. A memo is accepted only after independent verification of the current evidence, with an exact-quote citation for every checklist item.
- **Contradictions force `needs_input`.** Success stops at `awaiting_signoff`, and only a named human can acknowledge it. Acknowledgment never dispatches.
- **Honest provenance.** A run is labeled live only after Meta answers. The Meta transcript is held on the server, so the browser cannot relabel edited text as Meta. Every turn keeps its response ID, token usage and latency.
- **Security.** The API key stays on the server and is sent only to `api.meta.ai`. Remote error bodies are hidden. The console checks host, origin, token, content type and size.
- **Unmistakable labels.** Each run is headed **LIVE META INFERENCE — N RECORDED RESPONSES** or **OFFLINE SIMULATION — NO META API CALLS**; curb data says **SIMULATED CURB MEASUREMENTS**; a sign-off says **HUMAN ACKNOWLEDGMENT RECORDED — No vehicle dispatched**.
- **Audit integrity and provenance.** Every final state, including a correct `needs_input` stop, gets an integrity check of the record itself. The console shows separately where the reasoning, spoken request, card reading and curb measurements came from.
- **Session reliability.** The hosted console stays up through 15 idle minutes. Its page token survives a restart and changes when the password changes. A stale page is told "The review was not started; no Meta call was made" and is never retried automatically. Sign-in and origin checks are unchanged.
- **Testing.** 163 offline tests on `main`, run in CI on every pull request. They cover prompt injection in documents, transcripts and follow-ups; model failure and resume; unsupported audio; the spending cap; both sign-off labels; spoken dates and times (year boundaries, time zones, noon and midnight, vague phrasing); session expiry, restart and password rotation; and a headless-browser check of the console labels and remembered mode.

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
- Spoken dates and times are checked only in the supported forms; relative days ("tomorrow") and vague times are never guessed: they ask the rider to confirm. No live Meta run has exercised the spoken date/time check yet; it is verified offline, including against Meta's real transcript from 2026-10-29.
- This is a contest prototype. Nothing here has been used with real riders, and no production readiness is claimed.
- Meta response IDs are recorded by the application from Meta's responses and checked for presence and uniqueness. They have not been independently authenticated with Meta or by a third party.

## How judges can run it

```bash
./helper test
./helper serve
```

Open http://127.0.0.1:8765. Offline simulation needs no key. Live Meta needs the judge's own `MODEL_API_KEY` in a local `.env`. The published evidence can be checked without any key; see [docs/evidence/live-batch-2026-10-29/README.md](docs/evidence/live-batch-2026-10-29/README.md).
