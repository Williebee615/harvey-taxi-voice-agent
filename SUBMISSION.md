# Harvey Taxi Accessible Voice-Booking & Verification Agent (Meta Workshop Contest Submission)

## 1. Contest Assignment Overview
This project implements the Meta Workshop Verification-First Agent Architecture (`legal_agent/loop.py`, `agent_kit/`, `verification/checks.py`, and `ESCALATION_RULES.md`) applied to Harvey Taxi Service's ADA Accessible Ride Dispatch:

- **Document-Grounded 4-Turn Loop (`PLAN` -> `ACT` -> `OBSERVE`):**
  1. `list_documents`: Enumerates primary case files (`rider_intake.txt`, `HANDBOOK.md`, `sam3_curb_telemetry.json`).
  2. `set_checklist`: Formulates 4-8 verification questions + mandatory counter-evidence check before taking action.
  3. `analyze_documents`: Extracts verbatim source quotes and checks counter-evidence (obstructed 6.1ft South curb bay vs. 8.0ft ADA ramp requirement).
  4. `request_evidence` / `submit_memo`: Halts with `needs_input` when required intake details are missing, or stages at `awaiting_signoff` when human signature/dispatch approval is required.
- **Fixed-Point Verification (`verification/checks.py`):**
  Enforces exact quote matching, arithmetic invariance ($2.50 base + $1.50/mi, $0.00 ADA wheelchair & service dog fee), and refusal of premature actions.
- **Live Model Stack (Meta Muse + Fine-Tuned Muse Glimmer 30B):**
  - Primary Reasoning Loop: Meta `muse-spark-1.5` (`[https://api.meta.ai/v1](https://api.meta.ai/v1)`)
  - Fine-Tuned SFT Model (Fireworks AI): Meta `Muse Glimmer 30B` (`Training / Supervised / vxd87q0r`, Loss `0.57 -> 0.04`)
  - Live On-Demand GPU Deployment: `accounts/williebee615/models/ft-f7pywv9kusek5#accounts/williebee615/deployments/myxfl5zq`

## 2. Quick Verification Commands
    ./helper run
    ./helper live-norel
    ./helper test
