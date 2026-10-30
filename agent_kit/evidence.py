"""Case-scoped source evidence and independent, fail-closed booking checks."""
from __future__ import annotations
import hashlib
import json
import math
import re
from pathlib import Path
from agent_kit import schedule, settings


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


IMAGE_TYPES = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg'}
MAX_IMAGE_BYTES = 2_000_000
SPOKEN_REQUEST = 'spoken_request.txt'
MAX_SPOKEN_CHARS = 2_000


def images(root, case):
    """Image evidence in the case inbox. Bytes are never treated as text or quotations."""
    inbox = case_path(root, case) / 'inbox'
    result = {}
    for path in sorted(inbox.iterdir()):
        if path.is_symlink() or path.name.startswith('.') or path.suffix.lower() not in IMAGE_TYPES or not path.is_file():
            continue
        if path.stat().st_size > MAX_IMAGE_BYTES:
            raise ValueError('Evidence image too large')
        result[path.name] = path.read_bytes()
    return result


def run_documents(root, case, extra=None):
    """Case files plus run-scoped text evidence such as a spoken request transcript."""
    docs = documents(root, case)
    for name, text in (extra or {}).items():
        if name in docs or name != SPOKEN_REQUEST:
            raise ValueError('Unsupported run document')
        docs[name] = text
    return docs


def digest(docs, imgs=None):
    # Text-only cases keep the original digest, so earlier audit digests remain comparable.
    payload = docs if not imgs else {'documents': docs, 'images': {k: hashlib.sha256(v).hexdigest() for k, v in imgs.items()}}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def current_digest(root, case, extra=None):
    return digest(run_documents(root, case, extra), images(root, case))


def card_images(imgs):
    return sorted(name for name in imgs if name.startswith('appointment_card'))


CARD_FIELDS = ('appointment_date', 'appointment_time', 'arrive_by', 'destination')
_DATE_TIME = re.compile(r'(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})')


def _valid_fields(fields):
    """Return the fields that are present and well formed; anything else counts as unreadable."""
    from datetime import date
    good = {}
    for key in CARD_FIELDS:
        value = fields.get(key) if isinstance(fields, dict) else None
        if not isinstance(value, str) or not value.strip():
            continue
        value = value.strip()
        if key == 'appointment_date':
            try:
                date.fromisoformat(value)
            except ValueError:
                continue
        elif key in ('appointment_time', 'arrive_by') and not re.fullmatch(r'([01]\d|2[0-3]):[0-5]\d', value):
            continue
        good[key] = value
    return good


def _place(text):
    first = (text or '').split(',')[0].lower().replace('(fictional)', '')
    return re.sub(r'[^a-z0-9]+', ' ', first).strip()


def card_check(intake, extraction, digest_now):
    """Cross-check model-extracted card fields against the written rider request. Code decides; the model only reads."""
    result = {'passed': False, 'contradictions': [], 'unreadable': [], 'card_fields': None,
              'extracted_by': None, 'scope': 'Fictional demo card; transportation logistics only'}
    if not extraction:
        return {**result, 'reason': 'Appointment card has not been read and extracted in this run'}
    result.update(card_fields=extraction.get('fields'), extracted_by=extraction.get('extracted_by'))
    if extraction.get('source_digest') != digest_now:
        return {**result, 'reason': 'Card extraction is stale: evidence changed after it was recorded'}
    fields = _valid_fields(extraction.get('fields'))
    result['unreadable'] = [k for k in CARD_FIELDS if k not in fields]
    problems = result['contradictions']
    appointment = _DATE_TIME.search(intake.get('Appointment Time', ''))
    pickup = _DATE_TIME.search(intake.get('Pickup Time', ''))
    if not appointment:
        problems.append('Rider request has no appointment date and time to compare with the card')
    else:
        if 'appointment_date' in fields and fields['appointment_date'] != appointment[1]:
            problems.append(f"Card date {fields['appointment_date']} differs from request date {appointment[1]}")
        if 'appointment_time' in fields and fields['appointment_time'] != appointment[2]:
            problems.append(f"Card appointment time {fields['appointment_time']} differs from request time {appointment[2]}")
    if 'arrive_by' in fields and 'appointment_time' in fields and fields['arrive_by'] > fields['appointment_time']:
        problems.append('Card arrive-by time is after the appointment time')
    if pickup and 'appointment_date' in fields and 'arrive_by' in fields:
        if pickup[1] != fields['appointment_date']:
            problems.append(f"Pickup date {pickup[1]} differs from card date {fields['appointment_date']}")
        elif pickup[2] >= fields['arrive_by']:
            problems.append(f"Pickup time {pickup[2]} is not before the card's arrive-by time {fields['arrive_by']}")
    if 'destination' in fields and _place(fields['destination']) != _place(intake.get('Dropoff', '')):
        problems.append(f"Card location '{fields['destination']}' differs from request dropoff '{intake.get('Dropoff', '')}'")
    result['passed'] = not problems and not result['unreadable']
    result['reason'] = ('Card date, times and location agree with the rider request' if result['passed'] else
                        '; '.join(problems + ([f"Unreadable or missing card fields: {', '.join(result['unreadable'])}; confirm with the rider or coordinator"] if result['unreadable'] else [])))
    return result


_BYPASS = re.compile(r'\b(ignore|override|bypass|skip)\b.*\b(check|verification|review|sensor|policy|sign.?off)|without (human|sign.?off|review)|\bapprove (it|this|the ride) (now|automatically)', re.I | re.S)


def spoken_request_check(text, intake):
    """The transcript is untrusted evidence: its accessibility needs must appear in the intake, and it cannot instruct the review."""
    needs = []
    if re.search(r'wheel ?chair|ramp|mobility|scooter', text, re.I):
        needs.append(('wheelchair or ramp access', 'Mobility Device'))
    if re.search(r'service (dog|animal)|guide dog|assistance animal', text, re.I):
        needs.append(('service animal', 'Assistance Animal'))
    missing = [label for label, field in needs if not intake.get(field) or intake[field].startswith('MISSING_')]
    bypass = bool(_BYPASS.search(text))
    reasons = [f'Spoken request mentions {label}, but the rider intake does not record it' for label in missing]
    if bypass:
        reasons.append('Spoken request contains an instruction to bypass review; it is treated as evidence, not a command')
    return {'passed': not missing and not bypass, 'detected_needs': [label for label, _ in needs],
            'missing_in_intake': missing, 'bypass_instruction': bypass,
            'reason': '; '.join(reasons) or 'Accessibility needs in the spoken request match the rider intake'}


def _reject_constant(value):
    raise ValueError('Nonfinite JSON evidence is invalid')


def inspect(root, case, extra=None, card_extraction=None):
    from verification import checks
    docs = run_documents(root, case, extra)
    imgs = images(root, case)
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
    evidence_digest = digest(docs, imgs)
    if card_images(imgs):
        checks_out['appointment_card_check'] = card_check(fields, card_extraction, evidence_digest)
    if SPOKEN_REQUEST in docs:
        checks_out['spoken_request_check'] = spoken_request_check(docs[SPOKEN_REQUEST], fields)
        # Spoken dates and times are compared with the intake and with card fields read in this run from the current evidence.
        card = _valid_fields(card_extraction.get('fields')) if card_extraction and card_extraction.get('source_digest') == evidence_digest else None
        checks_out['spoken_schedule_check'] = schedule.check(docs[SPOKEN_REQUEST], fields, card)
    return {'checks': checks_out, 'passed': all(x['passed'] for x in checks_out.values()),
            'rider': fields.get('Rider'), 'selected_bay': selected,
            'evidence_digest': evidence_digest, 'telemetry_source': 'simulation_fixture',
            'policy_scope': 'Demo fleet policy; not a universal legal clearance standard'}
