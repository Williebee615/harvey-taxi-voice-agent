# Norel AI — Fixed-Point Verification Specification (`VERIFICATION.md`)

When `VERIFICATION=on`, `agent_kit/tools` enables `VERIFIER_TOOLS` (`flag_privileged`, `request_evidence`, `check_signatures`) and runs fixed-point checks at three stages:

1. **`set_checklist` Verification:** Ensures all 6 required ADA transit items (`pickup_location`, `destination_address`, `requested_time`, `mobility_requirement`, `service_animal`, `verified_fare`) are tracked.
2. **`analyze_document` / `record_fact` Verification:** Verifies every recorded rider fact and policy quote against `HANDBOOK.md` and `ground_truth/harvey-taxi-ada-case.json`.
3. **`submit_memo` Verification:** Enforces deterministic Harvey Taxi pricing math (`$2.50 Base + $1.50/mile`, `$0.00` ADA/service-animal surcharge) and transitions to `awaiting_signoff`.
