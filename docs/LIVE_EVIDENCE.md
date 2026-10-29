# Live model evidence

This file records what has actually run against Meta's API. Configuration, a configured key, or offline tests are not evidence of inference.

## Status (2026-10-29 UTC)

| Capability | Status | Evidence |
|---|---|---|
| Muse Spark tool calling (Responses API) | **Verified by entrant exports, 2026-10-28** | Two runs in [LIVE_ACCEPTANCE.md](LIVE_ACCEPTANCE.md) |
| Muse Spark image input (appointment card) | **Not yet tested** | Run `./helper probe` |
| SAM 3.1 segmentation | **Availability unknown** | `./helper probe` checks the model list only |
| Meta speech-to-text | **Availability unknown** | `./helper probe` checks the model list only |

The cloud development session used on 2026-10-29 could not reach `api.meta.ai` because its network policy blocked the host, and it had no key. All probes must run on the entrant's machine, or in a session where that host is allowed.

## Running the probes

```bash
./helper probe --no-image   # model list only; no inference call
./helper probe              # also one Muse Spark call with the fictional appointment card
```

The result is saved to `workspace/probes/probe_<timestamp>.json`. It contains the endpoint, the listed model IDs, and the image call's response ID, model, token usage, extracted fields and per-field pass/fail. It contains no key and no remote error bodies.

How to read the outcome:

- `image_input.status = PASSED`: Muse Spark read the card, and every expected field matched.
- `MODEL_RESPONDED_FIELDS_MISMATCH`: inference succeeded, but at least one field was wrong. Record it as a quality finding, not a pass.
- `REQUEST_REJECTED_OR_FAILED`: the request shape (`input_image` with a data URL) may not be supported. Check the HTTP status hint and Meta's documentation before changing the request.
- For SAM and speech, `LISTED` only means a model ID appeared. Each still needs its documented request format and a successful call before the project can say it is integrated.
