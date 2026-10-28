from __future__ import annotations
import json
from pathlib import Path
def _path(root: str | Path, run_id: str) -> Path:
    from agent_kit.progress import run_path
    run_path(root, run_id)
    d = Path(root) / 'workspace' / 'case_records'
    d.mkdir(parents=True, exist_ok=True)
    return d / f'{run_id}.json'
def load_record(root: str | Path, run_id: str) -> dict:
    p = _path(root, run_id)
    if p.exists(): return json.loads(p.read_text())
    return {'run_id': run_id, 'checklist': [], 'plan': [], 'facts': [], 'flags': [], 'signatures': [], 'evidence_requests': [], 'memo': None}
def save_record(root: str | Path, run_id: str, rec: dict) -> dict:
    _path(root, run_id).write_text(json.dumps(rec, indent=2) + '\n')
    r2 = Path(root) / 'workspace' / 'runs'
    r2.mkdir(parents=True, exist_ok=True)
    (r2 / f'{run_id}_record.json').write_text(json.dumps(rec, indent=2) + '\n')
    return rec
