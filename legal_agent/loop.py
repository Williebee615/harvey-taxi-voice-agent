import json
from pathlib import Path
from agent_kit import client as cm, progress, tools
STOP = {'answered','needs_input','awaiting_signoff','paused'}
def run_agent(root, objective=None, *, turns=10, verification=True):
 r = Path(root); obj = objective or 'Verify ADA ride'
 rid = progress.new_run(r, obj)
 return _loop(r, rid, [{'role':'user','content':obj}], turns, 0, verification)
def resume_run(root, run_id, message=None, *, turns=10, verification=True):
 r = Path(root); sv = progress.load_progress(r, run_id)
 if not message or not str(message).strip(): return {'run_id':run_id,'status':sv.get('status','paused'),'turn':sv.get('turn',0),'model_calls':0,'note':'0 calls'}
 res = _loop(r, run_id, list(sv.get('messages',[]))+[{'role':'user','content':str(message)}], turns, int(sv.get('turn',0)), verification)
 res['model_calls'] = 1; return res
def _loop(r, rid, msgs, turns, st, ver):
 api = cm.create(); tr = []; t = st
 for i in range(1, turns+1):
  t = st + i
  resp = api.responses.create(model='muse-spark-1.5', instructions='Work case', input=msgs, tools=tools.names(ver))
  c = resp.output[0]; st_val = 'awaiting_signoff' if c.name=='submit_memo' else 'running'
  msgs.append({'type':'function_call_output','call_id':c.call_id,'output':json.dumps({'status':st_val})})
  tr.append({'turn':t,'tool':c.name,'status':st_val})
  progress.save_progress(r, rid, t, st_val, c.name, msgs)
  if st_val in STOP: return {'run_id':rid,'status':st_val,'turn':t,'note':c.name,'trace':tr,'tools_available':tools.names(ver)}
 return {'run_id':rid,'status':'paused','turn':t,'note':'limit','trace':tr}
