import json
from pathlib import Path
from agent_kit import client as cm, progress, tools
STOP = {'answered', 'needs_input', 'awaiting_signoff', 'paused'}
def resolve_objective(root, case_name=None, prompt=None):
    r = Path(root)
    if prompt and str(prompt).strip(): return str(prompt).strip()
    if case_name:
        cp = r / 'cases' / case_name / 'objective.md'
        if cp.exists(): return cp.read_text().strip()
    default_p = r / 'cases' / 'harvey-taxi-ada-doctor-visit' / 'objective.md'
    return default_p.read_text().strip() if default_p.exists() else 'Investigate case'
def run_agent(root, objective=None, *, turns=4, verification=True, case_name=None):
    r = Path(root)
    obj = resolve_objective(r, case_name=case_name, prompt=objective)
    rid = progress.new_run(r, obj)
    return _loop(r, rid, [{'role': 'user', 'content': obj}], turns, 0, verification, obj)
def resume_run(root, run_id, message=None, *, turns=4, verification=True):
    r = Path(root); sv = progress.load_progress(r, run_id)
    if not message or not str(message).strip():
        return {'run_id': run_id, 'status': sv.get('status', 'paused'), 'turn': sv.get('turn', 0), 'model_calls': 0}
    msgs = list(sv.get('messages', [])) + [{'role': 'user', 'content': str(message)}]
    res = _loop(r, run_id, msgs, turns, int(sv.get('turn', 0)), verification, str(message))
    res['model_calls'] = 1; return res
def _loop(r, rid, msgs, turns, st, ver, obj):
    api = cm.create(); tr = []; t = st
    for i in range(1, turns + 1):
        t = st + i
        resp = api.responses.create(model='muse-spark-1.5', instructions='Work any domain case', input=msgs, tools=tools.names(ver))
        c = resp.output[0]
        st_val = 'awaiting_signoff' if c.name == 'submit_memo' else 'running'
        msgs.append({'type': 'function_call_output', 'call_id': c.call_id, 'output': json.dumps({'status': st_val})})
        tr.append({'turn': t, 'tool': c.name, 'status': st_val})
        progress.save_progress(r, rid, t, st_val, c.name, msgs)
        if st_val in STOP:
            return {'run_id': rid, 'objective': obj, 'status': st_val, 'turn': t, 'trace': tr, 'tools_available': tools.names(ver)}
    return {'run_id': rid, 'objective': obj, 'status': 'paused', 'turn': t, 'trace': tr}
