# Hosted console redeploy plan

Prepared 2026-10-30 UTC. Owner approval to redeploy from exactly `53d77779dbf478ac125b3970de3ad8cb3f1d16d1` was given on 2026-10-30. **The deployment isn't complete until the owner's command output shows it and the hosted checks pass.** This changes only the contest app `harvey-healthcare-review` on Modal. The production Harvey Taxi apps are untouched.

Paid Meta calls stay on hold until the hosted checks pass. After that, at most **$0.90 in total** may be spent on the recording, with no automatic retries.

## What is deployed

| Item | Value |
|---|---|
| Commit | `53d77779dbf478ac125b3970de3ad8cb3f1d16d1` (merge of PRs #11–#14). CI `verify-agent` green on its push run; 163 tests passed with none skipped on a clean checkout |
| Currently hosted | `fc49119` (PR #8), deployed 2026-10-29 per the owner's deploy output |
| New on the hosted console | 15-minute idle window and a restart-stable session token (PR #11); spoken date/time check (PR #12). PRs #13–#14 change docs only |
| Unchanged | App name and URL; Modal secret `harvey-healthcare-demo` (the same three names, values not touched); Volume `harvey-healthcare-runs` and its saved runs; Basic-auth sign-in; origin checks; one container and one request at a time |

`modal_console.py` uploads only `agent_kit`, `harvey_agent`, `verification`, `ui`, `cases`, `index.html`, `app.js` and `console.css`. Deploying from a pinned commit uploads exactly that commit's files.

## Commands for the Mac, in order

Run them in the `harvey-healthcare-review` folder, one line at a time. Don't paste comments into zsh. Send the output of each phase before starting the next.

### Phase 1: pin the commit, test it, record the rollback version (free)

```bash
git status --short
git fetch origin
git checkout --detach 53d77779dbf478ac125b3970de3ad8cb3f1d16d1
git log --oneline -1
./helper test
echo "test exit status: $?"
python3 -m modal app history harvey-healthcare-review
```

Expected results:
- `git status --short` prints nothing. If it lists changes, stop and send the list.
- `git log` prints `53d7777 Merge pull request #14: Demo script and recording checklist`.
- The tests end with `OK`, and `test exit status: 0`. The skip count can differ on the Mac.
- The history's newest line is the 2026-10-29 deployment. **Its version (for example `v7`) is the rollback target.**

### Phase 2: deploy (approved)

```bash
python3 -m modal deploy modal_console.py
python3 -m modal app history harvey-healthcare-review
```

Expected results:
- `✓ App deployed`, with `https://williebee615--harvey-healthcare-review-console.us-east.modal.run`.
- The history shows one new version on top. Record that version and the commit `53d7777`.

### Phase 3: hosted checks (no Meta API charges; Modal hosting time is used)

The check script is standalone and reads the password from `CONSOLEPW` without printing it. It runs only Offline simulation and fails if any record shows live inference.

```bash
git show origin/main:audit/hosted_check.py > /tmp/hosted_check.py
read -s CONSOLEPW
export CONSOLEPW
python3 /tmp/hosted_check.py https://williebee615--harvey-healthcare-review-console.us-east.modal.run
echo "hosted check exit status: $?"
```

After `read -s`, type the reviewer password and press Return; nothing is shown. The script checks:
- Authentication: no password returns 401, a wrong password returns 401, the right password returns 200, and a stale token returns 403.
- Saved runs: the two earlier hosted runs (`run_b2023b2d…`, `run_0e228025…`) still read back as `completed_after_human_signoff`.
- Take 1, Appointment card with the demo sentence, offline: `awaiting_signoff`, 9 checks, none failed, 0 Meta calls.
- Take 2, Card contradiction, offline: `needs_input`, only `appointment_card_check` failed, 0 Meta calls.
- It ends with `"all_checks_passed": true` and exit status 0.

Both offline reviews are saved to the shared Volume as new offline runs, labeled as simulation.

Optional visual check in Chrome: the sign-in prompt appears; **Saved reviews** lists the earlier runs; an offline Appointment card run shows the **spoken schedule check**.

### If any Phase 3 check fails: roll back

```bash
python3 -m modal app rollback harvey-healthcare-review vN
python3 -m modal app history harvey-healthcare-review
```

`vN` is the version recorded in Phase 1. The rollback appears as a new history entry, and the URL is unchanged. The rollback command was checked against `modal app rollback --help` (client 1.6.3). Alternatively, `git checkout fc49119` and `python3 -m modal deploy modal_console.py`.

Rollback restores the code. It doesn't touch the secret or the saved runs. Runs saved by the new version carry an extra `spoken_schedule_check`, and the older code reads them without error.

### Finally

```bash
git checkout main
git pull --ff-only origin main
```

## Expected hosting cost (provisional)

**Provisional until the app's actual resource settings and the account's credits are confirmed on the Modal dashboard.**
- `modal_console.py` sets no CPU or memory request, so Modal's defaults apply. Those defaults weren't verified from this session.
- modal.com can't be reached from this session. The rates below are Modal's published rates as quoted by third-party pricing pages:
  - CPU: $0.0000131 per physical core per second;
  - memory: $0.00000222 per GiB per second;
  - Starter plan: $30 a month in compute credits.

| Assumed basis | Per hour the container is up | Per review session (15-minute idle tail plus about 15 minutes of use) |
|---|---|---|
| 0.125 core, 0.5 GiB | about $0.01 | about $0.005 |
| 1 core, 1 GiB | about $0.06 | about $0.03 |

On these assumptions, a recording day with about 2 hours of container time costs roughly $0.02–$0.11 of Modal compute. The 15-minute window adds at most about $0.014 per session compared with the old 60-second window. The hosted checks above make no Meta API charges, but they do use Modal hosting time. Meta API costs are separate.

## Records after a verified deploy

- README, SUBMISSION and MODAL: the deployed commit `53d7777`, the Modal version, and the date (UTC), all taken from the owner's output.
- "Deployed" isn't "tested live". Only the offline hosted checks are verified by this plan.
- Submission status and edit permissions stay unresolved until the owner confirms them in the portal. No commit is tagged as submitted.
