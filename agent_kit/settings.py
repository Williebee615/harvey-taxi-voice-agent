from __future__ import annotations
import os, json, urllib.request
from pathlib import Path

MODEL_ROLES = {
    'reasoning': 'muse-spark-1.5',
    'fine_tuned_verifier': 'accounts/williebee615/models/ft-f7pywv9kusek5#accounts/williebee615/deployments/myxfl5zq',
    'base_open_weight': 'accounts/fireworks/models/muse-glimmer-30b',
    'speech_intake': 'muse-wonder-audio-1.0',
    'visual_curb_verifier': 'sam-3.1-curb-segmentation'
}

MODEL_API_MODEL = os.environ.get('MODEL_API_MODEL', MODEL_ROLES['reasoning'])
FIREWORKS_BASE_MODEL = MODEL_ROLES['base_open_weight']
FIREWORKS_DEPLOYED_MODEL = MODEL_ROLES['fine_tuned_verifier']
FIREWORKS_MODEL = os.environ.get('FIREWORKS_MODEL', FIREWORKS_DEPLOYED_MODEL)
FIREWORKS_DEPLOYMENT_ID = 'accounts/williebee615/deployments/myxfl5zq'
FIREWORKS_FINETUNE_JOB_ID = 'vxd87q0r'
FIREWORKS_OUTPUT_MODEL = os.environ.get('FIREWORKS_OUTPUT_MODEL', 'ft-f7pywv9kusek5')
CASE_DIR = os.environ.get('CASE_DIR', 'cases/harvey-taxi-ada-doctor-visit')
VERIFICATION = os.environ.get('VERIFICATION', 'on')

BASE_FARE_USD = 2.50
PER_MILE_USD = 1.50
ADA_SURCHARGE_USD = 0.00
MIN_RAMP_CLEARANCE_FT = 8.0

def calculate_verified_fare(miles: float, wheelchair: bool = True, service_animal: bool = True) -> dict:
    if miles < 0:
        raise ValueError('Verified mileage cannot be negative')
    mileage_charge = round(miles * PER_MILE_USD, 2)
    total = round(BASE_FARE_USD + mileage_charge + ADA_SURCHARGE_USD, 2)
    return {
        'base_fare': BASE_FARE_USD,
        'per_mile_rate': PER_MILE_USD,
        'verified_miles': round(miles, 2),
        'mileage_charge': mileage_charge,
        'ada_wheelchair_fee': ADA_SURCHARGE_USD,
        'service_animal_fee': ADA_SURCHARGE_USD,
        'total_fare': total,
        'formula': f'${BASE_FARE_USD:.2f} + ({miles:.1f} mi * ${PER_MILE_USD:.2f}/mi) + $0.00 ADA = ${total:.2f}'
    }

def probe_live_inference(prompt_text: str = 'Verify Harvey Taxi 6.0 mile ADA fare ($2.50 + $1.50/mi, $0 ADA fee).') -> dict:
    fw_key = os.environ.get('FIREWORKS_API_KEY', '').strip()
    if fw_key:
        for candidate in [FIREWORKS_DEPLOYED_MODEL, FIREWORKS_BASE_MODEL]:
            try:
                payload = json.dumps({
                    'model': candidate,
                    'messages': [
                        {'role': 'system', 'content': 'You are the Harvey Taxi ADA Verification Agent. Be concise.'},
                        {'role': 'user', 'content': prompt_text}
                    ],
                    'max_tokens': 90,
                    'temperature': 0.0
                }).encode('utf-8')
                req = urllib.request.Request(
                    'https://api.fireworks.ai/inference/v1/chat/completions',
                    data=payload,
                    headers={'Authorization': f'Bearer {fw_key}', 'Content-Type': 'application/json', 'User-Agent': 'HarveyTaxi-Verifier/1.0'}
                )
                with urllib.request.urlopen(req, timeout=8) as r:
                    if r.status == 200:
                        data = json.loads(r.read().decode('utf-8'))
                        return {
                            'live': True,
                            'mode': 'LIVE_FIREWORKS_DEPLOYED_LORA' if '#' in candidate else 'LIVE_FIREWORKS_MUSE_GLIMMER_30B',
                            'active_model': candidate,
                            'response': data['choices'][0]['message']['content'].strip(),
                            'usage': data.get('usage', {})
                        }
            except Exception:
                continue
    return {
        'live': False,
        'mode': 'DETERMINISTIC_FALLBACK_SIMULATION',
        'active_model': 'deterministic-local-verifier',
        'response': None,
        'usage': {}
    }

def inference_mode() -> str:
    if not (os.environ.get('FIREWORKS_API_KEY') or os.environ.get('META_API_KEY') or os.environ.get('MODEL_API_KEY')):
        return 'DETERMINISTIC_FALLBACK_SIMULATION'
    return probe_live_inference()['mode']

def model() -> str:
    if os.environ.get('FIREWORKS_API_KEY'):
        return os.environ.get('FIREWORKS_MODEL', FIREWORKS_DEPLOYED_MODEL)
    return os.environ.get('MODEL_API_MODEL', MODEL_API_MODEL)

def base_url() -> str:
    if os.environ.get('FIREWORKS_API_KEY'):
        return os.environ.get('FIREWORKS_BASE_URL', 'https://api.fireworks.ai/inference/v1')
    return os.environ.get('MODEL_API_BASE', 'https://api.meta.ai/v1')

def verification_enabled() -> bool:
    return os.environ.get('VERIFICATION', VERIFICATION).lower() in ('on', 'true', '1', 'yes')

def case_dir(root_path: str | Path | None = None) -> Path:
    base = Path(root_path) if root_path else Path(__file__).resolve().parent.parent
    return base / os.environ.get('CASE_DIR', CASE_DIR)
