# Three-minute demonstration

Updated 2026-10-30 UTC. The script below shows the console as it will be **after PRs #11 (session reliability) and #12 (spoken date/time checks) are merged and the hosted console is redeployed**. Each of those steps needs the owner's approval. Until then, see "If #11 and #12 aren't deployed yet".

## What the video must show (judging criteria)

| Criterion | Shown by |
|---|---|
| Impact (30%) | A wheelchair user's clinic trip: wrong day, arrival time, ramp, fair fare, way home. Built by an operating Nashville taxi company |
| Meta AI tooling (25%) | Meta speech-to-text on a real voice, Muse Spark reading the card image, and Muse Spark choosing every investigation step, with response IDs on screen |
| Technical depth (20%) | Code, not the model, checks the card, the spoken needs, the spoken date and time, and the fare. A contradiction is blocked |
| Demo (25%) | One live successful review with sign-off, then one live blocked contradiction, under three minutes |

## Recording checklist

### Owner approvals, before the recording day
- [ ] PR #11 and PR #12 merged, and the hosted console redeployed from that `main`. Record the deployed commit.
- [ ] Paid calls released for the recording. Budget approved on 2026-10-29: about $0.90 in total for demo takes. **Paid calls are on hold as of 2026-10-30**, so confirm before recording.
- [ ] Submission status confirmed in the portal (see SUBMISSION.md), so you know whether the video link can still be added or changed.

### Free rehearsal (no paid calls)
- [ ] Open the console in **Chrome** and sign in as `reviewer`.
- [ ] Select **Offline simulation** and run **Appointment card**, typing the spoken sentence below into the text box. The console should end at awaiting sign-off with the **OFFLINE SIMULATION — NO META API CALLS** label. Never show this as Meta in the video.
- [ ] Run **Card contradiction** in Offline simulation. It should stop at **needs input** with the card check failing.
- [ ] Practise the sentence aloud twice at a steady pace.

### Screen and browser
- [ ] Close unrelated tabs, notifications, Messages and Mail. Hide the bookmarks bar.
- [ ] Never show `.env`, keys, Modal secrets, billing pages, saved passwords or personal files.
- [ ] Browser zoom so the three panels fit (about 80–90%).
- [ ] **Safari users:** Shift-Command-R turns on Reader, which hides the console's styling. To reload, use Command-R. Press Esc to leave Reader.
- [ ] Allow the microphone when asked, then check the level with one quiet test recording. That test is a paid transcription of under a cent.
- [ ] Untick **Step through one tool at a time**.

### Live takes (paid)
- [ ] Select **Live Meta**. The button reads **Start live Meta review (paid API calls)**.
- [ ] Take 1 and Take 2 as scripted below.
- [ ] After each take, click **Download audit JSON**.
- [ ] Check each take's run ID in **Saved reviews**. It must be new, not `run_0e228025…` or `run_b2023…`.

### After recording
- [ ] Send both JSON files for verification and evidence preservation (PR, owner approval).
- [ ] Trim to under 3:00 (aim for 2:50). Add the captions required by the labeling rules.
- [ ] Upload as unlisted or public, and open the link in a signed-out browser.
- [ ] Put the link in the portal and in SUBMISSION.md (PR).

## Labeling rules

- A new live run can be shown as live. If waiting is cut, caption it **Waiting shortened**.
- A reopened saved run must be captioned **Saved live Meta run (date)**.
- Never show offline simulation as Meta inference. Keep its label visible.
- Curb data is always **SIMULATED CURB MEASUREMENTS**. Never call it measured, and never say SAM analyzed it.
- Typed text is never presented as Meta speech-to-text.

## The spoken sentence (Take 1)

> "Hi, this is Jordan Ellis. I need a wheelchair-accessible ride with my service dog to Demo Community Clinic on Monday, November second. I need to arrive by nine forty-five in the morning."

It matches the fictional booking and card: Monday 2026-11-02, arrive by 09:45, wheelchair and service dog on the intake. Saying a different day or time will (correctly) stop the review. Don't improvise during the take.

## Script

| Time | On screen | Say |
|---|---|---|
| 0:00–0:15 | Console home, **Live Meta** selected. | "I'm Willie Harvey, founder of Harvey Taxi in Nashville. For a wheelchair user, getting to the doctor depends on details that are easy to get wrong: the day, the arrival time, a ramp, a fair price. Here's how we check them before anyone is booked." |
| 0:15–0:40 | Click **Appointment card**; the card appears. Click **Record with Meta speech-to-text**; the red indicator shows. Say the sentence. Click **Stop and transcribe with Meta**. | "The rider just says what they need. Nothing is recorded until they press the button, and the audio goes through our server to Meta's speech-to-text model, so the key never touches the browser." |
| 0:40–0:50 | Transcript appears with "Transcribed by Meta muse-voice-transcribe-1.0". Tick **This Meta transcript matches what I said**. | "Meta transcribed it in about three seconds. The rider confirms it. If they edit it, it's labeled as typed text, not Meta." |
| 0:50–1:25 | Click **Start live Meta review (paid API calls)**. Point at the green **LIVE META INFERENCE — N RECORDED RESPONSES** label and the activity list. Expand **analyze documents**, then **record document fields**. Point at the receipts panel. | "Now Meta's Muse Spark runs the review and chooses every step. It reads the appointment card photo and records the date, the times and the clinic. Every step has a recorded Meta response ID and token count." |
| 1:25–2:00 | Independent verification panel: point at the **appointment card check**, the **spoken request check**, the **spoken schedule check** ("Spoken dates and times agree with the booking and the appointment card"), the **fare check**, and the orange **SIMULATED CURB MEASUREMENTS** label. | "Then code, not the model, decides. The card must agree with the booking. The wheelchair and service dog the rider mentioned must be on the intake. Monday, November second and nine forty-five must match the booking and the card. The fare is computed: two fifty plus a dollar fifty a mile, and zero dollars for accessibility. The curb data here is simulated, and it's labeled that way." |
| 2:00–2:15 | Memo with citations. Type your name and click **Record demo sign-off**. The blue **HUMAN ACKNOWLEDGMENT RECORDED — No vehicle dispatched** label appears. | "The memo cites its sources and stops for a person. Sign-off is a human decision; nothing is dispatched or charged." |
| 2:15–2:45 | Click **Card contradiction** and start a live review (no recording needed). Show the failed **appointment card check** ("Card date 2026-11-02 differs from request date 2026-11-03") and **needs input**. | "Now the booking says Tuesday, November third, but the card says Monday, November second. That's exactly how someone misses an appointment. The card check fails, the review stops at needs input, and sign-off is blocked until a person fixes it." |
| 2:45–2:58 | Receipts panel, then the repository's evidence folder. | "Meta listens and reads. Our code verifies. A person decides. Every case here is fictional, and every live result is published with its Meta receipts." |

## If something fails during recording

- **"The console restarted… Nothing was sent":** click the button again; no charge was made. (This needs #11 deployed.)
- **The page shows plain text without styling (Safari):** you are in Reader. Press Esc.
- **Microphone or transcription error:** type the sentence instead and say "typed request" on camera. Don't present typed text as Meta speech.
- **The spoken schedule check fails:** the transcript differs from the sentence (a wrong day or time). Show it honestly as the safeguard working, or start the take again. A retake costs another review (about $0.10–$0.30).
- **A live review pauses on an API error:** stop. Use the saved live runs, captioned. Don't retry repeatedly without budget approval.

## If #11 and #12 aren't deployed yet

- The **spoken schedule check** row won't appear. Drop "Monday, November second and nine forty-five must match…" from the 1:25–2:00 narration.
- The console stops after 60 idle seconds. Reload with Command-R just before each take, and move from transcription to Start without pausing.

No clinical, dispatch, HIPAA or production-readiness claim is made in this video.
