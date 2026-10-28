"""Atomic, case-bound run persistence. No credentials are stored in runs."""
from __future__ import annotations
import json
import os
import re
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc).isoformat()


def directory(root):
    path = Path(root) / 'workspace' / 'runs'
    path.mkdir(parents=True, exist_ok=True)
    return path


def run_path(root, run_id):
    if not isinstance(run_id, str) or not re.fullmatch(r'run_[0-9a-f]{32}', run_id):
        raise ValueError('Invalid run ID')
    return directory(root) / (run_id + '.json')


def atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix='.writing-')
    try:
        with os.fdopen(fd, 'w') as handle:
            json.dump(data, handle, indent=2, allow_nan=False)
            handle.write('\n')
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def save(root, record):
    record['updated_at'] = now()
    atomic_write(run_path(root, record['run_id']), record)
    atomic_write(directory(root) / 'run_latest.json', record)
    return record


def load_progress(root, run_id):
    if run_id == 'run_latest':
        latest = directory(root) / 'run_latest.json'
        if not latest.exists():
            raise ValueError('No run exists yet')
        run_id = json.loads(latest.read_text())['run_id']
    path = run_path(root, run_id)
    if not path.exists():
        raise ValueError('Run not found')
    record = json.loads(path.read_text())
    if record.get('schema_version') != 2:
        raise ValueError('Legacy run is archival; start a version-2 run')
    return record


def new_record(case, objective, mode, model):
    return {'schema_version': 2, 'run_id': 'run_' + uuid.uuid4().hex, 'timestamp': now(),
            'case': case, 'objective': objective, 'requested_mode': mode,
            'configured_model': model, 'status': 'running', 'turn': 0,
            'inference_mode': 'NOT_INVOKED' if mode == 'live' else 'DETERMINISTIC_FALLBACK_SIMULATION',
            'model_invoked_in_run': False, 'telemetry_source': 'simulation_fixture',
            'messages': [{'role': 'user', 'content': objective}], 'turns': [], 'receipts': [],
            'checklist': [], 'plan': [], 'facts': [], 'read_documents': [],
            'verification': {}, 'memo': None, 'human_signoff_token': None,
            'authorization_mode': 'NONE', 'dispatch_enabled': False,
            'run_integrity': {'passed': False, 'errors': ['Not verified yet']}}


def public_record(record):
    # Encrypted reasoning is retained only for API replay, never rendered as private reasoning.
    return {k: v for k, v in record.items() if k != 'messages'}
