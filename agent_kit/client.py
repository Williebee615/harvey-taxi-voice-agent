import json
from dataclasses import dataclass
@dataclass
class FC:
    type: str; name: str; call_id: str; arguments: str
@dataclass
class Resp:
    output: list
class RE:
    def create(self, **kw):
        msgs = kw.get('input', [])
        obj = str(msgs[0].get('content', '')) if msgs else ''
        s = sum(1 for m in msgs if isinstance(m, dict) and m.get('type')=='function_call_output')
        seq = ['list_documents', 'set_checklist', 'update_plan', 'submit_memo']
        n = seq[min(s, len(seq)-1)]
        args = json.dumps({'objective': obj[:80], 'step': s+1})
        return Resp([FC('function_call', n, f'call_{s+1}', args)])
class C:
    def __init__(self): self.responses = RE()
def create(): return C()
