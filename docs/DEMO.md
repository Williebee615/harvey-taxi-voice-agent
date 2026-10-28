# Three-minute contest video

## Record these two outcomes

Use the clinic visit and missing-return cases already verified in [LIVE_ACCEPTANCE.md](LIVE_ACCEPTANCE.md). This is a product demonstration, not another test campaign. Keep the app running locally and close unrelated browser tabs. Do not show `.env`, keys, account billing pages or personal files.

Use real app interaction. If displaying an existing saved review, label it **Saved live Meta run** and say so. If cutting API waiting time from a newly recorded run, label the cut **Waiting shortened**. Never present a saved or edited run as an uninterrupted live execution. Do not record offline simulation and call it live Meta inference.

On Mac, press **Shift + Command + 5**, choose **Record Selected Portion**, select the app window area, and choose your microphone under Options. Record narration and screen together. Stop through the menu-bar recording control. Aim for 2:50–2:58 so the final file stays below three minutes. Check the exported duration and listen to the audio before uploading.

## Timed narration and screen actions

Read naturally and leave room to point at the interface. Rehearse once; do not try to read all JSON aloud.

| Time | Screen action | Narration |
|---|---|---|
| 0:00–0:20 | Show the healthcare console and clinic case. | “I'm Willie Harvey, founder of Harvey Taxi. Getting someone to a healthcare appointment takes more than an address. A wheelchair user needs a suitable vehicle, a pickup plan, a clear fare, and a plan for getting home. This project makes that transportation evidence reviewable.” |
| 0:20–0:45 | Select Live Meta and show a real run beginning, or open the saved clinic review with a visible saved-run label. | “Our agent uses Meta Muse Spark to choose its tools. It reads the request and policy, builds a checklist, and records source quotations. These tool choices come from the model. The interface lets a reviewer inspect what each tool actually returned.” |
| 0:45–1:15 | Expand one `record_fact`, then the corresponding verification result. Show a receipt's model and response ID briefly. | “Here is an exact quotation linked to a checklist question. Code checks that it exists in the source file. Separate checks validate required transport details, fare arithmetic, the selected pickup bay, and conflicting evidence. This receipt identifies a real Muse Spark API response. The supplied curb measurements are simulated fixtures.” |
| 1:15–1:45 | Show the accepted clinic memo, all passing checks, pending actions and limitations. Do not invent an unsigned state for a signed saved run. | “For this clinic case, the quoted fare matches the supplied tariff, the selected bay meets the demo vehicle policy, and a return coordination plan is documented. The memo cites its evidence and holds for human review. It does not claim the return pickup is already confirmed.” |
| 1:45–2:15 | Switch to the saved missing-return review, labeled Saved live Meta run. Show failed healthcare check and `request_evidence`. | “Now the return plan is missing. The live agent's review ends at needs input. This healthcare transport check identifies the missing plan, and sign-off remains blocked. A plausible-looking request is not enough when required evidence is absent.” |
| 2:15–2:40 | Return to the signed clinic audit; show reviewer acknowledgment and JSON export. | “Human acknowledgment is recorded separately. The audit preserves tool results, citations, verification and the review state. A typed demo acknowledgment never dispatches a vehicle. The successful case and the blocked case both have inspected live-run audits.” |
| 2:40–2:58 | Show repository branch and PR contribution diff, then return to the product. | “During the event, we developed the live model loop, verification gates, healthcare cases and connected console. This is transportation coordination, not medical advice. There is no live SAM measurement or real dispatch. Our goal is to give coordinators and dispatchers a clearer, evidence-backed handoff.” |

## Final recording checks

- Duration is at most three minutes; screen and narration are understandable.
- New event work is distinguished from the existing business and starter code.
- Live model inference, saved replay and simulated curb evidence are correctly labeled.
- Both the valid review and missing-return block are shown.
- The video URL works in a signed-out/private browser and can be viewed without requesting access.
- Paste the final video URL into `SUBMISSION.md` and the official event submission form. Do not submit the old GitHub Pages simulation as the live Python application.

No patient-outcome, live-dispatch, clinical-clearance, HIPAA or production-readiness claim is demonstrated by this video.
