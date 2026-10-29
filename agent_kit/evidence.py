"""Case-scoped source evidence and independent, fail-closed booking checks."""
from __future__ import annotations
import hashlib
import json
import math
import re
from pathlib import Path
from agent_kit import settings


def case_path(root, case):
    if not isinstance(case, str) or not re.fullmatch(r'[a-zA-Z0-9_-]+', case):
        raise ValueError('Invalid case name')
    base = (Path(root) / 'cases').resolve()
    if (base / case).is_symlink() or (base / case / 'inbox').is_symlink():
        raise ValueError('Symlink case evidence is not supported')
    path = (base / case).resolve()
    if path.parent != base or not (path / 'inbox').is_dir():
        raise ValueError(f'Unknown or unsupported case: {case}')
    return path


def documents(root, case):
    inbox = case_path(root, case) / 'inbox'
    result = {}
    for path in sorted(inbox.iterdir()):
        if path.is_symlink() or path.name.startswith('.') or path.suffix not in ('.txt', '.md', '.json'):
            continue
        if path.is_file():
            if path.stat().st_size > 200_000:
                raise ValueError('Evidence document too large')
            result[path.name] = path.read_text()
    return result


def digest(docs):
    return hashlib.sha256(json.dumps(docs, sort_keys=True).encode()).hexdigest()


def _reject_constant(value):
    raise ValueError('Nonfinite JSON evidence is invalid')


def inspect(root, case):
    from verification import checks
    docs = documents(root, case)
    fields = dict(line.split(':', 1) for line in docs.get('rider_intake.txt', '').splitlines() if ':' in line)
    fields = {k.strip(): v.strip() for k, v in fields.items()}
    missing = [k for k in ('Rider', 'Pickup', 'Dropoff', 'Pickup Time', 'Verified Distance', 'Quoted Fare')
               if not fields.get(k) or fields[k].startswith('MISSING_')]
    mileage = re.fullmatch(r'(\d+(?:\.\d+)?)\s*miles?', fields.get('Verified Distance', ''), re.I)
    fare = re.match(r'^\$(\d+(?:\.\d{1,2})?)(?=\s|$|\()', fields.get('Quoted Fare', ''))
    miles = float(mileage[1]) if mileage else None
    total = float(fare[1]) if fare else None
    if miles is None and 'Verified Distance' not in missing:
        missing.append('Verified Distance')
    if total is None and 'Quoted Fare' not in missing:
        missing.append('Quoted Fare')
    # Reject any positive surcharge explicitly associated with an accessibility fee.
    quoted = fields.get('Quoted Fare', '')
    fees = re.findall(r'\$(\d+(?:\.\d+)?)\s*(?:ADA|wheelchair|service(?:[- ]animal| dog)?)\b', quoted, re.I)
    fee = max([float(x) for x in fees], default=0.0)
    fare_check = checks.verify_fare_invariant(miles, total, fee) if miles is not None and total is not None else {'passed': False, 'reason': 'Missing verified mileage or quoted fare', 'expected_fare': None, 'formula': None}
    quote = '$2.50 base component plus $1.50 per verified mile.'
    quote_check = {'passed': quote in docs.get('HANDBOOK.md', ''), 'reason': 'Demo fare policy must contain the exact tariff quotation', 'claimed_quote': quote}
    try:
        telemetry = json.loads(docs.get('curb_telemetry.json', '{}'), parse_constant=_reject_constant)
        if not isinstance(telemetry, dict):
            telemetry = {}
    except ValueError:
        telemetry = {}
    selected = telemetry.get('selected_bay')
    bay = telemetry.get(selected, {}) if isinstance(selected, str) else {}
    bay = bay if isinstance(bay, dict) else {}
    clearance = bay.get('clearance_ft')
    valid = checks.finite(clearance)
    curb_check = checks.verify_curb_safety(clearance) if valid else {'passed': False, 'reason': 'Missing finite clearance telemetry', 'clearance_ft': None}
    if bay.get('safe_for_ramp') is not True or 'OBSTRUCTED' in str(bay.get('status', '')).replace('UNOBSTRUCTED', ''):
        curb_check.update(passed=False, reason='Selected bay is obstructed or not explicitly safe in supplied telemetry')
    contradiction = 'CONTRADICTION' in json.dumps(telemetry) or bool(re.search(r'\b(ignore|override|without human|without sign.off)\b', fields.get('Dispatcher Override Note', ''), re.I))
    counter = [{'bay': k, **v} for k, v in telemetry.items() if isinstance(v, dict) and k != selected]
    checks_out = {'intake_check': {'passed': not missing, 'missing_fields': missing},
                  'quote_check': quote_check, 'fare_check': fare_check, 'curb_check': curb_check,
                  'counter_evidence_check': {'passed': not contradiction, 'contradiction': contradiction, 'other_bays': counter}}
    if fields.get('Trip Purpose'):
        healthcare_missing = [key for key in ('Coordinator Contact', 'Appointment Time', 'Return Plan', 'Vehicle Capability')
                              if not fields.get(key) or fields[key].startswith('MISSING_')]
        clinical = fields.get('Clinical Support Required', '').lower()
        capability = fields.get('Vehicle Capability', '').startswith('CONFIRMED')
        checks_out['healthcare_transport_check'] = {
            'passed': not healthcare_missing and clinical == 'no' and capability,
            'missing_fields': healthcare_missing,
            'reason': ('Transport coordination details supplied; no clinical support requested'
                       if not healthcare_missing and clinical == 'no' and capability else
                       'Resolve return plan, coordinator or vehicle details; clinical-support requests require an appropriate human service'),
            'scope': 'Transportation logistics only; not clinical clearance or emergency response'}
    return {'checks': checks_out, 'passed': all(x['passed'] for x in checks_out.values()),
            'rider': fields.get('Rider'), 'selected_bay': selected,
            'evidence_digest': digest(docs), 'telemetry_source': 'simulation_fixture',
            'policy_scope': 'Demo fleet policy; not a universal legal clearance standard'}
