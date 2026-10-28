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


def verify_checklist(items):
    return isinstance(items, list) and 4 <= len(items) <= 8


def verify_fact_quote(quote, source_text):
    return isinstance(quote, str) and bool(quote.strip()) and quote in source_text


def verify_memo_submission(record):
    return verify_run_record(record)['passed']
