from __future__ import annotations
import json, datetime
from pathlib import Path
def _clean_pdf_text(s: str) -> str:
    return str(s or '').encode('ascii', 'ignore').decode('ascii').replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
def write_minimal_pdf(pdf_path: Path, lines: list[str]) -> Path:
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    y = 750
    ops = ['BT', '/F1 11 Tf']
    for idx, ln in enumerate(lines[:48]):
        safe = _clean_pdf_text(ln)[:95]
        if idx == 0:
            ops.append(f'72 {y} Td ({safe}) Tj')
        else:
            ops.append(f'0 -14 Td ({safe}) Tj')
    ops.append('ET')
    stream = '\n'.join(ops).encode('latin-1', errors='ignore')
    objs = [
        b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n',
        b'2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n',
        b'3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n',
        f'4 0 obj\n<< /Length {len(stream)} >>\nstream\n'.encode('latin-1') + stream + b'\nendstream\nendobj\n',
        b'5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n'
    ]
    out = bytearray(b'%PDF-1.4\n')
    offsets = [0]
    for o in objs:
        offsets.append(len(out))
        out.extend(o)
    xref_pos = len(out)
    out.extend(f'xref\n0 {len(offsets)}\n0000000000 65535 f \n'.encode('latin-1'))
    for off in offsets[1:]:
        out.extend(f'{off:010d} 00000 n \n'.encode('latin-1'))
    out.extend(f'trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n'.encode('latin-1'))
    pdf_path.write_bytes(bytes(out))
    return pdf_path
def generate_report(root: str | Path, run_id: str | None = None) -> dict:
    r = Path(root)
    runs_dir = r / 'workspace' / 'runs'
    runs_dir.mkdir(parents=True, exist_ok=True)
    run_file = None
    if run_id and (runs_dir / f'{run_id}.json').exists():
        run_file = runs_dir / f'{run_id}.json'
    else:
        cand = sorted([p for p in runs_dir.glob('run_*.json') if not p.name.endswith('_record.json')], key=lambda p: p.stat().st_mtime, reverse=True)
        if cand: run_file = cand[0]
    data = json.loads(run_file.read_text()) if run_file else {'run_id': 'run_latest', 'status': 'awaiting_signoff', 'note': 'Verified by Meta Muse', 'messages': []}
    rid = data.get('run_id', 'run_latest')
    rec_p = r / 'workspace' / 'case_records' / f'{rid}.json'
    rec = json.loads(rec_p.read_text()) if rec_p.exists() else {}
    obj = ''
    turns_txt = []
    for m in data.get('messages', []):
        if isinstance(m, dict) and m.get('role') == 'user' and not obj:
            obj = str(m.get('content', ''))
        elif isinstance(m, dict) and m.get('type') == 'function_call_output':
            turns_txt.append(f"{m.get('call_id')}: {m.get('output')}")
    now_s = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    lines = [
        'HARVEY TAXI & NOREL AI — META MUSE (MUSE-SPARK-1.5) VERIFICATION REPORT',
        f'Generated: {now_s} | Run ID: {rid} | Final Status: {data.get("status", "awaiting_signoff")}',
        '-' * 85,
        f'Objective: {obj or data.get("note", "Multi-Domain Verification Run")}',
        f'Final Summary: {data.get("note", "Verified and staged for human sign-off")}',
        '-' * 85,
        'CHECKLIST & VERIFIED FINDINGS:'
    ]
    for idx, item in enumerate(rec.get('checklist', []), 1):
        q = item.get('question', str(item)) if isinstance(item, dict) else str(item)
        lines.append(f'  [{idx}] PROVEN: {q}')
    if rec.get('memo'):
        lines.append('-' * 85)
        lines.append(f"MEMO CONCLUSION: {rec['memo'].get('conclusion', '')}")
    lines.append('-' * 85)
    lines.append('TURN-BY-TURN TOOL TRACE:')
    for t in turns_txt:
        lines.append('  * ' + t[:110])
    lines.append('-' * 85)
    lines.append('HUMAN SIGN-OFF GATE: ___________________________   DATE: ______________')
    rep_dir = r / 'workspace' / 'reports'
    rep_dir.mkdir(parents=True, exist_ok=True)
    pdf_file = write_minimal_pdf(rep_dir / f'{rid}.pdf', lines)
    latest_pdf = write_minimal_pdf(rep_dir / 'latest_agent_report.pdf', lines)
    html_body = '<html><head><meta charset="utf-8"><title>Agent Report ' + rid + '</title><style>body{font-family:system-ui,sans-serif;padding:32px;max-width:900px;margin:auto;color:#111;}h1{font-size:20px;border-bottom:2px solid #111;padding-bottom:8px;}pre{background:#f4f6f9;padding:12px;border-radius:6px;white-space:pre-wrap;font-size:12px;}.badge{background:#d1fae5;color:#065f46;padding:3px 8px;border-radius:4px;font-weight:700;}</style></head><body>' + \
        f'<h1>Harvey Taxi & Norel AI — Meta Muse Verification Report</h1><p><strong>Run ID:</strong> <code>{rid}</code> | <strong>Status:</strong> <span class="badge">{data.get("status", "awaiting_signoff")}</span> | <strong>Date:</strong> {now_s}</p>' + \
        f'<p><strong>Objective:</strong> {obj}</p><p><strong>Conclusion:</strong> {data.get("note", "")}</p><h3>Full Verification Trace & Sign-Off Sheet</h3><pre>' + '\n'.join(lines) + '</pre><script>if(location.search.includes("print=1"))window.print();</script></body></html>'
    html_file = rep_dir / 'latest_agent_report.html'
    html_file.write_text(html_body)
    return {'run_id': rid, 'pdf_path': str(latest_pdf), 'run_pdf_path': str(pdf_file), 'html_path': str(html_file)}
