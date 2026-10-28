from __future__ import annotations
from pathlib import Path
from agent_kit import settings

def verify_exact_quote(root: str | Path, case_name: str, doc_name: str, claimed_quote: str) -> dict:
    fpath = Path(root) / 'cases' / case_name / 'inbox' / doc_name
    if not fpath.exists():
        return {'passed': False, 'reason': f'Missing document {doc_name}'}
    content = fpath.read_text()
    passed = bool(claimed_quote and claimed_quote.strip() in content)
    return {'passed': passed, 'doc_name': doc_name, 'claimed_quote': claimed_quote, 'reason': 'Exact verbatim quote verified' if passed else 'Quote not found verbatim'}

def verify_fare_invariant(miles: float, claimed_total: float, claimed_ada_fee: float = 0.0) -> dict:
    expected = settings.calculate_verified_fare(miles)
    total_ok = abs(claimed_total - expected['total_fare']) < 0.005
    ada_ok = abs(claimed_ada_fee - 0.0) < 0.005
    passed = total_ok and ada_ok
    reasons = []
    if not total_ok:
        reasons.append(f"Fare drift: claimed ${claimed_total:.2f} != expected ${expected['total_fare']:.2f}")
    if not ada_ok:
        reasons.append(f'Illegal ADA surcharge: ${claimed_ada_fee:.2f} (must be $0.00)')
    return {'passed': passed, 'expected_fare': expected['total_fare'], 'claimed_fare': claimed_total, 'formula': expected['formula'], 'reason': 'Fare invariant satisfied' if passed else '; '.join(reasons)}

def verify_curb_safety(clearance_ft: float) -> dict:
    passed = clearance_ft >= settings.MIN_RAMP_CLEARANCE_FT
    return {'passed': passed, 'clearance_ft': clearance_ft, 'required_ft': settings.MIN_RAMP_CLEARANCE_FT, 'reason': f'SAFE ({clearance_ft:.1f}ft >= 8.0ft)' if passed else f'UNSAFE BOARDING: {clearance_ft:.1f}ft < 8.0ft minimum ADA ramp clearance'}

def verify_run_record(record: dict) -> dict:
    errors = []
    turns = record.get('turns', [])
    seq = [t.get('tool') for t in turns]
    if len(turns) < 4 or seq[:3] != ['list_documents', 'set_checklist', 'analyze_documents']:
        errors.append(f'Invalid 4-turn sequence: {seq}')
    if record.get('status') == 'completed' and not record.get('human_signoff_token'):
        errors.append('Premature completion without human_signoff_token')
    if not record.get('counter_evidence_checked'):
        errors.append('Counter-evidence check missing')
    return {'passed': len(errors) == 0, 'errors': errors}

def verify_checklist(items: list) -> bool:
    return isinstance(items, list) and 4 <= len(items) <= 8

def verify_fact_quote(quote: str, source_text: str) -> bool:
    return bool(quote and source_text and quote.strip() in source_text)

def verify_memo_submission(record: dict) -> bool:
    return verify_run_record(record)['passed']
