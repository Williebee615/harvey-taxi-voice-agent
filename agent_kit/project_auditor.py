from __future__ import annotations
import json
from pathlib import Path
from agent_kit import settings, work_engine, pdf_export
def run_full_audit(root: str | Path) -> dict:
    r = Path(root)
    results = []
    issues = []
    for dom, prm in [
        ('harveytaxiservice.com', 'Dispatch Van #11 for 15 miles from 100 Broadway to BNA Airport'),
        ('turbotax.com', 'Prepare Schedule C and Form 8826 ADA fleet tax credit for $24,500 Van #07'),
        ('va.gov', 'File VA Form 10-3542 BTSS medical ride reimbursement for 10 miles wheelchair trip'),
        ('bna.com', 'Verify Nashville Airport BNA ADA curbside pickup permit and AVI transponder'),
        ('stripe.com', 'Settle hospital NEMT voucher #VCH-9920 for 8 miles trip')
    ]:
        try:
            wk = work_engine.execute_work(r, dom, prm)
            ok = Path(wk['files']['pdf']).exists() and Path(wk['files']['csv']).exists() and len(wk['line_items']) >= 5
            results.append({'component': f'Domain Work Engine [{dom}]', 'status': 'PASS' if ok else 'FAIL', 'detail': wk['deliverable_type']})
            if not ok: issues.append(f'Missing deliverable files for {dom}')
        except Exception as e:
            results.append({'component': f'Domain Work Engine [{dom}]', 'status': 'FAIL', 'detail': str(e)})
            issues.append(f'{dom} error: {e}')
    rep = pdf_export.generate_report(r)
    pdf_ok = Path(rep['pdf_path']).exists() and Path(rep['html_path']).exists()
    results.append({'component': 'PDF & HTML Verification Report Exporter', 'status': 'PASS' if pdf_ok else 'FAIL', 'detail': rep['pdf_path']})
    fw_ok = settings.FIREWORKS_FINETUNE_JOB_ID == 'vxd87q0r' and settings.FIREWORKS_DEPLOYMENT_ID == 'accounts/williebee615/deployments/myxfl5zq'
    results.append({'component': 'Fireworks AI Norel Ai Deployment (myxfl5zq / vxd87q0r / ft-f7pywv9)', 'status': 'PASS' if fw_ok else 'FAIL', 'detail': settings.FIREWORKS_DEPLOYMENT_ID})
    report = {'all_passed': len(issues) == 0, 'total_checked': len(results), 'issues': issues, 'results': results}
    (r / 'workspace' / 'reports' / 'system_health_audit.json').write_text(json.dumps(report, indent=2) + '\n')
    return report
