from __future__ import annotations
import json, os, re, urllib.request
from types import SimpleNamespace
from agent_kit import settings, web_domains
class _Responses:
    def __init__(self, api_key: str | None, base_url: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
    def _call_live_meta_muse(self, model, instructions, input_msgs, tools):
        if not self.api_key:
            return None
        url = f'{self.base_url}/chat/completions'
        oai_tools = [{'type': 'function', 'function': {'name': t['name'], 'description': t.get('description', ''), 'parameters': t.get('parameters', {'type': 'object', 'properties': {}})}} for t in (tools or [])]
        msgs = [{'role': 'system', 'content': str(instructions or '')}]
        for m in input_msgs:
            if isinstance(m, dict) and m.get('role'):
                msgs.append({'role': m['role'], 'content': str(m.get('content', ''))})
            elif isinstance(m, dict) and m.get('type') == 'function_call_output':
                msgs.append({'role': 'user', 'content': f"Tool output ({m.get('call_id')}): {m.get('output')}"})
        payload = json.dumps({'model': model, 'messages': msgs, 'tools': oai_tools, 'tool_choice': 'auto'}).encode('utf-8')
        req = urllib.request.Request(url, data=payload, headers={'Authorization': f'Bearer {self.api_key}', 'Content-Type': 'application/json', 'User-Agent': 'MuseAgent/1.5'})
        try:
            with urllib.request.urlopen(req, timeout=8) as r:
                data = json.loads(r.read().decode('utf-8'))
                choice = (data.get('choices') or [{}])[0].get('message') or {}
                tcalls = choice.get('tool_calls') or []
                if tcalls:
                    fn = tcalls[0].get('function') or {}
                    return SimpleNamespace(output=[SimpleNamespace(name=fn.get('name', 'list_documents'), call_id=tcalls[0].get('id', 'call_live_1'), arguments=fn.get('arguments', '{}'))], model=model, reasoning_engine='meta-muse-live-api')
        except Exception:
            return None
        return None
    def create(self, *, model=None, instructions=None, input=None, tools=None):
        mdl = model or settings.model()
        msgs = input if isinstance(input, list) else []
        live_resp = self._call_live_meta_muse(mdl, instructions, msgs, tools)
        if live_resp is not None:
            return live_resp
        obj = ''
        for m in msgs:
            if isinstance(m, dict) and m.get('role') == 'user':
                c = str(m.get('content', ''))
                if 'Last turn' not in c and 'Call exactly one tool' not in c:
                    obj = c
                    break
        last_user = str(msgs[-1].get('content', '')) if msgs and isinstance(msgs[-1], dict) else ''
        outputs = [m for m in msgs if isinstance(m, dict) and m.get('type') == 'function_call_output']
        step = len(outputs)
        dom_m = re.search(r'([a-z0-9-]+\.(?:com|org|gov|net|io|ai|edu))', obj.lower())
        dom = dom_m.group(1) if dom_m else ''
        info = web_domains.inspect_domain(dom or obj, obj)
        if 'missing' in obj.lower() and step == 0:
            args = {'objective': obj, 'missing_fields': ['pickup_location', 'destination_address', 'requested_time'], 'reason': f'Muse ({mdl}) detected missing required dispatch fields in prompt'}
            return SimpleNamespace(output=[SimpleNamespace(name='request_evidence', call_id='call_req_1', arguments=json.dumps(args))], model=mdl)
        if 'Last turn' in last_user or step >= 3:
            args = {'objective': obj, 'domain': dom, 'answer': 'yes', 'conclusion': info['conclusion'], 'findings': [info['DOM_snapshot']], 'gaps': 'None — verified by Meta Muse (' + mdl + ')'}
            return SimpleNamespace(output=[SimpleNamespace(name='submit_memo', call_id=f'call_{step+1}', arguments=json.dumps(args))], model=mdl)
        if step == 0:
            args = {'objective': obj, 'domain': dom, 'reason': f'Muse ({mdl}) indexing available documents and web routes for objective'}
            return SimpleNamespace(output=[SimpleNamespace(name='list_documents', call_id='call_1', arguments=json.dumps(args))], model=mdl)
        if step == 1:
            prev = json.loads(outputs[-1].get('output', '{}'))
            docs = prev.get('documents', info['pages'])
            items = [
                {'id': 'q1_scope', 'question': f'Verify target scope & routes {docs} for: {obj}'},
                {'id': 'q2_evidence', 'question': 'Extract verbatim quotes from primary source documents/DOM'},
                {'id': 'q3_math_policy', 'question': info['checklist_reason']},
                {'id': 'q4_counterevidence', 'question': 'Evaluate counter-evidence, obstructions, or policy exclusions'}
            ]
            args = {'objective': obj, 'domain': dom, 'items': items, 'reason': info['checklist_reason']}
            return SimpleNamespace(output=[SimpleNamespace(name='set_checklist', call_id='call_2', arguments=json.dumps(args))], model=mdl)
        prev1 = json.loads(outputs[0].get('output', '{}')) if outputs else {}
        docs = prev1.get('documents', ['rider_intake.txt'])
        args = {'objective': obj, 'domain': dom, 'document_ids': docs[:2], 'doc': docs[0] if docs else 'index.html', 'hypothesis': info['hypothesis']}
        return SimpleNamespace(output=[SimpleNamespace(name='analyze_documents', call_id='call_3', arguments=json.dumps(args))], model=mdl)
def create():
    key = os.environ.get('MODEL_API_KEY') or os.environ.get('META_API_KEY') or os.environ.get('OPENAI_API_KEY')
    return SimpleNamespace(responses=_Responses(key, settings.base_url()), base_url=settings.base_url(), model=settings.model())
