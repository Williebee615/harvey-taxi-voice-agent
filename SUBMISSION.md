# Harvey Taxi — Accessible Voice-Booking & Verification Agent
**Meta Global AI Developer Hackathon (Startup Track)**
**Strict Scope:** Harvey Taxi Accessible Voice-Booking & Verification Agent (`Williebee615/harvey-taxi-voice-agent`)

## 1. Architecture Diagram
    [Rider Intake (rider_intake.txt) + Policy (HANDBOOK.md) + SAM 3.1 Curb Sensor (sam3_curb_telemetry.json)]
                                                |
                                                v
    [4-Turn Document-Grounded Agent Loop (legal_agent/loop.py)]
      Turn 1 (PLAN):    list_documents    -> Enumerate case evidence files
      Turn 2 (PLAN):    set_checklist     -> 5 verification items + counter-evidence probe
      Turn 3 (ACT):     analyze_documents -> Verify verbatim quote, $2.50+$1.50/mi fare, & SAM 3.1 >=8.0ft curb
      Turn 4 (OBSERVE): request_evidence  -> Halt at needs_input on missing fields, unsafe 6.1ft curb, or fare drift
                        submit_memo       -> Halt at awaiting_signoff until human dispatcher sign-off
                                                |
                                                v
    [Human Dispatcher Sign-Off Gate (./helper resume '<Signature>')] -> final_status=completed_after_human_signoff

## 2. Meta Model Role Mapping & Live vs. Fallback Transparency
- **Primary Reasoning Engine:** Meta `muse-spark-1.5` (`[https://api.meta.ai/v1](https://api.meta.ai/v1)`)
- **Fine-Tuned Policy & Fare Verifier (Fireworks AI SFT):** Meta `Muse Glimmer 30B` (Job `vxd87q0r`, Loss `0.57 -> 0.04`, Live Deployment `accounts/williebee615/models/ft-f7pywv9kusek5#accounts/williebee615/deployments/myxfl5zq`)
- **Speech Intake Transcription:** Meta `muse-wonder-audio-1.0`
- **Visual Curb Clearance Verifier:** Meta `sam-3.1-curb-segmentation` (`>= 8.0ft` ramp clearance requirement)
- **Simulation Boundary:** When run without API keys in `.env` (such as in GitHub Actions CI or browser-only judge preview), `inference_mode()` explicitly reports `DETERMINISTIC_FALLBACK_SIMULATION`. No real vehicles are dispatched and no real payments are processed.

## 3. Before vs. After: Unverified Agent vs. Verified Harvey Taxi Agent
- **Obstructed 6.1ft South Curb Bay:** Unverified agent dispatches to South Bay and strands wheelchair rider; Verified Agent checks SAM 3.1 counter-evidence, rejects 6.1ft South Bay, and selects 9.4ft North Bay or halts with `needs_input`.
- **Illegal $15.00 Wheelchair/Service Dog Fee ($26.50 quote):** Unverified agent accepts overcharge; Verified Agent enforces `$2.50 base + $1.50/mi + $0.00 ADA fee = $11.50` (49 CFR Part 37) and halts on fare drift.
- **Missing Pickup Address/Time:** Unverified agent hallucinates defaults; Verified Agent calls `request_evidence` and halts at `needs_input`.
- **Premature Completion:** Unverified agent marks ride `completed` immediately; Verified Agent halts at `awaiting_signoff` until `./helper resume` records human authorization.

## 4. Verification & Demo Commands
    ./helper test
    ./helper validate-models
    ./helper run --case harvey-taxi-ada-doctor-visit
    ./helper resume Dispatcher-Willie-Harvey
    ./helper run --case harvey-taxi-unsafe-curb-boarding
    ./helper run --case harvey-taxi-incomplete-intake
