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

To change the key or password later, replace the whole secret from a Terminal where the values are loaded privately (for example with `read -s`): `python3 -m modal secret create harvey-healthcare-demo MODEL_API_KEY="$NEWKEY" MODEL_API_MODEL=muse-spark-1.3 HARVEY_DEMO_PASSWORD="$CONSOLEPW" --force`, then redeploy. Current deployment: https://williebee615--harvey-healthcare-review-console.us-east.modal.run, from `main` at `c7c1f1a` (2026-10-29).

Open the URL printed by deploy. Browser sign-in username: `reviewer`; password: the value you stored in Modal Secrets. Share reviewer access privately with authorized testers. Never put a Meta key into a browser field, public repository, video or submission description.

Run the clinic and missing-return-plan cases from this hosted URL and download their audit JSON. A successful deployment alone does not verify model invocation. Check `LIVE_META_API`, response receipts and both outcomes before describing the hosted demo as tested.

All reviewers with this password share a demo workspace and can inspect its fictional runs. One container and one concurrent request limit write contention; saved runs persist on a Modal Volume. This is a controlled contest demo, not a multi-user production service. The UI's human acknowledgment remains a demo acknowledgment only. The public Pages overview remains separate.

Modal compute/storage and Meta API calls consume their respective balances. The $30 displayed in the dashboard is not evidence that contest credits have been applied (the Official Rules describe $150 in Meta Model API credits; confirm the amount and expiry in your account). Confirm balances and set spending controls in each provider dashboard. Stop the new `harvey-healthcare-review` app in Modal when no longer needed.
