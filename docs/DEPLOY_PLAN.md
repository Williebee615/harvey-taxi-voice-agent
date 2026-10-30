# Hosted console redeploy plan (for owner review)

Prepared 2026-10-30 UTC. **Not executed. Deployment and paid calls are on hold until the owner approves.** This changes only the contest app `harvey-healthcare-review` on Modal. The production Harvey Taxi apps are untouched.

## What would be deployed

| Item | Value |
|---|---|
| Commit | `main` at `53d77779dbf478ac125b3970de3ad8cb3f1d16d1` (merge of PRs #11–#14; CI `verify-agent` green; 163 tests) |
| Currently hosted | `fc49119` (PR #8), deployed 2026-10-29 per the owner's deploy output |
| New on the hosted console | 15-minute idle window and a restart-stable session token (PR #11); spoken date/time check (PR #12). PRs #13–#14 change docs only |
| Unchanged | App name, URL, Modal secret `harvey-healthcare-demo` (same three names; no new secret), Volume `harvey-healthcare-runs` and its saved runs, Basic-auth sign-in, origin checks, one container, one request at a time |

## Before deploying (free)

Run on the Mac, in the `harvey-healthcare-review` folder. Run the commands one per line; don't paste comments into zsh.

```bash
git fetch origin
git checkout main
git pull --ff-only origin main
git log --oneline -1
./helper test 2>&1 | tail -3
python3 -m modal app history harvey-healthcare-review
```

Expected results:
- `git log` prints `53d7777`.
- The tests end with `OK`. The skip count can differ on the Mac.
- The history's last line is the 2026-10-29 deployment. **Write down its version** (for example `v7`). That is the rollback target.

## Deploy (needs approval)

```bash
python3 -m modal deploy modal_console.py
```

Expected output: `✓ App deployed` and the same URL, `https://williebee615--harvey-healthcare-review-console.us-east.modal.run`.

## Verify after deploying (free; no Meta calls)

1. Open the URL in Chrome. The browser asks for the `reviewer` sign-in.
2. Select **Offline simulation** and click **Appointment card**. Type the demo sentence and click **Start offline simulation (no API calls)**. Expected: **awaiting signoff**, nine checks passing, including **spoken schedule check**: "Spoken dates and times agree with the booking and the appointment card". The receipts panel says no API calls were made.
3. Leave the page idle for 2 minutes, then click **Card contradiction** and start an offline review. It should run, because the console stays up for 15 minutes. If the container did restart, the page says "The review was not started; no Meta call was made" and the next click works.
4. `python3 -m modal app history harvey-healthcare-review` shows the new version on top.

## Rollback

Option A, Modal's rollback (checked against `modal app rollback --help`, client 1.6.3):

```bash
python3 -m modal app rollback harvey-healthcare-review vN
```

`vN` is the version noted before deploying. Without a version, the command returns to the previous one. Modal records a rollback as a new deployment in the history, and the URL is unchanged.

Option B, redeploy the previous code:

```bash
git checkout fc49119
python3 -m modal deploy modal_console.py
git checkout main
```

Notes:
- Rollback restores the code. It doesn't touch the secret or the Volume.
- Runs saved by the new version carry an extra `spoken_schedule_check` entry. The older code reads them without error, because it treats checks as a list.
- Each command uses the Modal login on the Mac; this cloud session has no Modal credentials.

## Expected hosting cost (estimate)

modal.com isn't reachable from this session. The rates below are Modal's published rates as quoted by third-party pricing pages, so **confirm them on the Modal dashboard**:
- CPU: $0.0000131 per physical core per second.
- Memory: $0.00000222 per GiB per second.
- Starter plan: $30 a month in free compute credits.

The app sets no CPU or memory request, so Modal's defaults apply (not verified here). Billing is assumed to follow the larger of the reservation and actual use.

| Basis | Per hour the container is up | Per review session (a 15-minute idle tail plus about 15 minutes of use) |
|---|---|---|
| Low: 0.125 core, 0.5 GiB | about $0.01 | about $0.005 |
| High: 1 core, 1 GiB | about $0.06 | about $0.03 |

A recording day with about 2 hours of container time would cost roughly **$0.02–$0.11 of Modal compute**, within the Starter credits if the account is on that plan. The 15-minute window costs at most about $0.014 more per session than the old 60-second one. Meta API costs are separate, and paid calls remain on hold.

## Records to update after an approved deploy

- README, SUBMISSION and MODAL: record the deployed commit and the date (UTC), per the owner's deploy output.
- Keep "deployed" separate from "tested live". A deploy alone doesn't verify Meta inference.
