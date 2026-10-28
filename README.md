# Harvey Taxi — Accessible Care Transportation Review

A verifiable agent for the transportation gap around healthcare appointments. A coordinator supplies a fictional rider request, fare policy and pickup evidence; the agent investigates, records exact quotations, checks the booking independently and prepares a cited memo for a human reviewer.

This is a hackathon prototype for transportation logistics. It does not provide medical advice, clinical clearance, emergency services, real vehicle dispatch or payment processing. Benefits such as fewer missed appointments are hypotheses for a future pilot, not measured outcomes.

## Run locally

Python 3.10+ is sufficient; the core application has no third-party Python dependencies.

```bash
./helper test
./helper serve
```

Open http://127.0.0.1:8765. Choose a case and simulation or live mode. Step through individual tools or run a batch. Inspect tool arguments and observed source evidence, verification results, the cited memo and API receipt metadata. Saved reviews can be reopened and exported as JSON.

The static GitHub Pages copy explains that a local server is required; it never pretends to run a live agent.

## Configure Meta privately

Create `.env` locally (never commit it):

```dotenv
MODEL_API_KEY=replace_locally_with_your_key
MODEL_API_MODEL=muse-spark-1.3
MODEL_API_BASE=https://api.meta.ai/v1
```

Existing `META_MODEL` and `META_BASE_URL` aliases are supported. Explicit `MODEL_API_*` names take precedence. Shell environment values take precedence over `.env`. Fireworks credentials may remain in `.env`; this adapter never uses them for Meta authentication. Requests are restricted to the official Meta endpoint and redirects are refused.

```bash
./helper validate-models
./helper run --case healthcare-clinic-visit --mode live --turns 20
```

A probe is separate from a booking. `LIVE_META_API` is recorded only after a successful model response within that booking run. Live mode sends case evidence to Meta and incurs API usage; use fictional demo data. API errors pause the run; there is no silent simulation or provider fallback. The live tool-calling workflow must be tested on the user's configured machine before recording a live demo.

## Modes and workflow

| Mode | Tool choices | API calls | Curb measurements |
|---|---|---|---|
| Simulation | Explicitly scripted offline demonstration | None | Labeled fixture data |
| Live | Meta selects one tool each turn | Meta Responses API | Same labeled fixture data |

The loop loads instructions and the objective, exposes tool schemas, executes the chosen tool and returns its observation to the model. It saves the transcript after every turn. Stateless Responses replay retains encrypted reasoning items locally for continuation; the UI exposes public tool records, not private reasoning. The model cannot approve or dispatch a ride.

Tools: `list_documents`, `set_checklist`, `update_plan`, `analyze_documents`, `record_fact`, `verify_booking`, `request_evidence`, `submit_memo`.

`submit_memo` independently enforces current intake, tariff, quoted fare, zero accessibility surcharge, selected-bay safety and counter-evidence checks. Every checklist item needs a finding with valid case-scoped fact citations; citations must collectively cover intake, policy and telemetry. Facts are exact source quotations; model interpretations are not certified as true merely because a quotation exists. The human must review the memo's conclusions.

## Healthcare demonstration

| Case | Expected result | Why |
|---|---|---|
| `healthcare-clinic-visit` | `awaiting_signoff` | Coordinator, appointment, vehicle capability and return plan supplied |
| `healthcare-missing-return-plan` | `needs_input` | Return coordination is unresolved |
| `healthcare-clinical-support` | `needs_input` | Request is outside transportation-only scope |
| `harvey-taxi-unsafe-curb-boarding` | `needs_input` | Supplied bay evidence fails the demo policy |
| `harvey-taxi-wrong-fare-drift` | `needs_input` | Quoted fare violates supplied tariff |
| `harvey-taxi-contradictory-evidence` | `needs_input` | Override conflicts with evidence |
| `harvey-taxi-incomplete-intake` | `needs_input` | Required rider details absent |

The 8ft clearance threshold is the **demo fleet's vehicle-specific policy**, not a universal legal accessibility standard. No live SAM segmentation, calibrated physical measurement, speech model, EHR connection or hospital authorization is implemented. A `model` label inside a fixture does not mean that model ran.

## Pause, continue, review

Each start returns a unique `run_id`; substitute it below:

```bash
./helper run --case healthcare-clinic-visit --mode live --turns 1
./helper resume --run-id run_REPLACE_WITH_RETURNED_ID --turns 20
./helper show --run-id run_REPLACE_WITH_RETURNED_ID
./helper approve --run-id run_REPLACE_WITH_RETURNED_ID --signature 'Demo Reviewer'
```

A `needs_input` run makes no new model calls without a follow-up. Update source case files locally, then describe the change:

```bash
./helper resume --run-id run_REPLACE_WITH_RETURNED_ID --message 'The coordinator updated the return plan in rider_intake.txt.'
```

A follow-up is not evidence. The live agent must recheck and recite current source files. Simulation evidence changes require a new simulation run. `awaiting_signoff` and signed runs return without model calls. Approval targets the exact run ID and rechecks the current evidence digest. Changed evidence blocks approval. Typed names are **simulated acknowledgments**, not authenticated dispatch authority.

## Safety and storage boundaries

- The server binds only to loopback, checks Host/Origin and uses a session token for mutations. Only explicit frontend assets are served; `.env`, code and run files cannot be fetched as static files.
- UI text uses DOM text nodes, not HTML interpolation. The core has no browser automation or external action tools.
- Run transcripts and fixture details persist locally in `workspace/runs/`; exported audits contain source evidence. Do not use real patient data in this prototype. No HIPAA compliance or production security certification is claimed.
- Single local server process is the supported deployment. CLI/server concurrent mutations of the same run are unsupported. Authenticated staff roles, encrypted storage, retention controls, vendor agreements, production concurrency and real transport integrations require separate engineering before a clinical pilot.
- A 40-turn batch and 200-turn run budget bound paid calls. Errors are surfaced without keys or remote error bodies.

## Validation and architecture

```text
CLI / local console → resumable model loop → schema-validated tools
                                             ↓
                          case-scoped sources + independent checks
                                             ↓
                                 cited memo → demo human review
```

`./helper test` runs offline numerical, evidence, tool-contract, fake-provider multi-turn, resume, approval and HTTP security tests. The existing Node entry point forwards to the same tests. CI runs tests and JavaScript syntax checks without API keys. See [VERIFICATION.md](VERIFICATION.md) and [docs/DEMO.md](docs/DEMO.md).

Historical Fireworks receipts remain archived as provenance only. They are not evidence of current inference, training quality or a live deployed model in this version. Optional `modal_app.py` exposes a CPU fixture verifier; it does not claim GPU or model execution.

## Hackathon contribution record

This upgrade replaces the preexisting scripted/canned workflow with an explicit live Meta Responses loop, exact citations, resumable audit records, independent submission gates, a connected local console and healthcare transportation fixtures. See the upgrade pull request and commit diff for precise contribution boundaries. Existing Harvey Taxi business services are context, not functionality newly built here. Confirm event eligibility and contribution dates against the organizer's rules before submission.


## Contest submission package

The current scope is the tested local application, public source and a three-minute video. No hosting purchase or public backend is part of this submission preparation. Use [SUBMISSION.md](SUBMISSION.md), the [contest checklist](docs/CONTEST_CHECKLIST.md), [timed video script](docs/DEMO.md) and [reviewed live acceptance record](docs/LIVE_ACCEPTANCE.md). The video link and event-form submission remain outstanding. The public GitHub Pages page is not the live Python backend.
