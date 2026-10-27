import json
from pathlib import Path
from agent_kit import client as cm, progress, settings, tools
STOP = {'answered', 'needs_input', 'awaiting_signoff', 'paused'}
INST = Path(__file__).with_name('system_instructions.md')
NUDGE = 'Call exactly one tool. When ready, file with submit_memo.'
LAST = 'Last turn, file with submit_memo now.'
def resolve_objective(root, case_name=None, prompt=None):
    r = Path(root)
    if prompt and str(prompt).strip(): return str(prompt).strip()
    if case_name:
        cp = r / 'cases' / case_name / 'objective.md'
        if cp.exists(): return cp.read_text().strip()
    dp = r / 'cases' / 'harvey-taxi-ada-doctor-visit' / 'objective.md'
    return dp.read_text().strip() if dp.exists() else 'Investigate case'
def run_agent(root, objective=None, *, turns=4, verification=True, case_name=None):
    r = Path(root)
    obj = resolve_objective(r, case_name=case_name, prompt=objective)
    rid = progress.new_run(r, obj)
    return _loop(r, rid, [{'role': 'user', 'content': obj}], turns, 0, verification, obj)
def resume_run(root, run_id, message=None, *, turns=4, verification=True):
    r = Path(root); sv = progress.load_progress(r, run_id)
    msg = message if message is not None else progress.resume(r, run_id)
    if not msg or not str(msg).strip():
        return {'run_id': run_id, 'status': sv.get('status', 'paused'), 'turn': sv.get('turn', 0), 'note': sv.get('note', ''), 'model_calls': 0}
    msgs = list(sv.get('messages', [])) + [{'role': 'user', 'content': str(msg)}]
    res = _loop(r, run_id, msgs, turns, int(sv.get('turn', 0)), verification, str(msg))
    res['model_calls'] = 1; return res
def _loop(r, rid, msgs, turns, st, ver, obj):
    ins = INST.read_text() if INST.exists() else 'Reason step by step'
    api = cm.create(); tr = []; t = st; note = ''
    for i in range(1, turns + 1):
        t = st + i
        if i == turns: msgs.append({'role': 'user', 'content': LAST})
        try:
            resp = api.responses.create(model=settings.model(), instructions=ins, input=msgs, tools=tools.definitions(r, rid, ver))
        except Exception as e:
            note = f'API exception: {e}'
            progress.save_progress(r, rid, t, 'paused', note, msgs)
            return {'run_id': rid, 'objective': obj, 'status': 'paused', 'turn': t, 'note': note, 'trace': tr}
        if not resp.output:
            msgs.append({'role': 'user', 'content': NUDGE})
            progress.save_progress(r, rid, t, 'running', 'nudged', msgs)
            continue
        c = resp.output[0]
        res = tools.run(api, r, rid, c)
        st_val = 'running' if 'error' in res else res.get('status', 'running')
        note = str(res.get('note') or res.get('error') or c.name)
        msgs.append({'type': 'function_call_output', 'call_id': c.call_id, 'output': json.dumps(res)})
        tr.append({'turn': t, 'tool': c.name, 'status': st_val, 'note': note})
        progress.save_progress(r, rid, t, st_val, note, msgs)
        if st_val in STOP:
            return {'run_id': rid, 'objective': obj, 'status': st_val, 'turn': t, 'note': note, 'trace': tr, 'tools_available': tools.names(ver)}
    note = 'turn budget exhausted'
    progress.save_progress(r, rid, t, 'paused', note, msgs)
    return {'run_id': rid, 'objective': obj, 'status': 'paused', 'turn': t, 'note': note, 'trace': tr}
