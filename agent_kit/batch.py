"""Owner-approved live verification batch with a hard spending cap.

Spending is enforced *before* every paid call: the batch stops if the cost so
far plus a deliberately high estimate of the next call would exceed the cap.
Cost so far is computed from Meta's own usage receipts at Standard-mode list
prices, charging cached input at the full input rate and every output token
(including reasoning) at the output rate, so it can only overstate the bill.

A scenario passes only if the saved run reached its expected final state and
satisfied every independent check; a Meta response alone is not a pass.
"""
from __future__ import annotations
import hashlib
import json
import os
from contextlib import contextmanager
from pathlib import Path
from unittest import mock
from agent_kit import client, evidence, progress, settings, speech
from harvey_agent.loop import approve_run, run_agent

# Standard-mode list prices, dev.meta.ai/docs/pricing-rate-limits (read 2026-10-29), USD per token.
INPUT_USD = 1.25 / 1_000_000
OUTPUT_USD = 4.25 / 1_000_000
MAX_OUTPUT_TOKENS = 4096          # agent_kit.client caps every response at this
FIRST_CALL_INPUT_BOUND = 20_000   # measured first-turn requests are far smaller
NEXT_CALL_GROWTH_BOUND = 8_000    # one tool observation plus an attached image
CARD, CONFLICT, CLINIC = 'healthcare-appointment-card', 'healthcare-card-contradiction', 'healthcare-clinic-visit'


def receipt_cost(receipt):
    usage = receipt.get('usage') or {}
    return (usage.get('input_tokens') or 0) * INPUT_USD + (usage.get('output_tokens') or 0) * OUTPUT_USD


def next_call_bound(record):
    last = record['receipts'][-1]['usage'].get('input_tokens', 0) if record.get('receipts') else 0
    tokens_in = last + NEXT_CALL_GROWTH_BOUND if last else FIRST_CALL_INPUT_BOUND
    return tokens_in * INPUT_USD + MAX_OUTPUT_TOKENS * OUTPUT_USD


class Ledger:
    """Tracks spending across the whole batch and refuses calls that could pass the cap."""
    def __init__(self, cap_usd):
        self.cap = float(cap_usd)
        self.closed = 0.0          # finished runs and transcriptions
        self.calls = 0
        self.stopped = None

    def spent(self, record=None):
        return self.closed + (sum(receipt_cost(r) for r in record['receipts']) if record else 0.0)

    def guard(self, record):
        projected = self.spent(record) + next_call_bound(record)
        if projected > self.cap:
            self.stopped = f'Spending limit: ${self.spent(record):.4f} spent + ${next_call_bound(record):.4f} next-call bound exceeds ${self.cap:.2f} cap'
            return self.stopped
        self.calls += 1
        return None

    def close_run(self, record):
        self.closed += sum(receipt_cost(r) for r in record['receipts'])


@contextmanager
def _no_network():
    def refuse(*_args, **_kwargs):
        raise AssertionError('Network access attempted during the no-cost failure test')
    with mock.patch('urllib.request.OpenerDirector.open', side_effect=refuse) as opened:
        yield opened


def _check(name, ok, detail=''):
    return {'check': name, 'passed': bool(ok), 'detail': detail}


def _common(record):
    model_turns = [t for t in record['turns'] if t.get('tool') != 'api_error']
    return [
        _check('labeled live only after Meta answered', record['inference_mode'] == 'LIVE_META_API' and record['model_invoked_in_run']),
        _check('one receipt per model turn', len(record['receipts']) == len(model_turns) and all(t.get('receipt') for t in model_turns),
               f"{len(record['receipts'])} receipts, {len(model_turns)} model turns"),
        _check('no API error', not any(t.get('tool') == 'api_error' for t in record['turns'])),
        _check('dispatch disabled, no authorization', record['dispatch_enabled'] is False and record['authorization_mode'] == 'NONE' and not record.get('human_signoff_token')),
    ]


def _failed_checks(record):
    return sorted(k for k, v in record['verification'].items() if not v['passed'])


def _memo_cites(record, document):
    facts = {f['id']: f for f in record['facts']}
    return bool(record.get('memo')) and any(facts.get(fid, {}).get('document') == document
                                            for finding in record['memo']['findings'] for fid in finding['fact_ids'])


def accept_card(record):
    extraction = record.get('card_extraction') or {}
    return _common(record) + [
        _check('final status awaiting_signoff', record['status'] == 'awaiting_signoff', record['status']),
        _check('card fields recorded by the live model', extraction.get('extracted_by') == 'LIVE_META_API', str(extraction.get('fields'))),
        _check('all independent checks pass', record['verification'] and not _failed_checks(record), str(_failed_checks(record))),
        _check('card check present and passed', record['verification'].get('appointment_card_check', {}).get('passed') is True),
        _check('memo cites the card image', _memo_cites(record, 'appointment_card.png')),
    ]


def accept_conflict(root, record):
    extraction = record.get('card_extraction') or {}
    card = record['verification'].get('appointment_card_check', {})
    try:
        approve_run(root, record['run_id'], 'Batch acceptance probe')
        refused = False
    except ValueError:
        refused = True
    return _common(record) + [
        _check('final status needs_input', record['status'] == 'needs_input', record['status']),
        _check('card fields recorded by the live model', extraction.get('extracted_by') == 'LIVE_META_API', str(extraction.get('fields'))),
        _check('only the card check fails', _failed_checks(record) == ['appointment_card_check'], str(_failed_checks(record))),
        _check('card check cites the date difference', 'differs from request date' in card.get('reason', ''), card.get('reason', '')),
        _check('no memo accepted', record.get('memo') is None),
        _check('human approval refused', refused),
    ]


def accept_spoken(record):
    source = record.get('speech_source') or {}
    return _common(record) + [
        _check('final status awaiting_signoff', record['status'] == 'awaiting_signoff', record['status']),
        _check('transcript produced by Meta speech-to-text', isinstance(source, dict) and source.get('model') == speech.MODEL and bool(source.get('session_id')), str(source.get('session_id'))),
        _check('spoken request check passed', record['verification'].get('spoken_request_check', {}).get('passed') is True),
        _check('all independent checks pass', record['verification'] and not _failed_checks(record), str(_failed_checks(record))),
        _check('memo quotes the spoken request', _memo_cites(record, evidence.SPOKEN_REQUEST)),
    ]


def accept_failure(record, network_calls):
    return [
        _check('run paused on the API error', record['status'] == 'paused' and record['turns'][-1].get('tool') == 'api_error', record.get('pause_reason', '')),
        _check('never labeled live', record['inference_mode'] == 'NOT_INVOKED' and not record['model_invoked_in_run']),
        _check('no receipts, no memo', not record['receipts'] and record.get('memo') is None),
        _check('zero network calls', network_calls == 0, str(network_calls)),
    ]


def _summary(name, record, checks, ledger_cost):
    usage = [r.get('usage') or {} for r in record['receipts']]
    public = json.dumps(progress.public_record(record), sort_keys=True).encode()
    return {'scenario': name, 'run_id': record['run_id'], 'case': record['case'], 'status': record['status'],
            'turns': record['turn'], 'receipts': len(record['receipts']),
            'first_response_id': record['receipts'][0]['response_id'] if record['receipts'] else None,
            'last_response_id': record['receipts'][-1]['response_id'] if record['receipts'] else None,
            'input_tokens': sum(u.get('input_tokens') or 0 for u in usage),
            'cached_input_tokens': sum((u.get('input_tokens_details') or {}).get('cached_tokens') or 0 for u in usage),
            'output_tokens': sum(u.get('output_tokens') or 0 for u in usage),
            'estimated_cost_usd': round(ledger_cost, 4), 'failed_checks': _failed_checks(record),
            'speech_source': record.get('speech_source'), 'pause_reason': record.get('pause_reason') or None,
            'acceptance': checks, 'passed': all(c['passed'] for c in checks),
            'audit_sha256': hashlib.sha256(public).hexdigest()}


def _is_api_error(record):
    return record['status'] == 'paused' and bool(record['turns']) and record['turns'][-1].get('tool') == 'api_error'


def run(root, cap_usd=5.0, max_turns=30, api=None, transcribe=None):
    """Failure path first (free), then card, contradiction and spoken request, stopping on API errors or the cap.

    `api` and `transcribe` replace the Meta connections in offline tests only.
    """
    transcribe = transcribe or speech.transcribe
    settings.load_env(root)
    root = Path(root)
    started_at = progress.now()
    ledger = Ledger(cap_usd)
    results, stop_reason = [], None

    # 1. Authentication failure path: no key at all, network blocked, so nothing can be billed.
    saved = os.environ.get('MODEL_API_KEY')
    os.environ['MODEL_API_KEY'] = ''
    try:
        with _no_network() as opened:
            record = run_agent(root, turns=1, case_name=CARD, mode='live')
        results.append(_summary('authentication failure (no key)', record, accept_failure(record, opened.call_count), 0.0))
    finally:
        if saved is None:
            os.environ.pop('MODEL_API_KEY', None)
        else:
            os.environ['MODEL_API_KEY'] = saved

    scenarios = [('appointment card', CARD, None, accept_card),
                 ('card contradiction', CONFLICT, None, lambda r: accept_conflict(root, r)),
                 ('spoken request (Meta speech-to-text)', CLINIC, speech.DEMO_AUDIO, accept_spoken)]
    for name, case, audio, accept in scenarios:
        spoken = source = None
        if audio:
            seconds = speech.wav_info((root / audio).read_bytes())['seconds']
            bound = (int(seconds) + 2) * speech.USD_PER_HOUR / 3600
            if ledger.spent() + bound > ledger.cap:
                stop_reason = f'Spending limit reached before transcription of {audio}'
                break
            try:
                heard = transcribe((root / audio).read_bytes())
            except client.ModelError as error:
                stop_reason = f'Speech-to-text API error: {error}'
                results.append({'scenario': name, 'status': 'transcription_failed', 'passed': False, 'error': str(error)})
                break
            ledger.calls += 1
            ledger.closed += heard['cost_usd_estimate'] or bound
            spoken = heard['transcript']
            source = {k: heard[k] for k in ('model', 'session_id', 'audio_duration_ms', 'latency_ms', 'billed_seconds_estimate', 'cost_usd_estimate')}
        before = ledger.spent()
        record = run_agent(root, turns=max_turns, case_name=case, mode='live', spoken_request=spoken,
                           speech_source=source, before_call=ledger.guard, api=api(case) if api else None)
        ledger.close_run(record)
        cost = ledger.spent() - before + ((source or {}).get('cost_usd_estimate') or 0)
        results.append(_summary(name, record, accept(record), cost))
        if ledger.stopped:
            stop_reason = ledger.stopped
            break
        if _is_api_error(record):
            stop_reason = f'API error in {name}: {record.get("pause_reason")}'
            break

    report = {'batch_version': 1, 'started_at': started_at, 'timestamp': progress.now(), 'cap_usd': ledger.cap, 'max_turns': max_turns,
              'paid_calls': ledger.calls, 'estimated_cost_usd': round(ledger.spent(), 4),
              'pricing_basis': 'Standard-mode list prices; cached input charged as full input; reasoning charged as output',
              'stopped_early': stop_reason, 'scenarios': results,
              'all_passed': not stop_reason and len(results) == 4 and all(r.get('passed') for r in results)}
    path = root / 'workspace' / 'batch' / ('batch_' + report['timestamp'].replace(':', '').replace('+', '_') + '.json')
    progress.atomic_write(path, report)
    report['saved_to'] = str(path.relative_to(root))
    return report
