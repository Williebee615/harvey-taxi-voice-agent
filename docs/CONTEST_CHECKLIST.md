# Contest-only submission checklist

Source of requirements: the Meta Global AI Developer Hackathon participant guide supplied by the entrant in this session. This file is an execution checklist, not a substitute for the official rules accepted in the event platform.

| Requirement | Status | Evidence or remaining action |
|---|---|---|
| Fit a project theme | Prepared | Build for Your World: firsthand accessible transportation coordination |
| Incorporate Meta models | Verified live 2026-10-29 | Muse Spark tool calling and image understanding, Muse Voice Transcribe; see docs/LIVE_EVIDENCE.md. SAM 3.1 not used |
| Public source repository | Available | PR #3's head is already in `main`; link `main` or the current contest branch |
| Identify work built during the event | Prepared for review | PR diff, dated commits and SUBMISSION.md contribution boundary; entrant confirms eligibility |
| Team at most four, contributors listed | Entrant confirmation needed | Verify actual registration; do not assume solo or select a track from business ownership alone |
| Accessible three-minute demo video | Not complete | Follow DEMO.md; upload and verify signed-out access |
| Repository and video links accessible | Repository available; video pending | Check the exact links used in the submission form |
| Submit through official CV platform | Not complete | Entrant completes the form with verified contributor, track, source and video details |
| Deadline | Per supplied schedule | November 4, 2026, 9 PM Eastern / 8 PM America/Chicago; check organizer announcements for changes |

## Scope boundaries

No Render purchase, domain cutover, real patient integration or removal of offline development tools is needed to complete the requirements listed above. A password-protected hosted console now runs on Modal (deployed from `main` at `fc49119`, PR #8, 2026-10-29). It is useful for judges but not a mandatory entry condition, and it needs a redeploy after each approved merge.

The old GitHub Pages page is not the live agent. Use source plus an accessible demonstration video as submission artifacts; accurately describe the local execution requirement wherever the form asks about a live product.

## Current acceptance

- Automated regression: 67 offline tests passed at commit `80876be` (historical record in LIVE_ACCEPTANCE.md). On 2026-10-29, after the card, speech, receipts, batch, console-recording, integrity and provenance work, 137 offline tests passed. After the console-label work (sign-off label, headline badges, remembered mode), 143 tests run; 141 pass and 2 skip without the optional Modal dependencies (the headless-browser test also skips where Playwright is unavailable).
- Positive live case: cited memo accepted, independent checks passed, separate demo acknowledgment recorded.
- Negative live case: missing return plan detected; no acknowledgment or dispatch.
- Full source and hash checks are recorded in LIVE_ACCEPTANCE.md.

Do not merge or change the public landing page merely to claim deployment. A source merge and a hosted working backend are different operations. The final source branch can be submitted directly if it remains public and accessible.
