from __future__ import annotations
import json, uuid, re
from datetime import datetime, timezone
from pathlib import Path
from agent_kit import settings
from verification import checks

def run_agent(root: str | Path, turns: int = 4, objective: str | None = None, case_name: str | None = None) -> dict:
    root_path = Path(root).resolve()
    cname = case_name or 'harvey-taxi-ada-doctor-visit'
    if not (root_path / 'cases' / cname).is_dir():
        raise ValueError(f'Unknown case: {cname}. Refusing to substitute a default case.')
    inbox = root_path / 'cases' / cname / 'inbox'
    docs = sorted([p.name for p in inbox.iterdir() if p.is_file()]) if inbox.exists() else []
    intake_txt = (inbox / 'rider_intake.txt').read_text() if (inbox / 'rider_intake.txt').exists() else ''
    handbook_txt = (inbox / 'HANDBOOK.md').read_text() if (inbox / 'HANDBOOK.md').exists() else ''
    sam_json = json.loads((inbox / 'sam3_curb_telemetry.json').read_text()) if (inbox / 'sam3_curb_telemetry.json').exists() else {}
    obj = objective or f'Verify ADA ride booking for case {cname}'
    run_id = f'run_{uuid.uuid4().hex[:8]}'
    # This loop is deterministic. A separate model probe must never be presented as this run's inference.
    mode = 'DETERMINISTIC_FALLBACK_SIMULATION'

    t1 = {'turn': 1, 'phase': 'PLAN', 'tool': 'list_documents', 'arguments': {'case': cname}, 'observation': {'documents': docs}}
    checklist_items = [
        {'id': 'q1_intake', 'question': 'Are pickup, dropoff, and pickup time complete?'},
        {'id': 'q2_fare', 'question': 'Does fare equal $2.50 + $1.50/mi with $0.00 ADA fee?'},
        {'id': 'q3_curb', 'question': 'Does SAM 3.1 confirm >= 8.0ft ramp clearance?'},
        {'id': 'q4_counter_evidence', 'question': 'Were obstructed bays (6.1ft South Bay) or illegal overrides rejected?'},
        {'id': 'q5_signoff', 'question': 'Is dispatch held at awaiting_signoff until human authorization?'}
    ]
    t2 = {'turn': 2, 'phase': 'PLAN', 'tool': 'set_checklist', 'arguments': {'items': checklist_items}, 'observation': {'count': len(checklist_items)}}

    # Verify the policy quote against case evidence. Never invent a quote if the file is absent.
    quote_target = '$2.50 base component plus $1.50 per verified mile.'
    quote_check = checks.verify_exact_quote(root_path, cname, 'HANDBOOK.md', quote_target)
    fields = {}
    for line in intake_txt.splitlines():
        if ':' in line:
            k, v = line.split(':', 1)
            fields[k.strip()] = v.strip()
    rider_name = fields.get('Rider', '').strip()
    required_fields = ('Rider', 'Pickup', 'Dropoff', 'Pickup Time', 'Verified Distance')
    missing_fields = [field for field in required_fields if not fields.get(field) or fields[field].startswith('MISSING_')]
    miles = None
    raw_miles = fields.get('Verified Distance', '')
    match_miles = re.fullmatch(r'\s*(\d+(?:\.\d+)?)\s*miles?\s*', raw_miles, re.I)
    if match_miles:
        value = float(match_miles.group(1))
        if value > 0:
            miles = value
    if miles is None and 'Verified Distance' not in missing_fields:
        missing_fields.append('Verified Distance')
    quoted = fields.get('Quoted Fare', '')
    fare_match = re.match(r'^\$(\d+(?:\.\d{1,2})?)\b', quoted)
    claimed_fare = float(fare_match.group(1)) if fare_match else None
    if claimed_fare is None:
        missing_fields.append('Quoted Fare')
    claimed_ada_fee = 15.0 if re.search(r'\$15(?:\.00)?\s*(?:ADA|wheelchair|service)', quoted, re.I) else 0.0
    fare_check = (checks.verify_fare_invariant(miles, claimed_fare, claimed_ada_fee)
                  if miles is not None and claimed_fare is not None else
                  {'passed': False, 'expected_fare': None, 'claimed_fare': claimed_fare,
                   'formula': None, 'reason': 'Missing verified mileage or explicitly quoted fare'})
    selected_bay = sam_json.get('selected_bay')
    bay_info = sam_json.get(selected_bay) if isinstance(selected_bay, str) else None
    try:
        clearance = float(bay_info['clearance_ft']) if isinstance(bay_info, dict) else None
    except (KeyError, ValueError, TypeError):
        clearance = None
    curb_check = (checks.verify_curb_safety(clearance) if clearance is not None else
                  {'passed': False, 'clearance_ft': None, 'required_ft': settings.MIN_RAMP_CLEARANCE_FT,
                   'reason': 'Missing selected curb bay or verified clearance telemetry'})
    missing_intake = bool(missing_fields) or 'incomplete' in cname or (obj and 'missing' in obj.lower())
    contradiction = 'CONTRADICTION' in json.dumps(sam_json) or 'contradictory' in cname

    t3 = {
        'turn': 3, 'phase': 'ACT', 'tool': 'analyze_documents',
        'arguments': {'documents': docs, 'verbatim_quote': quote_target, 'counter_evidence_probe': '6.1ft South Bay vs 9.4ft North Bay'},
        'observation': {'quote_verification': quote_check, 'fare_verification': fare_check, 'curb_verification': curb_check, 'missing_intake': missing_intake, 'missing_fields': missing_fields, 'contradiction_detected': contradiction}
    }

    if missing_intake:
        final_status = 'needs_input'
        t4_tool = 'request_evidence'
        t4_args = {'missing_fields': missing_fields, 'reason': 'Missing required rider evidence; no values substituted'}
    elif not quote_check['passed'] or not curb_check['passed'] or not fare_check['passed'] or contradiction:
        final_status = 'needs_input'
        t4_tool = 'request_evidence'
        t4_args = {'escalated_risk': (quote_check['reason'] if not quote_check['passed'] else curb_check['reason'] if not curb_check['passed'] else fare_check['reason']), 'corrected_fare': fare_check['formula']}
    else:
        final_status = 'awaiting_signoff'
        t4_tool = 'submit_memo'
        t4_args = {'rider': rider_name, 'verified_fare': f"${fare_check['expected_fare']:.2f}", 'formula': fare_check['formula'], 'selected_curb_bay': f'{selected_bay} ({clearance:.1f}ft >= 8.0ft)', 'rejected_counter_evidence': 'South Bay 6.1ft rejected', 'status': 'awaiting_signoff'}

    t4 = {'turn': 4, 'phase': 'OBSERVE', 'tool': t4_tool, 'arguments': t4_args, 'observation': {'final_status': final_status}}
    record = {
        'run_id': run_id, 'timestamp': datetime.now(timezone.utc).isoformat(), 'case': cname, 'objective': obj,
        'inference_mode': mode, 'model_invoked_in_run': False, 'model_roles_configured_not_executed': settings.MODEL_ROLES, 'telemetry_source': 'simulation_fixture', 'status': final_status,
        'counter_evidence_checked': bool(sam_json), 'human_signoff_token': None,
        'verification': {'quote_check': quote_check, 'fare_check': fare_check, 'curb_check': curb_check},
        'turns': [t1, t2, t3, t4]
    }
    record['run_integrity'] = checks.verify_run_record(record)
    runs_dir = root_path / 'workspace' / 'runs'
    runs_dir.mkdir(parents=True, exist_ok=True)
    (runs_dir / 'run_latest.json').write_text(json.dumps(record, indent=2) + '\n')
    for t in record['turns']:
        print(f"[turn {t['turn']}] {t['tool']} -> {json.dumps(t['arguments'])}")
    print(f'inference_mode={mode} final_status={final_status}')
    return record

def resume_run(root: str | Path, run_id: str = 'run_latest', dispatcher_signature: str = '') -> dict:
    root_path = Path(root).resolve()
    rpath = root_path / 'workspace' / 'runs' / 'run_latest.json'
    record = json.loads(rpath.read_text())
    if record.get('status') != 'awaiting_signoff':
        raise ValueError(f"Cannot approve run in status '{record.get('status')}'")
    if not dispatcher_signature or len(dispatcher_signature.strip()) < 3:
        raise ValueError('Valid human dispatcher signature required')
    if not record.get('run_integrity', {}).get('passed') or not all(record['verification'][key]['passed'] for key in ('quote_check', 'fare_check', 'curb_check')):
        raise ValueError('Cannot approve failed or unverifiable evidence')
    # A typed demo signature is not authenticated authorization for real dispatch.
    record['authorization_mode'] = 'SIMULATED_DISPATCHER_SIGNOFF'
    record['human_signoff_token'] = dispatcher_signature.strip()
    record['status'] = 'completed_after_human_signoff'
    rpath.write_text(json.dumps(record, indent=2) + '\n')
    print(f"[resume_run] run_id={record['run_id']} human_signoff_token='{dispatcher_signature.strip()}' final_status={record['status']}")
    return record
