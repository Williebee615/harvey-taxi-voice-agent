# Upgrade review notes

This branch changes the prototype's execution contract. Preserve the existing checkout and local `.env` before switching branches. The `.env` file is never included in the change.

- The old canned browser domain flows were removed from the active app. They fabricated website inspections and are not replaced with live website actions.
- `./helper --help` now displays command help instead of running a booking.
- Simulation remains available, labeled, network-free and driven through the same tool gates. Its trace is longer than the old fixed four-turn script because source facts and verification are explicit.
- Live mode is opt-in and uses Meta Responses only. The Fireworks key remains separate; archived receipts are not presented as current inference.
- `./helper resume` continues a run. Demo acknowledgment is now the explicit `./helper approve --run-id ... --signature ...` command. Approval never means dispatch.
- New version-2 run IDs are 32 hexadecimal characters after `run_`. Existing run artifacts remain archived; they are not migrated or silently reused for approvals.
- The dedicated local server replaces generic static file serving. Production hosting, staff identity, patient records, live voice, live images and real dispatch are separate work.

## Proposed clinic pilot

Start with fictional cases in a coordinator-led walkthrough. Evaluate whether the checklist and cited handoff reduce coordination time and catch incomplete return plans. Agree on the actual fleet's vehicle requirements before replacing the demo policy. Do not infer clinical readiness or transport suitability from an LLM response.

A real pilot needs participating organizations to define privacy arrangements, authenticated roles, operational handoffs, emergency exclusions, accessibility validation and outcome measurement. No clinical or regulatory compliance claim is established by this prototype.

The legacy report module now exports only the actual public JSON audit. It no longer invents an approved PDF when no run exists or labels every checklist item proven. Historical files under `workspace/` are unverified archives from the prior version; the new console accepts only version-2 runs.
