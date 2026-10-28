"""Legacy report entry point: export the actual public JSON audit, without inferred findings.

PDF generation is intentionally retired. The previous report invented success when
no record existed and truncated evidence. Use the console's Download audit JSON.
"""
from pathlib import Path
from agent_kit import progress


def generate_report(root, run_id=None):
    record = progress.load_progress(root, run_id or 'run_latest')
    report = Path(root) / 'workspace' / 'reports' / (record['run_id'] + '.json')
    progress.atomic_write(report, progress.public_record(record))
    return {'run_id': record['run_id'], 'json_path': str(report), 'format': 'application/json'}
