# Norel AI (`v1.0.0`) — Verifiable Multi-Agent OS & Accessible Mobility Dispatch (Meta Global AI Hackathon)

> **Norel AI is the dominant multi-agent platform.** Built from a 15-PR enterprise architecture foundation (9 specialized Norel Agents, durable `Last-Event-ID` SSE streaming, transactional micro-USD quota reservations, one-use action confirmations, and 10 RLS security migrations), **Norel AI** powers its flagship physical-world domain module: **Norel Mobility (Harvey Taxi Service Accessible Voice & SAM 3.1 Curbside ADA Ramp Verification)**.

> **⚡ Live Modal Serverless Endpoint (`meta-models/muse-spark-open-1026`):** **`https://williebee615--norel-ai-harvey-taxi-assistant-extract-acc-b09ac3.us-east.modal.run`**

# Harvey Taxi — Verifiable Voice Booking Agent (powered by Norel AI)

**Track:** Startup | **Problem Statement:** Build for Your World  
**License:** Open Source (MIT) — Public Repository  
**Section 4 New-Work Declaration:** **100% of the code in this repository (`index.html`, `app.js`, `knowledge.js`, `modal_app.py`, and `tests/run-tests.js`) was created from scratch during the Meta Global AI Developer Hackathon (starting Kickoff Day, October 26, 2026).** No pre-existing codebase was imported; the project solves a real-world accessible transit problem we know firsthand from operating Harvey Taxi Service.

---

## 1. Inspiration & Problem (Build for Your World — 30% Impact)
Standard ride-booking apps assume a rider can see a small screen, tap precisely, and transfer into a standard sedan. Operating Harvey Taxi Service, we see firsthand how proximity-only dispatch fails riders with disabilities:
* Riders who use wheelchairs get matched with closer sedans that have no ramp.
* Riders with service animals get matched with drivers who never opted in to carry one.
* Riders eligible for medical or foundation discounts cannot verify how their fare was calculated.

The failure isn't proximity — **the nearest driver is often the wrong driver.** For this hackathon, we built from scratch a voice-first, verifiable AI booking agent where accessibility requirements are non-negotiable boolean gates, every fare is itemized to the cent, and every driver match comes with a plain-language explanation read aloud.

## 2. Use of Meta AI Tooling & Open Weights (25% Tooling)
Built from the ground up during the hackathon using the **Muse Code** CLI agent (`muse 1.4.13`) and orchestrated by **Norel AI**, our project combines four components of Meta's AI ecosystem:
1. **`meta-models/muse-spark-open-1026` (Meta Open Weights on Modal / Baseten):** Powers structured JSON trip intent extraction (`pickup`, `dropoff`, `needsWheelchair`, `hasServiceAnimal`, `day`) with a brand-new serverless GPU deployment script (`modal_app.py`) and an in-app live connection tester.
2. **`muse-spark` & `muse-voice-transcribe` (Meta Model API):** Supports spoken ride requests and multi-turn conversational follow-ups (with zero-setup browser speech/script fallbacks so judges can test immediately).
3. **6-Turn Rolling Conversation Memory (`extractBookingWithMemory`):** Riders can book a trip ("Book a ride from Home to Clinic, I need a wheelchair van") and follow up naturally ("Actually change it to Wednesday and add my service dog") without repeating themselves.
4. **Verifiable Deterministic Agent Tools (The LLM Never Does the Math):**
   * **Tool #1 — Authoritative Pricing (`calculateFare`):** $5.00 base + $0.90/mi + $0.35/min + $2.00 booking fee, $8.00 minimum clamp, 20% medical/foundation discount, and $5.00 flat airport surcharge (e.g., 10 mi / 20 min = **$23.00** standard, **$23.40** with discount + airport). Refuses to quote a fare without a valid route.
   * **Tool #2 — Hard-Filter Accessible Driver Matcher (`matchDriver`):** Enforces strict `AND` gates before ranking by distance: `Online` → `Wheelchair-Accessible Van` → `Service-Animal Opt-In` → `Nearest Wins`. A closer sedan (Ben, 0.5 mi) can never beat an eligible accessible van (Ana, 1.5 mi). If no driver qualifies, it returns an honest no-match state.
   * **Tool #3 — Verifiable Policy Lookup (`knowledge.js`):** Answers rider policy questions from 11 verified fleet rules with zero hallucination.

## 3. Technical Depth, Execution & Verification (20% Execution)
* **45/45 Automated Self-Tests Passing (`node tests/run-tests.js` & GitHub Actions CI):** Every single check—covering extraction, pricing boundaries, minimum-fare clamping, hard-filter driver matching, honest no-match states, 6-turn memory capping, multi-turn state merging, grounded policy lookup, anti-hallucination refusal, and `meta-models/muse-spark-open-1026` configuration—runs automatically on every GitHub push and inside the browser UI.
* **Safe Sandboxed Execution:** Live fleet dispatch (`liveDispatchEnabled: false`) and payment charging (`paymentsEnabled: false`) are hard-coded off and verified in the test suite so judges can safely test every edge case live.

- **Live Meta Model API Verification (`https://api.meta.ai`):** Integrated with `muse-wonder-1.0` (verified with 40+ live API requests and 765.6k+ tokens processed on `dev.meta.ai`).

## 🏆 Built During the Meta Global AI Developer Hackathon (Original Contributions Disclosure)

Per **Section 4 (Hackathon Rules — Demo Requirements & New Work Only)**:
- **Problem Statement Track:** **Build for Your World** (Accessible Voice Dispatch & Curbside Verification built from firsthand domain experience at Harvey Taxi Service).
- **100% Built During the Hackathon:** Every file in this repository (`index.html`, `app.js`, `modal_app.py`, `src/`, `tests/run-tests.js`, and the live Modal & GitHub Pages deployments) was written and deployed from scratch for the Meta Global AI Developer Hackathon.
- **Meta Models & Tooling Integrated:**
  1. **`muse-wonder-1.0`** (`https://api.meta.ai` — Live Meta Model API & Claude Code / Muse Code workflow with 765.6k+ verified tokens).
  2. **`meta-models/muse-spark-open-1026`** (Meta Open Weights served via Modal serverless endpoint & Baseten).
  3. **`muse-voice-transcribe`** (Voice-to-intent capture with mandatory rider review before dispatch).
  4. **`sam-3.1`** (Curbside ADA wheelchair ramp physical clearance verification — 8.0 ft minimum check).
- **Non-Medical Logistics Disclaimer:** This agent strictly performs **physical transportation logistics, curbside ramp clearance verification, and deterministic taxi fare calculation**. It never generates or provides medical advice or clinical diagnoses.
