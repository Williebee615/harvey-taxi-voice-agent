"""Independent numerical and source verification for the demo fleet policy."""
import math
from agent_kit import evidence, settings


def verify_exact_quote(root, case_name, doc_name, claimed_quote):
    text = evidence.documents(root, case_name).get(doc_name, '')
    passed = verify_fact_quote(claimed_quote, text)
    return {'passed': passed, 'doc_name': doc_name, 'claimed_quote': claimed_quote,
            'reason': 'Exact quote verified' if passed else 'Quote not found verbatim'}


def finite(value):
    try:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    except (OverflowError, ValueError):
        return False


def verify_fare_invariant(miles, claimed_total, claimed_ada_fee=0.0):
    if not all(finite(x) for x in (miles, claimed_total, claimed_ada_fee)) or miles < 0:
        return {'passed': False, 'reason': 'Invalid finite fare inputs', 'expected_fare': None, 'formula': None}
    expected = settings.calculate_verified_fare(miles)
    total_ok = abs(claimed_total - expected['total_fare']) < 0.005
    ada_ok = claimed_ada_fee == 0
    reasons = []
    if not total_ok:
        reasons.append('Fare drift: quoted total differs from demo tariff')
    if not ada_ok:
        reasons.append('Accessibility surcharge must be $0.00 under demo policy')
    return {'passed': total_ok and ada_ok, 'expected_fare': expected['total_fare'], 'claimed_fare': claimed_total,
            'formula': expected['formula'], 'reason': '; '.join(reasons) or 'Fare invariant satisfied'}


def verify_curb_safety(clearance_ft):
    passed = finite(clearance_ft) and clearance_ft >= settings.MIN_RAMP_CLEARANCE_FT
    return {'passed': passed, 'clearance_ft': clearance_ft if finite(clearance_ft) else None,
            'required_ft': settings.MIN_RAMP_CLEARANCE_FT, 'reason': 'Demo fleet clearance met' if passed else 'Missing or insufficient demo fleet clearance'}


def verify_run_record(record):
    checks = record.get('verification', {})
    errors = []
    if not checks or not all(x.get('passed') is True for x in checks.values()):
        errors.append('Independent checks incomplete or failed')
    if record.get('status') == 'completed_after_human_signoff' and not record.get('human_signoff_token'):
        errors.append('Missing reviewer')
    if not record.get('memo'):
        errors.append('Cited memo missing')
    return {'passed': not errors, 'errors': errors}


FINAL_STATES = ('needs_input', 'awaiting_signoff', 'completed_after_human_signoff')
INTEGRITY_SCOPE = 'Audit record consistency for this final state; not a booking approval'


def audit_integrity(root, record):
    """Check that a run's audit record is internally consistent for the state it ended in.

    A correct needs_input stop passes; integrity is about the record, not the booking.
    """
    status = record.get('status')
    if status not in FINAL_STATES:
        return {'passed': False, 'state': status, 'scope': INTEGRITY_SCOPE,
                'errors': ['Not verified yet: integrity is checked when the run reaches needs_input or awaiting_signoff']}
    errors = []
    model_turns = [t for t in record.get('turns', []) if t.get('tool') != 'api_error']
    receipts = record.get('receipts', [])
    if record.get('requested_mode') == 'live':
        if record.get('inference_mode') != 'LIVE_META_API' or not record.get('model_invoked_in_run'):
            errors.append('Live run reached a final state without a recorded Meta response')
        if len(receipts) != len(model_turns) or not all(t.get('receipt', {}).get('response_id') for t in model_turns):
            errors.append('Every model turn needs exactly one Meta receipt with a response ID')
    elif receipts or record.get('model_invoked_in_run') or record.get('inference_mode') != 'DETERMINISTIC_FALLBACK_SIMULATION':
        errors.append('Simulation run carries live-inference provenance')
    if record.get('telemetry_source') != 'simulation_fixture':
        errors.append('Curb telemetry source is not declared')
    if record.get('dispatch_enabled') is not False:
        errors.append('Dispatch must remain disabled')
    signed = status == 'completed_after_human_signoff'
    signoff_fields = (record.get('authorization_mode'), bool(record.get('human_signoff_token')), bool(record.get('signed_at')))
    if signoff_fields != (('SIMULATED_DISPATCHER_SIGNOFF', True, True) if signed else ('NONE', False, False)):
        errors.append('Sign-off fields do not match the final state')
    docs = evidence.run_documents(root, record['case'], record.get('run_documents'))
    current = evidence.current_digest(root, record['case'], record.get('run_documents'))
    for fact in record.get('facts', []):
        if fact.get('kind') == 'image_fields':
            ok = fact.get('fields') == (record.get('card_extraction') or {}).get('fields')
        else:
            ok = isinstance(fact.get('quote'), str) and fact['quote'] in docs.get(fact.get('document'), '')
        if not ok or fact.get('source_digest') != current:
            errors.append(f"Fact {fact.get('id')} no longer matches current source evidence")
    checks = record.get('verification') or {}
    failed = sorted(k for k, v in checks.items() if not v.get('passed'))
    if checks and record.get('verified_digest') != current:
        errors.append('Independent checks were run against different evidence')
    if status == 'needs_input':
        if record.get('memo') is not None:
            errors.append('A needs_input run must not hold an accepted memo')
        if not failed and not record.get('evidence_requests'):
            errors.append('needs_input without a failed check or an evidence request')
    else:
        if not record.get('memo') or not checks or failed:
            errors.append('Sign-off states need an accepted memo and all independent checks passing')
    return {'passed': not errors, 'state': status, 'scope': INTEGRITY_SCOPE, 'failed_checks': failed,
            'evidence_requested': bool(record.get('evidence_requests')), 'errors': errors}


def verify_checklist(items):
    return isinstance(items, list) and 4 <= len(items) <= 8


def verify_fact_quote(quote, source_text):
    return isinstance(quote, str) and bool(quote.strip()) and quote in source_text


def verify_memo_submission(record):
    return verify_run_record(record)['passed']
