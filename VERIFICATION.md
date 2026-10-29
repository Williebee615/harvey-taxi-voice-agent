# Verification contract

Run `./helper test`. All automated tests are offline and use temporary case/run directories. A fake Responses transport tests agent orchestration; it does not demonstrate actual Meta availability or response quality.

## Required invariants

- Simulation never makes model calls or receives a live label.
- Live credentials are sent only to Meta's fixed HTTPS endpoint; no cross-provider key reuse, redirect or silent fallback.
- Unknown case names, path traversal, symlink cases and arbitrary static file access are refused.
- Missing rider, journey, time, mileage, quote, policy or curb evidence is never filled with convenient defaults.
- Fare uses decimal currency rounding; NaN, infinity, booleans and negative mileage fail.
- Source quotations must occur exactly in actual case files. There is no permissive length-based quote verification.
- Every memo finding cites facts tied to its own checklist item and the current source digest. Intake, policy and telemetry citations are required.
- A memo cannot bypass independent booking checks. Unresolved gaps lead to `needs_input`.
- Clinical-support requests and incomplete healthcare transport coordination lead to human follow-up; the application does not determine medical suitability.
- Approval requires `awaiting_signoff`, a reviewer, an accepted memo, unchanged evidence and freshly passing checks. It never enables actual dispatch.
- Model transcripts, tool observations and request/usage metadata are persisted per unique run. Follow-up keeps the run ID; no-work resumes make zero calls.
- Host, Origin, body bounds, content type, mutation token and server concurrency are checked.
- Appointment-card fields come only from a card image viewed in the run. Code cross-checks them against the rider request; a contradiction, missing or unreadable field, or a changed image blocks the memo and approval.
- Images are never quoted as text, never exceed 2 MB, and are never stored in public observations.
- A spoken request is run-scoped, untrusted evidence. Its accessibility needs must appear in the intake, bypass instructions fail the check, and the memo must quote it.
- Injected instructions in documents, transcripts or follow-ups cannot unlock tools: there is no approval, dispatch or payment tool.
- The accessibility surcharge is always $0.00; any positive wheelchair, ADA or service-animal fee fails the fare check.
- A failed model call pauses the run; a run is labeled live only after a successful Meta response.
- Every final state (`needs_input`, `awaiting_signoff`, signed off) records an audit-integrity verdict. It covers receipts per model turn, live or simulation provenance, the declared simulated curb source, verbatim facts against unchanged evidence, no memo on a blocked run, dispatch off, and sign-off fields matching the state. It is a record check, not a booking approval. It confirms that a Meta response ID was recorded for every model turn; it does not query Meta to authenticate those IDs. Paused runs stay "Not verified yet".

## Manual live acceptance (on the configured Mac)

1. `./helper validate-models`: verify a real response ID, configured model and usage.
2. `./helper run --case healthcare-clinic-visit --mode live --turns 20`.
3. Verify tools are chosen by the model, actual function outputs are replayed and a cited memo reaches `awaiting_signoff`.
4. Run the missing-return, unsafe-curb, appointment-card and card-contradiction cases live; verify escalation. Tool selection can vary, but independent gates must remain unchanged.
5. Disconnect network or use an invalid local key; verify an explicit pause and no synthetic success.
6. Reopen a saved run and continue after a deliberate turn pause; sign off only after reviewing evidence.

The separate connection probe previously succeeded on the user's Mac. This repository upgrade still requires the integrated live acceptance above. Meta speech recognition, SAM image segmentation, calibrated clearance and real healthcare interoperability are not implemented. Muse Spark image input is implemented but awaits live verification; see docs/LIVE_EVIDENCE.md.
