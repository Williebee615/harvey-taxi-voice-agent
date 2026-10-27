from __future__ import annotations
def verify_checklist(items):
    if not isinstance(items, list) or not (4 <= len(items) <= 8):
        return {'ok': False, 'error': 'Checklist must have 4 to 8 items'}
    has_sig = any(isinstance(x, dict) and x.get('requires_signature') for x in items)
    has_counter = any(isinstance(x, dict) and x.get('points_other_way') for x in items)
    if not (has_sig and has_counter):
        return {'ok': False, 'error': 'Missing requires_signature or points_other_way item'}
    return {'ok': True, 'count': len(items)}

def verify_fact_quote(source_text, quote):
    if not quote or str(quote).strip() not in str(source_text):
        return {'ok': False, 'error': 'Exact quote not found in source document'}
    return {'ok': True, 'verified_quote': str(quote).strip()}

def verify_memo_submission(checklist_ok, signatures_ok, fare_usd, miles=6):
    expected = round(2.50 + (1.50 * miles), 2)
    if not checklist_ok or not signatures_ok:
        return {'ok': False, 'status': 'needs_input', 'error': 'Checklist or signatures incomplete'}
    if abs(float(fare_usd) - expected) > 0.001:
        return {'ok': False, 'status': 'running', 'error': f'Fare mismatch: expected {expected}'}
    return {'ok': True, 'status': 'awaiting_signoff', 'verified_fare_usd': expected}
