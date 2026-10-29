# Three-minute demonstration

## Before recording

1. Open the hosted console (https://williebee615--harvey-healthcare-review-console.us-east.modal.run) in Chrome and sign in as `reviewer`. Allow the microphone when asked. The real-microphone path was verified there on 2026-10-29. Alternatively, run it locally with `./helper serve` in a terminal where your Meta key is set.
2. Close unrelated tabs. Never show `.env`, keys, billing pages, saved passwords or personal files.
3. Choose **Live Meta** in the console. A full live review costs about $0.10–$0.30; the transcription costs less than a cent.
4. Do one quiet rehearsal of the spoken request so the microphone level is right.
5. Uncheck **Step through one tool at a time** so each review runs straight through (about 20–45 seconds).

**Budget:** recording this demo needs new paid calls (two live reviews and one transcription, about $0.30–$0.60). Get the owner's approval for that spend first. If live recording isn't possible, use the saved live runs from 2026-10-29 and label them (see "Labeling rules").

## Labeling rules

- A new live run can be shown as live. If you cut waiting time, add the caption **Waiting shortened**.
- A reopened saved run must carry the caption **Saved live Meta run (2026-10-29)**.
- Never show offline simulation as Meta inference. The receipts panel says "Offline simulation" for those runs; keep it visible.
- Keep under three minutes. Aim for 2:50.

## Script

| Time | On screen | Say |
|---|---|---|
| 0:00–0:15 | Console home. | "I'm Willie Harvey, founder of Harvey Taxi in Nashville. For a wheelchair user, getting to the doctor depends on details that are easy to get wrong: the day, the arrival time, a ramp, a fair price. Here's how we check them before anyone is booked." |
| 0:15–0:40 | Click **Appointment card**; the card appears. Click **Record with Meta speech-to-text**; the red recording indicator shows. Say: *"I need a wheelchair-accessible ride with my service dog to Demo Community Clinic on Monday, November second. I need to arrive by nine forty-five."* Click **Stop and transcribe**. | "The rider just says what they need. Nothing is recorded until they press the button. The audio goes through our server to Meta's speech-to-text model, so the key never touches the browser." |
| 0:40–0:55 | The transcript appears with "Transcribed by Meta muse-voice-transcribe-1.0". Tick **This Meta transcript matches what I said**. | "Meta transcribed it in about three seconds. The rider confirms it, and if they edit it, it's labeled as typed text, not Meta." |
| 0:55–1:30 | Click **Start review**. Point at the activity list, then expand **analyze documents** and **record document fields**. Point at the receipts panel and the *Where each result came from* panel (live Meta reasoning; curb measurements simulated). | "Now Meta's Muse Spark runs the review and chooses every step itself. Here it looks at the appointment card and records the date, the times and the clinic. Every step has a real Meta response ID and token count." |
| 1:30–2:00 | Independent verification panel: card check, spoken request check, fare check. Point at the fare policy box. | "Then code, not the model, decides. The card has to agree with the booking. The wheelchair and service dog the rider mentioned have to be on the intake. The fare is computed: two fifty plus a dollar fifty a mile, and zero dollars for accessibility. Always." |
| 2:00–2:15 | Memo with citations; type a reviewer name; click **Record demo sign-off**. | "The memo cites its sources and stops for a person. Sign-off is a human decision; nothing is dispatched or charged." |
| 2:15–2:45 | Click **Card contradiction**, start a live review (or open the saved run, captioned). Show the failed card check and **needs input**. | "Now the booking says Tuesday, but the card says Monday. That's exactly how someone misses an appointment. The card check fails, the review stops at needs input, and sign-off is blocked until a person fixes it." |
| 2:45–2:58 | Receipts panel, then the repository's evidence folder. | "Meta listens and reads. Our code verifies. A person decides. Every case here is fictional, and every live result is published with its Meta receipts." |

## If something fails during recording

- **Microphone or transcription error:** type the request instead and say "typed request" on camera. Don't present typed text as Meta speech.
- **A live review pauses on an API error:** stop. Use the saved live runs, captioned. Don't retry repeatedly without budget approval.
- **The live card run doesn't reach `awaiting_signoff`:** keep it on camera if it is still honest and clear, or use the saved run, captioned.

## Final checks

- Under three minutes; narration clear.
- Live, saved and typed segments captioned correctly.
- Both the successful review and the blocked contradiction are shown.
- No keys, billing pages, saved passwords or personal data on screen.
- The video link opens in a signed-out browser. Paste it into `SUBMISSION.md` and the event form.

No clinical, dispatch, HIPAA or production-readiness claim is made in this video.
