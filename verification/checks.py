def verify_checklist(items):
    ok = isinstance(items, list) and 4 <= len(items) <= 8
    return {'ok': ok, 'count': len(items) if isinstance(items, list) else 0}
def verify_fact_quote(src, q):
    ok = bool(q and str(q).strip() in str(src))
    return {'ok': ok, 'verified_quote': str(q).strip() if ok else ''}
def verify_memo_submission(chk_ok, sig_ok, val=0, expected=0):
    if not (chk_ok and sig_ok): return {'ok': False, 'status': 'needs_input'}
    return {'ok': True, 'status': 'awaiting_signoff'}
