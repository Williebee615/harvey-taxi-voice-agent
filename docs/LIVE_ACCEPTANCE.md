# Reviewed live acceptance evidence — 2026-10-28

These results come from entrant-supplied JSON exports inspected against the contest branch's actual case files. Provider response IDs and usage were present in the exports; they were not independently fetched from Meta. The exports contain fictional transportation cases. Full transcripts and private credentials are not published here.

| Check | Clinic visit | Missing return plan |
|---|---|---|
| Run ID | `run_97319752cdb04bd89f48e9e8b2e94234` | `run_d950e24d8b754220959058b75c1d594a` |
| Mode / model | `LIVE_META_API` / `muse-spark-1.3` | `LIVE_META_API` / `muse-spark-1.3` |
| Tool turns | 24 | 20 |
| Final review outcome | `awaiting_signoff` before separate acknowledgment | `needs_input` |
| Exported final status | `completed_after_human_signoff` | `needs_input` |
| Source digest matches case files | Yes | Yes |
| Independent booking checks | All six passed | Healthcare transport check failed on `Return Plan`; other checks passed |
| Final memo citations | All referenced fact IDs, checklist ownership, exact quotes and source digests checked | No accepted memo |
| Human acknowledgment | Demo reviewer name recorded | Absent |
| Real dispatch | Disabled | Disabled |

The successful run's recorded tool results contain no refusal or retry. Its public audit omits the conversation messages, so it cannot independently establish that no follow-up message was supplied. Neither outcome proves production readiness, clinical safety or improved appointment attendance.

## Source export fingerprints

These SHA-256 values identify the inspected exports without publishing the full files:

- `run_97319752cdb04bd89f48e9e8b2e94234.json`: `86d316347fcb579a013f653551743ac77beef46eb520002bfa1704201d4492d1`
- `run_d950e24d8b754220959058b75c1d594a.json`: `6bfe517910a7d4d8ecf780c2bb8e1868734744b168279d30fd5326d67976e832`

Keep the original exports locally. Do not substitute the older 37-turn recovery run when describing the fresh 24-turn result. Token usage includes repeated conversation input and cached tokens; it is not a dollar cost or count of unique generated words.

## Automated evidence

The contest code's 67 offline regression tests passed on the entrant's Mac and in GitHub Actions for commit `80876be6c07a6fad816937f2faaaf8f0f452e5c8`. Those tests cover numerical rules, exact quotations, citation freshness, fake-provider orchestration, resume, memo classification, approval and local HTTP security. They complement the live exports; mocked tests are not evidence of live Meta execution.

CI run: https://github.com/Williebee615/harvey-taxi-voice-agent/actions/runs/40709877565

The separate, uncommitted hosting preparation is outside this contest branch and outside this acceptance record.
