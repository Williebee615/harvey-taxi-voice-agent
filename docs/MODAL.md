# Hosted reviewer console on Modal

This optional deployment serves the current healthcare review UI and agent, not the legacy `extract_accessible_booking` endpoint. Modal runs CPU application code; Meta Model API performs reasoning. No GPU inference is claimed. The existing Modal deployment is left untouched.

1. In Modal **Secrets**, create a custom secret named `harvey-healthcare-demo` with:
   - `MODEL_API_KEY`: your working Meta key.
   - `HARVEY_DEMO_PASSWORD`: a unique password of at least 16 characters.
   - `MODEL_API_MODEL`: `muse-spark-1.3`.
2. From the updated repository on your Mac:

```bash
python3 -m pip install modal
python3 -m modal setup
python3 -m modal deploy modal_console.py
```

To change the key or password later, replace the whole secret from a Terminal where the values are loaded privately (for example with `read -s`): `python3 -m modal secret create harvey-healthcare-demo MODEL_API_KEY="$NEWKEY" MODEL_API_MODEL=muse-spark-1.3 HARVEY_DEMO_PASSWORD="$CONSOLEPW" --force`, then redeploy. Current deployment: https://williebee615--harvey-healthcare-review-console.us-east.modal.run, from `main` at `fc49119` (PR #8, 2026-10-29).

Open the URL printed by deploy. Browser sign-in username: `reviewer`; password: the value you stored in Modal Secrets. Share reviewer access privately with authorized testers. Never put a Meta key into a browser field, public repository, video or submission description.

Run the clinic and missing-return-plan cases from this hosted URL and download their audit JSON. A successful deployment alone does not verify model invocation. Check `LIVE_META_API`, response receipts and both outcomes before describing the hosted demo as tested.

All reviewers with this password share a demo workspace and can inspect its fictional runs. One container and one concurrent request limit write contention; saved runs persist on a Modal Volume. This is a controlled contest demo, not a multi-user production service. The UI's human acknowledgment remains a demo acknowledgment only. The public Pages overview remains separate.

Modal compute/storage and Meta API calls consume their respective balances. The $30 displayed in the dashboard is not evidence that contest credits have been applied (the Official Rules describe $150 in Meta Model API credits; confirm the amount and expiry in your account). Confirm balances and set spending controls in each provider dashboard. Stop the new `harvey-healthcare-review` app in Modal when no longer needed.

## Sessions and troubleshooting

- **Idle window.** The console stays up for 15 idle minutes (`scaledown_window=900`). Modal bills for the idle CPU container during that window. Earlier deployments used 60 seconds: after a minute of inactivity the next click was refused with "Local console token and origin required".
- **Restarts.** The page's console token is derived on the server from `HARVEY_DEMO_PASSWORD` with a one-way HMAC. A restarted container accepts a page loaded before the restart. Only a signed-in reviewer receives the token, it doesn't reveal the password, and it changes when the password changes. Host, origin, password and token checks are unchanged. If a stale token is still rejected (for example after a password change), the page fetches a fresh one and says "The review was not started; no Meta call was made. Click the button again." It never retries a paid review on its own.
- **Held Meta transcripts** live in memory for 30 minutes and are used once. A container restart loses them. The console then asks the rider to record again; it never substitutes other text.
- **The page appears without styling in Safari.** **Shift-Command-R is Safari's Reader shortcut, not a hard reload.** Reader shows the page's text on a plain background without the console's styling or buttons. Press Shift-Command-R again, or Esc, to leave Reader. The server marks every response `Cache-Control: no-store`, so an ordinary reload (Command-R) already fetches the current version.
