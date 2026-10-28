"""Workshop-style model -> tool -> observation loop with resumable run records."""
from __future__ import annotations
import json
from pathlib import Path
from agent_kit import client as model_client, evidence, progress, settings, tools

STOP = {'needs_input', 'awaiting_signoff', 'paused', 'completed_after_human_signoff'}


def _instructions():
    return Path(__file__).with_name('system_instructions.md').read_text()


def _simulation_calls(root, record):
    """Explicit offline demonstration. These choices are scripted, never called AI."""
    docs = evidence.documents(root, record['case'])
    items = [
        {'id': 'intake', 'question': 'Are the rider, journey, time and quoted fare supplied?'},
        {'id': 'fare', 'question': 'Does the quoted fare follow the supplied tariff?'},
        {'id': 'curb', 'question': 'Does supplied curb telemetry meet the demo fleet policy?'},
        {'id': 'counter', 'question': 'Is contradictory evidence rejected and human signoff required?'}]
    calls = [('list_documents', {}), ('set_checklist', {'items': items}),
             ('analyze_documents', {'documents': list(docs)}), ('verify_booking', {})]
    if not evidence.inspect(root, record['case'])['passed']:
        return calls + [('request_evidence', {'missing': ['Resolve the failed independent booking checks shown in verification.']})]
    sources = [('intake', 'rider_intake.txt'), ('fare', 'HANDBOOK.md'),
               ('curb', 'sam3_curb_telemetry.json'), ('counter', 'HANDBOOK.md')]
    findings = []
    for i, (item, document) in enumerate(sources, 1):
        if item == 'fare':
            quote = '$2.50 base component plus $1.50 per verified mile.'
        elif item == 'counter':
            quote = next((line for line in docs[document].splitlines() if 'awaiting_signoff' in line), docs[document])
        elif item == 'curb':
            quote = docs[document]
        else:
            quote = next(line for line in docs[document].splitlines() if line.strip())
        claim = 'Source evidence for ' + item + '; see independent checks.'
        calls.append(('record_fact', {'item': item, 'document': document, 'quote': quote, 'claim': claim}))
        findings.append({'item': item, 'finding': claim, 'fact_ids': [f'F{i}']})
    return calls + [('submit_memo', {'answer': 'Demo evidence passed independent checks; dispatcher review is required.', 'findings': findings, 'gaps': []})]


def _advance(root, record, turns, api=None):
    if isinstance(turns, bool) or not isinstance(turns, int) or not 1 <= turns <= 40:
        raise ValueError('Turn limit must be 1-40')
    if record['turn'] + turns > 200:
        raise ValueError('Run budget exceeded; start a new run')
    record['status'] = 'running'
    progress.save(root, record)
    scripted = _simulation_calls(root, record) if record['requested_mode'] == 'simulation' else None
    api = api or (model_client.create() if scripted is None else None)
    for offset in range(turns):
        turn = record['turn'] + 1
        event = {'turn': turn, 'phase': 'ACT', 'timestamp': progress.now()}
        try:
            if scripted is not None:
                if turn > len(scripted):
                    record['status'] = 'paused'
                    break
                name, args = scripted[turn - 1]
                call = {'type': 'function_call', 'name': name, 'call_id': f'simulation_{turn}', 'arguments': json.dumps(args)}
                output = [call]
            else:
                response = api.responses.create(model=record['configured_model'], instructions=_instructions(),
                    input=record['messages'], tools=tools.definitions(root, record['run_id']))
                record['model_invoked_in_run'] = True
                record['inference_mode'] = 'LIVE_META_API'
                receipt = {'turn': turn, 'response_id': response.get('id'), 'model': response.get('model'), 'usage': response.get('usage', {})}
                record['receipts'].append(receipt)
                output = response['output']
                event['receipt'] = receipt
                calls = [x for x in output if x.get('type') == 'function_call']
                # Preserve exact provider output (including encrypted replay data), not hidden reasoning text in UI.
                record['messages'].extend(output)
                if len(calls) != 1 or not calls[0].get('call_id'):
                    for bad in calls:
                        record['messages'].append({'type': 'function_call_output', 'call_id': bad.get('call_id'), 'output': json.dumps({'error': 'Exactly one tool per turn; none executed.'})})
                    record['messages'].append({'role': 'user', 'content': 'Call exactly one available tool. No tool was executed this turn.'})
                    event.update(tool='no_tool_executed', arguments={}, observation={'error': 'Model must select exactly one tool'})
                    record['turn'] = turn
                    record['turns'].append(event)
                    progress.save(root, record)
                    continue
                call = calls[0]
            if scripted is not None:
                record['messages'].extend(output)
            result = tools.run(api, root, record['run_id'], call, record=record)
            record['messages'].append({'type': 'function_call_output', 'call_id': call['call_id'], 'output': json.dumps(result)})
            if offset == turns - 2:
                record['messages'].append({'role': 'user', 'content': 'One turn remains in this batch. Submit a fully cited memo if ready; otherwise request missing evidence. Never skip checks.'})
            try:
                arguments = json.loads(call.get('arguments', '{}')) if isinstance(call.get('arguments'), str) else call.get('arguments', {})
            except ValueError:
                arguments = {'invalid_json': True}
            event.update(tool=call['name'], arguments=arguments, observation=result)
            record['status'] = result.get('status', 'running')
        except model_client.ModelError as error:
            event.update(tool='api_error', arguments={}, observation={'error': str(error)})
            record['status'] = 'paused'
            record['pause_reason'] = str(error)
        record['turn'] = turn
        record['turns'].append(event)
        progress.save(root, record)
        print(f"[turn {turn}] {event['tool']} -> {record['status']}", flush=True)
        if record['status'] in STOP:
            break
    if record['status'] == 'running':
        record['status'] = 'paused'
        record['pause_reason'] = 'Turn batch exhausted; continue explicitly.'
    progress.save(root, record)
    print(f"inference_mode={record['inference_mode']} final_status={record['status']}", flush=True)
    return record


def run_agent(root, turns=20, objective=None, case_name=None, mode='simulation', api=None):
    if mode not in ('simulation', 'live'):
        raise ValueError('Choose simulation or live')
    case = case_name or 'harvey-taxi-ada-doctor-visit'
    evidence.case_path(root, case)
    if objective is not None and (not isinstance(objective, str) or len(objective) > 10_000):
        raise ValueError('Objective must be text of at most 10000 characters')
    objective = objective or f'Investigate accessible booking evidence for {case}. Verify fare, intake, curb evidence and counter-evidence; hold for dispatcher signoff.'
    record = progress.new_record(case, objective, mode, settings.model())
    return _advance(root, record, turns, api)


def resume_run(root, run_id='run_latest', dispatcher_signature='', *, message='', turns=20, api=None):
    record = progress.load_progress(root, run_id)
    if dispatcher_signature:
        return approve_run(root, record['run_id'], dispatcher_signature)
    if record['status'] in ('awaiting_signoff', 'completed_after_human_signoff'):
        return record  # No API calls when no work is required.
    if record['status'] == 'needs_input' and not message.strip():
        return record
    if message:
        if not isinstance(message, str) or len(message) > 10_000:
            raise ValueError('Follow-up must be text of at most 10000 characters')
        record['messages'].append({'role': 'user', 'content': 'Human follow-up (not proof of source changes): ' + message})
        # Evidence must be rechecked and re-cited, never approved from a follow-up alone.
        record['verified_digest'] = None
        record['facts'] = []
        record['memo'] = None
        if record['requested_mode'] == 'simulation':
            raise ValueError('For changed simulation evidence, start a new run. Live runs support follow-up.')
    return _advance(root, record, turns, api)


def approve_run(root, run_id, signature):
    record = progress.load_progress(root, run_id)
    if record['status'] != 'awaiting_signoff':
        raise ValueError('Only an awaiting_signoff run can be approved')
    if not isinstance(signature, str) or not 3 <= len(signature.strip()) <= 120:
        raise ValueError('Enter a reviewer name of 3-120 characters')
    current = evidence.inspect(root, record['case'])
    if not current['passed'] or current['evidence_digest'] != record.get('verified_digest') or not record.get('run_integrity', {}).get('passed') or not record.get('memo'):
        raise ValueError('Evidence failed or changed since verification. Start a new review.')
    record.update(status='completed_after_human_signoff', human_signoff_token=signature.strip(),
                  authorization_mode='SIMULATED_DISPATCHER_SIGNOFF', signed_at=progress.now())
    record.setdefault('audit', []).append({'action': 'demo_signoff', 'timestamp': progress.now(), 'reviewer': signature.strip()})
    return progress.save(root, record)
