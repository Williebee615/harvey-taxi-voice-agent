import json, uuid
from pathlib import Path
def _d(r):
 d = Path(r)/'workspace'/'runs'; d.mkdir(parents=True, exist_ok=True); return d
def new_run(r, obj):
 rid = 'run_' + uuid.uuid4().hex[:8]; save_progress(r, rid, 0, 'running', 'init', [{'role':'user','content':obj}]); return rid
def save_progress(r, rid, t, s, n, m):
 d = {'run_id':rid,'turn':t,'status':s,'note':n,'messages':[x if isinstance(x,dict) else {'type':'call'} for x in m]}
 (_d(r)/f'{rid}.json').write_text(json.dumps(d,indent=2)+'\n'); return d
def load_progress(r, rid):
 f = _d(r)/f'{rid}.json'
 return json.loads(f.read_text()) if f.exists() else {'run_id':rid,'turn':0,'status':'paused','note':'none','messages':[]}

def resume(root, run_id):
    f = Path(root) / 'world' / 'follow_up' / f'{run_id}.txt'
    return f.read_text().strip() if f.exists() else None

def branch(root, run_id):
    saved = load_progress(root, run_id)
    new_id = rid = f'{run_id}_ver'
    save_progress(root, new_id, saved.get('turn', 0), 'running', 'branched with verification on', saved.get('messages', []))
    return new_id
