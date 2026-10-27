# Norel AI — Accessible Transit Escalation Rules (`ESCALATION_RULES.md`)

1. **Missing Critical Dispatch Fields (`status: "needs_input"`):**
   - If `pickup_location`, `destination_address`, or `requested_time` is null or unverified, the agent MUST pause the run with `status = "needs_input"` and ask a clarifying question.
2. **Unverified Route Distance (Fare Refusal Rule):**
   - The agent MUST refuse to estimate or quote a dollar fare until route mileage is verified.
3. **Curbside ADA Ramp Obstruction (`SAM 3.1 < 8.0 ft`):**
   - If SAM 3.1 segmentation detects `< 8.0 ft` of clear curb width, the agent MUST trigger autonomous alternate drop-off zone recovery or escalate before dispatch.
4. **Medical / Privileged Information Guardrail (`flag_privileged`):**
   - The agent MUST strip medical diagnoses and refuse health advice, recording strictly transit accommodation facts (`wheelchair_access`, `service_animal`).
5. **Mandatory Human Sign-Off (`status: "awaiting_signoff"`):**
   - Before any booking preview transitions to `answered`, the loop MUST pause at `awaiting_signoff` for explicit rider confirmation.
