"""Check the hosted console after a deploy without any Meta API charges.

Runs only Offline simulation (no model, no Meta calls) and refuses any record that shows live inference.
The reviewer password is read from the CONSOLEPW environment variable and is never printed.
Modal hosting time is still used while it runs.
Usage: python3 audit/hosted_check.py https://...modal.run
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.request

DEMO = ('Hi, this is Jordan Ellis. I need a wheelchair-accessible ride with my service dog to Demo Community Clinic '
        'on Monday, November second. I need to arrive by nine forty-five in the morning.')
EARLIER_RUNS = ('run_b2023b2da615466fba74a611b17ec923', 'run_0e228025cdfe4b6397add01fc117c7eb')


def call(base, path, password=None, body=None, token=None):
    headers = {}
    if password is not None:
        headers['Authorization'] = 'Basic ' + base64.b64encode(f'reviewer:{password}'.encode()).decode()
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers.update({'Content-Type': 'application/json', 'X-Console-Token': token or ''})
    request = urllib.request.Request(base + path, data=data, headers=headers, method='POST' if data else 'GET')
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.status, json.loads(response.read() or b'null') if 'json' in response.headers.get('Content-Type', '') else None
    except urllib.error.HTTPError as error:
        return error.code, None


def offline_review(base, password, token, case, spoken=None):
    status, record = call(base, '/api/run', password, {'case': case, 'mode': 'simulation', 'spoken_request': spoken}, token)
    for _ in range(40):
        if status != 200 or record['status'] != 'paused':
            break
        status, record = call(base, '/api/continue', password, {'run_id': record['run_id'], 'message': ''}, token)
    if status != 200:
        return {'ok': False, 'http': status}
    live = record.get('model_invoked_in_run') or record.get('receipts') or record.get('inference_mode') != 'DETERMINISTIC_FALLBACK_SIMULATION'
    failed = sorted(k for k, v in record['verification'].items() if not v['passed'])
    return {'ok': not live, 'run_id': record['run_id'], 'status': record['status'], 'failed_checks': failed,
            'checks': len(record['verification']), 'meta_calls': len(record.get('receipts', [])),
            'integrity': record.get('run_integrity', {}).get('passed')}


def main(base):
    base = base.rstrip('/')
    password = os.environ.get('CONSOLEPW', '')
    if len(password) < 16:
        sys.exit('Set CONSOLEPW to the reviewer password first (it is not printed).')
    results = {'no_password': call(base, '/')[0], 'wrong_password': call(base, '/api/config', 'not-the-password-0000')[0]}
    status, config = call(base, '/api/config', password)
    results['signed_in'] = status
    if status != 200:
        print(json.dumps(results, indent=1)); sys.exit(1)
    token = config['token']
    results['stale_token'] = call(base, '/api/run', password, {'case': 'healthcare-clinic-visit', 'mode': 'simulation'}, 'stale-token')[0]
    status, runs = call(base, '/api/runs', password)
    results['saved_runs_listed'] = len(runs or [])
    results['earlier_runs'] = {}
    for run_id in EARLIER_RUNS:
        status, record = call(base, f'/api/run?id={run_id}', password)
        results['earlier_runs'][run_id[:12]] = record['status'] if status == 200 else f'HTTP {status}'
    results['take1_appointment_card'] = offline_review(base, password, token, 'healthcare-appointment-card', DEMO)
    results['take2_card_contradiction'] = offline_review(base, password, token, 'healthcare-card-contradiction')
    take1, take2 = results['take1_appointment_card'], results['take2_card_contradiction']
    passed = (results['no_password'] == 401 and results['wrong_password'] == 401 and results['signed_in'] == 200
              and results['stale_token'] == 403 and take1.get('ok') and take2.get('ok')
              and take1.get('status') == 'awaiting_signoff' and take1.get('failed_checks') == [] and take1.get('checks') == 9
              and take2.get('status') == 'needs_input' and take2.get('failed_checks') == ['appointment_card_check']
              and take1.get('meta_calls') == 0 and take2.get('meta_calls') == 0
              and all(v == 'completed_after_human_signoff' for v in results['earlier_runs'].values()))
    results['all_checks_passed'] = bool(passed)
    print(json.dumps(results, indent=1))
    sys.exit(0 if passed else 1)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
