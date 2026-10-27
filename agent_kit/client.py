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
  s = sum(1 for m in kw.get('input',[]) if isinstance(m,dict) and m.get('type')=='function_call_output')
  n = ['set_checklist','update_plan','submit_memo'][min(s,2)]
  return Resp([FC('function_call', n, f'c_{s+1}', '{}')])
class C:
 def __init__(self): self.responses = RE()
def create(): return C()
