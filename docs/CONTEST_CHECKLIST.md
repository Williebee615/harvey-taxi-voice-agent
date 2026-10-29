# Contest-only submission checklist

Source of requirements: the Meta Global AI Developer Hackathon participant guide supplied by the entrant in this session. This file is an execution checklist, not a substitute for the official rules accepted in the event platform.

| Requirement | Status | Evidence or remaining action |
|---|---|---|
| Fit a project theme | Prepared | Build for Your World: firsthand accessible transportation coordination |
| Incorporate Meta models | Verified in supplied live audits | Muse Spark Responses API; no claim that every available Meta model is used |
| Public source repository | Available | PR #3's head is already in `main`; link `main` or the current contest branch |
| Identify work built during the event | Prepared for review | PR diff, dated commits and SUBMISSION.md contribution boundary; entrant confirms eligibility |
| Team at most four, contributors listed | Entrant confirmation needed | Verify actual registration; do not assume solo or select a track from business ownership alone |
| Accessible three-minute demo video | Not complete | Follow DEMO.md; upload and verify signed-out access |
| Repository and video links accessible | Repository available; video pending | Check the exact links used in the submission form |
| Submit through official CV platform | Not complete | Entrant completes the form with verified contributor, track, source and video details |
| Deadline | Per supplied schedule | November 4, 2026, 9 PM Eastern / 8 PM America/Chicago; check organizer announcements for changes |

## Scope boundaries

No Render purchase, public Python deployment, domain cutover, real patient integration or removal of offline development tools is needed to complete the requirements listed above. Keep the tested local app and make its execution instructions reproducible. A judge-friendly hosted app can be useful but is not presented here as a mandatory entry condition.

The old GitHub Pages page is not the live agent. Use source plus an accessible demonstration video as submission artifacts; accurately describe the local execution requirement wherever the form asks about a live product.

## Current acceptance

- Automated regression: 67 offline tests passed at commit `80876be` (historical record in LIVE_ACCEPTANCE.md). After the 2026-10-29 cleanup, 78 offline tests pass with the optional Modal dependencies installed (76 pass and 2 skip without them).
- Positive live case: cited memo accepted, independent checks passed, separate demo acknowledgment recorded.
- Negative live case: missing return plan detected; no acknowledgment or dispatch.
- Full source and hash checks are recorded in LIVE_ACCEPTANCE.md.

Do not merge or change the public landing page merely to claim deployment. A source merge and a hosted working backend are different operations. The final source branch can be submitted directly if it remains public and accessible.
