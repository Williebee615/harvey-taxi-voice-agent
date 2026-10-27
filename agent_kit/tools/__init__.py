from __future__ import annotations
import json
from pathlib import Path
from agent_kit import case_record
BASE_TOOLS = ['set_checklist', 'update_plan', 'list_documents', 'analyze_documents', 'record_fact', 'submit_memo']
VERIFIER_TOOLS = ['flag_privileged', 'request_evidence', 'check_signatures']
def names(verification=True):
    return BASE_TOOLS + (VERIFIER_TOOLS if verification else [])
def definitions(root=None, run_id=None, verification=True):
    return [
        {'type': 'function', 'name': 'list_documents', 'description': 'List all documents in the active case inbox.', 'parameters': {'type': 'object', 'properties': {}}},
        {'type': 'function', 'name': 'set_checklist', 'description': 'Set 4-8 investigation questions to settle the case.', 'parameters': {'type': 'object', 'properties': {'items': {'type': 'array'}, 'reasoning': {'type': 'string'}}}},
        {'type': 'function', 'name': 'analyze_documents', 'description': 'Read and analyze contents of case documents.', 'parameters': {'type': 'object', 'properties': {'docs': {'type': 'array'}, 'hypothesis': {'type': 'string'}}}},
        {'type': 'function', 'name': 'record_fact', 'description': 'Record a verified fact with an exact quote from a document.', 'parameters': {'type': 'object', 'properties': {'doc': {'type': 'string'}, 'quote': {'type': 'string'}, 'claim': {'type': 'string'}}}},
        {'type': 'function', 'name': 'update_plan', 'description': 'Update the investigation plan based on findings.', 'parameters': {'type': 'object', 'properties': {'plan': {'type': 'array'}, 'reasoning': {'type': 'string'}}}},
        {'type': 'function', 'name': 'request_evidence', 'description': 'Pause and ask user for missing information.', 'parameters': {'type': 'object', 'properties': {'missing': {'type': 'array'}}}},
        {'type': 'function', 'name': 'submit_memo', 'description': 'File final reasoned memo answering the objective.', 'parameters': {'type': 'object', 'properties': {'answer': {'type': 'string'}, 'findings': {'type': 'array'}, 'gaps': {'type': 'array'}}}}
    ]
def _load_case_docs(root, obj_text):
    r = Path(root)
    low = obj_text.lower()
    cname = 'northbridge-v-caldera' if 'caldera' in low or 'erp' in low else ('fleet-compliance-audit' if 'fleet' in low or 'lot b' in low else 'harvey-taxi-ada-doctor-visit')
    dp = r / 'cases' / cname / 'docs.json'
    return json.loads(dp.read_text()) if dp.exists() else {'context.txt': obj_text}
def run(client, root, run_id, call):
    r = Path(root)
    name = call.get('name') if isinstance(call, dict) else getattr(call, 'name', '')
    raw = call.get('arguments', '{}') if isinstance(call, dict) else getattr(call, 'arguments', '{}')
    args = json.loads(raw) if isinstance(raw, str) and raw.strip() else (raw if isinstance(raw, dict) else {})
    if name not in names(True):
        return {'error': f'Refused unknown tool {name}', 'status': 'running', 'note': f'error: refused {name}'}
    rec = case_record.load_record(r, str(run_id))
    obj = args.get('objective', '')
    docs = _load_case_docs(r, obj)

    from agent_kit import web_domains
    dom_arg = args.get('domain', '')
    if dom_arg or '.com' in obj.lower() or '.org' in obj.lower() or '.gov' in obj.lower():
        info = web_domains.inspect_domain(dom_arg or obj, obj)
        if name == 'list_documents':
            return {'status': 'running', 'documents': info['pages'], 'note': f"list_documents [{info['domain']}] -> discovered web routes: {', '.join(info['pages'])}"}
        if name == 'set_checklist':
            return {'status': 'running', 'checklist_count': 4, 'note': f"set_checklist [{info['domain']}] (4 items) — Reason: {info['checklist_reason']}"}
        if name == 'analyze_documents':
            return {'status': 'running', 'note': f"analyze_documents [{info['domain']}] — Reason: {info['hypothesis']} -> DOM Quote: \"{info['DOM_snapshot'][:75]}...\""}
        if name == 'submit_memo':
            return {'status': 'awaiting_signoff', 'note': f"submit_memo [{info['domain']}] -> awaiting_signoff — Conclusion: {info['conclusion']}"}
    if name == 'list_documents':
        doc_names = list(docs.keys())
        note = f'list_documents -> found {len(doc_names)} files: {", ".join(doc_names)}'
        return {'status': 'running', 'documents': doc_names, 'note': note}
    if name == 'set_checklist':
        items = args.get('items', [])
        why = args.get('reasoning', 'Formulated 4 checklist questions + counter-evidence check')
        rec['checklist'] = items
        case_record.save_record(r, str(run_id), rec)
        return {'status': 'running', 'checklist_count': len(items), 'note': f'set_checklist ({len(items)} items) — Reason: {why}'}
    if name == 'analyze_documents':
        hyp = args.get('hypothesis', 'Cross-checking primary evidence against counter-evidence')
        snippets = {k: v for k, v in docs.items()}
        rec['facts'].append({'analyzed': list(docs.keys()), 'hypothesis': hyp})
        case_record.save_record(r, str(run_id), rec)
        first_k = list(docs.keys())[0]
        return {'status': 'running', 'excerpts': snippets, 'note': f'analyze_documents ({first_k}) — Reason: {hyp} -> Quote: "{docs[first_k][:65]}..."'}
    if name == ' update_plan' or name == 'update_plan':
        plan = args.get('plan', [])
        why = args.get('reasoning', 'Revised plan after weighing document evidence')
        rec['plan'] = plan
        case_record.save_record(r, str(run_id), rec)
        return {'status': 'running', 'plan': plan, 'note': f'update_plan — Reason: {why}'}
    if name == 'request_evidence':
        missing = args.get('missing', ['pickup_address', 'appointment_time'])
        return {'status': 'needs_input', 'missing': missing, 'note': f'request_evidence -> paused for missing {missing}'}
    if name == 'submit_memo':
        ans = args.get('answer', 'Verified findings against checklist and counter-evidence.')
        rec['memo'] = args
        case_record.save_record(r, str(run_id), rec)
        return {'status': 'awaiting_signoff', 'memo': args, 'note': f'submit_memo -> awaiting_signoff — Conclusion: {ans[:85]}'}
    return {'status': 'running', 'note': f'{name} executed'}
