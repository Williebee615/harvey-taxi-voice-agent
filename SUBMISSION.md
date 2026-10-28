# Harvey Taxi — Accessible Care Transportation Review

## Submission status

The project and two live outcome audits have been reviewed. The required three-minute video is not recorded/linked yet, and the final form has not been submitted. Confirm the participant/team list and track in the event platform before submission. No paid hosting is required by the participant guide supplied to the project.

- Public source: https://github.com/Williebee615/harvey-taxi-voice-agent/tree/main
- Upgrade/contribution diff: https://github.com/Williebee615/harvey-taxi-voice-agent/pull/3
- Demo video: **PENDING — add the accessible recording URL before submission**
- Representative: Willie Harvey IV
- Additional contributors and track: confirm against the entrant's event registration; do not infer them from company ownership or AI assistance.

## Short description

Harvey Taxi uses Meta Muse Spark to investigate accessible healthcare transportation requests, cite source evidence, check fares and pickup conditions, and prepare a memo for human review. Missing return plans are escalated instead of silently accepted.

## Problem and impact

A ride request needs more than a destination. For a wheelchair user traveling to a clinic, the coordinator must establish pickup and appointment details, a suitable vehicle, a fare and a return coordination plan. Harvey Taxi brings firsthand transportation experience to an agent that makes those questions and their supporting evidence visible before human review.

The prototype's demonstrated impact is catching incomplete or contradictory transport evidence in fictional cases. Reduced coordinator effort, better rider experience and fewer missed appointments are future evaluation goals, not measured results.

## How Meta is used

In live mode, `muse-spark-1.3` chooses function tools through Meta's Responses API. It lists and reads case files, creates an investigation checklist, records exact quotations, requests independent verification and submits a cited memo. Tool observations feed back into the same conversation. Run records expose actual provider response IDs, model identifiers and usage metadata.

Code independently verifies intake, the supplied fare tariff, zero accessibility surcharge, selected-bay fixture evidence, counter-evidence and healthcare transport coordination fields. Every memo finding must cite current, case-scoped facts. The model cannot authorize dispatch or manufacture a human signature.

## Verified demo outcomes

1. Clinic visit: a live run reached `awaiting_signoff` after 24 tool turns with no recorded tool refusal or retry. Its final citations and source digest matched the files; a separate demo acknowledgment produced `completed_after_human_signoff`.
2. Missing return plan: a live run ended in `needs_input`; the healthcare check identified `Return Plan` as missing. No human signoff was recorded and dispatch remained disabled.

See [the acceptance record](docs/LIVE_ACCEPTANCE.md). The public audit omits conversation messages, so it does not independently prove the absence of follow-up messages.

## Work developed for this entry

The upgrade replaces the earlier canned browser trace and fixed scripted booking path with live Meta orchestration, exact source verification, run-bound citations, independent memo gates, resumable audits, a connected local console and healthcare transportation fixtures. The PR and dated commits identify the changed files and contribution boundary.

The earlier Harvey Taxi business, workshop starter concepts and historical Fireworks receipts are not presented as newly created integrations. Confirm build dates and eligibility against the accepted event rules; do not describe all preexisting repository content as new work.

## Demonstration boundaries

- Real model inference: Meta Muse Spark through the API.
- Simulated input: fictional rider cases and curb measurements. No live SAM segmentation or physical measurement is implemented.
- Human acknowledgment: a typed demo reviewer name, not authenticated operational authority.
- Not implemented: clinical advice, medical clearance, live speech transcription, EHR integration, real dispatch or payments.
- The 8ft clearance threshold and fare are the supplied demo fleet policy, not universal legal standards.

## How judges can run it

Use Python 3.10+. From the contest branch:

```bash
./helper test
./helper serve
```

Open http://127.0.0.1:8765. Offline simulation needs no key. For live mode, configure a private local `MODEL_API_KEY` from the judge's own Meta account; never commit or share a key. The repository and video must be accessible without relying on the submitter's Mac or private API credentials. GitHub Pages is not the live Python agent.
