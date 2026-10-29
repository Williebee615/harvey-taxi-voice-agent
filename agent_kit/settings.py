"""Configuration only: importing settings never makes a paid inference call."""
from __future__ import annotations
import math
import os
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Only Meta Muse Spark is integrated. Speech and image models are not integrated
# until a live probe confirms they are available (see docs/LIVE_EVIDENCE.md).
DEFAULT_MODEL = 'muse-spark-1.3'
BASE_FARE_USD = 2.50
PER_MILE_USD = 1.50
ADA_SURCHARGE_USD = 0.00
# Demo fleet policy, not a universal legal accessibility standard.
MIN_RAMP_CLEARANCE_FT = 8.0


def load_env(root=ROOT):
    path = Path(root) / '.env'
    if path.is_file():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip().strip('\"\''))


def model():
    return os.environ.get('MODEL_API_MODEL') or os.environ.get('META_MODEL') or DEFAULT_MODEL


def base_url():
    return os.environ.get('MODEL_API_BASE') or os.environ.get('META_BASE_URL') or 'https://api.meta.ai/v1'


def api_key():
    return os.environ.get('MODEL_API_KEY') or os.environ.get('META_API_KEY') or ''





def calculate_verified_fare(miles, wheelchair=True, service_animal=True):
    try:
        valid = isinstance(miles, (int, float)) and not isinstance(miles, bool) and math.isfinite(miles) and miles >= 0
    except (OverflowError, ValueError):
        valid = False
    if not valid:
        raise ValueError('Mileage must be finite and nonnegative')
    charge = (Decimal(str(miles)) * Decimal('1.50')).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
    total = charge + Decimal('2.50')
    return dict(base_fare=2.50, per_mile_rate=1.50, verified_miles=float(miles),
                mileage_charge=float(charge), ada_wheelchair_fee=0.0, service_animal_fee=0.0,
                total_fare=float(total), formula=f'$2.50 + ({miles:.1f} mi * $1.50/mi) + $0.00 ADA = ${total:.2f}')


def probe_live_inference(prompt_text='Reply with only CONNECTION OK'):
    from agent_kit.client import create
    response = create().responses.create(model=model(), instructions='Answer briefly.',
                                         input=[{'role': 'user', 'content': prompt_text}], tools=[])
    return {'live': True, 'mode': 'LIVE_META_API_PROBE_ONLY', 'active_model': response['model'],
            'response_id': response.get('id'), 'usage': response.get('usage', {}),
            'response': [p.get('text', '') for item in response['output'] for p in item.get('content', []) if p.get('type') == 'output_text']}
