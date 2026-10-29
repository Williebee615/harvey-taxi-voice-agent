# Three-minute contest video

## Before recording

1. Complete [the live test plan](LIVE_EVIDENCE.md). The card segment may be shown as live Meta reading **only if** the image probe passed and the live card runs behaved as expected. If not, see "If image input is not verified" below.
2. Start the console: `./helper serve`, then open http://127.0.0.1:8765 in Chrome (the browser speech recognition used here works there).
3. Close unrelated tabs. Never show `.env`, keys, billing pages or personal files.

## Labeling rules

- A newly recorded live run may be shown as live. If you cut waiting time, label the cut **Waiting shortened**.
- A reopened saved run must be labeled **Saved live Meta run**.
- Never show an offline simulation and call it Meta inference. The receipts panel says "Offline simulation" for those runs; keep it visible.
- Say that speech recognition is the browser's, not Meta's.

Aim for 2:50–2:58 so the exported file stays under three minutes.

## Timed script

| Time | Screen | Narration |
|---|---|---|
| 0:00–0:20 | Console home, Appointment card case selected, card visible. | "I'm Willie Harvey, founder of Harvey Taxi. For a wheelchair user, a ride to the doctor depends on details that are easy to get wrong: the date, the arrival time, the right vehicle, a fair price. Harvey Taxi checks those details before anyone is booked." |
| 0:20–0:40 | Click **Speak request** and say: "I need a wheelchair-accessible ride with my service dog to my clinic appointment on Monday." Choose **Live Meta**, start the review. | "The rider can simply say what they need. Speech-to-text here is the browser's own recognition, not Meta. The transcript becomes evidence, not an instruction." |
| 0:40–1:15 | Expand the **analyze documents** step, then **record document fields**. Point at the receipts panel. | "Meta's Muse Spark runs the review. It chooses each step itself: it reads the policy and the request, then looks at the appointment card image and records the date, the appointment time, the arrive-by time and the clinic. Every step here has a real Meta response ID and token count." |
| 1:15–1:45 | Verification panel: card check, spoken request check, fare check. Fare rule box. | "Then code, not the model, checks the work. The card must agree with the booking. The service dog and wheelchair the rider mentioned must be on the intake. The fare is computed: two fifty plus a dollar fifty a mile, and zero dollars for accessibility, always." |
| 1:45–2:05 | Memo with citations; enter reviewer name; record demo sign-off. | "The memo cites its sources, exact quotes and the card fields, and stops for a human. Sign-off is a demo acknowledgment; nothing is dispatched or charged." |
| 2:05–2:40 | Select **Card contradiction**, run live (or open the saved run, labeled). Show the failed card check and `needs input`. | "Now the written booking says Tuesday, but the card says Monday. A plausible booking for the wrong day is exactly how someone misses an appointment. The card check fails, the review stops at needs input, and sign-off is blocked until a person resolves it." |
| 2:40–2:58 | Return to the receipts panel, then the repository. | "Meta reads the evidence; deterministic checks decide what is safe to book; a human stays in control. This is transportation coordination, not medical advice, and every case here is fictional." |

## If image input is not verified

Do not narrate 0:40–1:15 as Meta reading the card. Either:
- leave the card out and run the spoken-request clinic case live, showing the contradiction with the **Missing return plan** case instead; or
- show the card cases in **offline simulation**, with the receipts panel visible, and say: "In this offline simulation the card values are scripted; live image reading is still being verified."

## Final checks

- Duration at most three minutes; narration audible.
- Live, saved and simulated segments correctly labeled; browser speech identified as not Meta.
- Both the successful review and the blocked contradiction are shown.
- The video link opens in a signed-out browser.
- Paste the final link into `SUBMISSION.md` and the official submission form.

No patient-outcome, live-dispatch, clinical-clearance, HIPAA or production-readiness claim is made by this video.
