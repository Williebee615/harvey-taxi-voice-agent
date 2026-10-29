# Demonstration evidence: hosted console runs, 2026-10-29

**These are hackathon demonstration records, not production data.** The rider, clinic and appointment are fictional, and the curb measurements are simulated fixtures. No vehicle was dispatched and no payment was taken. The only real name is the owner's: Willie Harvey IV recorded the demo sign-off, and he is named in his own spoken request.

The owner ran both reviews in **Live Meta** mode on the password-protected Modal console and exported them with **Download audit JSON**. They are stored unchanged, apart from JSON formatting.

| File | What it shows | Console version |
|---|---|---|
| `run_b2023b2da615466fba74a611b17ec923.json` | Standard ride: 24 live Muse Spark turns, all 6 checks pass, signed off | `c7c1f1a` |
| `run_0e228025cdfe4b6397add01fc117c7eb.json` | Standard ride with the owner's spoken request: Meta speech-to-text from a real microphone, confirmed by the reviewer; 27 live turns; all 7 checks pass, including the spoken-request check; audit integrity passed; signed off | `778b740` |

Each file is the application's public record: every Meta receipt (response ID, model, status, token usage, latency), every tool call with its arguments and observed result, facts, independent checks, the memo, sign-off and timestamps. It does not include the raw conversation, encrypted reasoning, system instructions or image bytes. A scan finds no credentials.

## Audit fingerprints

The SHA-256 of each record as compact JSON with sorted keys:

| Run | SHA-256 |
|---|---|
| `run_b2023b2d…` | `3ef9b71dde864d5ad85997013318e1110b241763d412c2af992866d4a8ff5465` |
| `run_0e228025…` | `eac7cd674552a2a42d2413a6520d7ba67829219f896730777328746a65465576` |

To check them, use the command in [`../live-batch-2026-10-29/README.md`](../live-batch-2026-10-29/README.md) with this folder's path.

Response IDs are the ones Meta returned, as saved by the application. They are checked for presence and uniqueness, not authenticated with Meta.
