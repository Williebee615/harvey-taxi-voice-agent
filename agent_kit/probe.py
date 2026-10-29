"""Capability probes for the Meta Model API. Records metadata only, never keys.

Three questions, at most one paid inference call:
1. Which model IDs does this account list?        GET /models (no inference)
2. Does Muse Spark read an image through Responses? One call with the fictional card
3. Are SAM 3.1 or speech models available?          Answered from the model list only.
   No request is sent to them: their request formats are not verified yet, and a
   guessed format would not be evidence either way.
"""
from __future__ import annotations
import base64
import json
import re
import urllib.error
import urllib.request
from pathlib import Path
from agent_kit import client, progress, settings

CARD = Path('cases/demo-appointment-card/appointment_card.png')
EXPECTED = {'appointment_date': '2026-11-02', 'appointment_time': '10:00',
            'arrive_by': '09:45', 'destination': 'Demo Community Clinic'}
PROMPT = ('This is a fictional demo appointment card. Extract transportation details. Reply with only a JSON '
          'object with keys appointment_date (YYYY-MM-DD), appointment_time (HH:MM, 24-hour), '
          'arrive_by (HH:MM, 24-hour), destination (string). Use null for anything not shown.')
SPEECH = re.compile(r'transcrib|voice|audio|speech|whisper', re.I)
SEGMENT = re.compile(r'\bsam\b|sam[-_ ]?3|segment', re.I)


def _base():
    base = settings.base_url().rstrip('/')
    if base != 'https://api.meta.ai/v1':
        raise client.ModelError('Probes only send credentials to https://api.meta.ai/v1.')
    key = settings.api_key().strip()
    if not key or key.startswith('YOUR_'):
        raise client.ModelError('Meta key missing or placeholder. Set MODEL_API_KEY locally.')
    return base, key


def list_models():
    base, key = _base()
    request = urllib.request.Request(base + '/models', headers={'Authorization': 'Bearer ' + key})
    try:
        with urllib.request.build_opener(client.NoRedirect()).open(request, timeout=30) as result:
            data = json.load(result)
    except urllib.error.HTTPError as error:
        return {'status': 'UNAVAILABLE', 'http_status': error.code, 'model_ids': []}
    except (urllib.error.URLError, TimeoutError, OSError):
        return {'status': 'NETWORK_ERROR', 'model_ids': []}
    except (ValueError, TypeError):
        return {'status': 'INVALID_JSON', 'model_ids': []}
    items = data.get('data') if isinstance(data, dict) else None
    ids = sorted({x['id'] for x in items or [] if isinstance(x, dict) and isinstance(x.get('id'), str)})
    return {'status': 'LISTED' if ids else 'EMPTY_OR_UNRECOGNIZED_SHAPE', 'model_ids': ids}


def _fields(text):
    match = re.search(r'\{.*\}', text or '', re.S)
    try:
        data = json.loads(match[0]) if match else None
    except ValueError:
        data = None
    return data if isinstance(data, dict) else None


def image_probe(root):
    image = base64.b64encode((Path(root) / CARD).read_bytes()).decode()
    content = [{'type': 'input_text', 'text': PROMPT},
               {'type': 'input_image', 'image_url': 'data:image/png;base64,' + image}]
    try:
        response = client.create().responses.create(model=settings.model(), instructions='Answer only from the image.',
                                                     input=[{'role': 'user', 'content': content}], tools=[])
    except client.ModelError as error:
        return {'status': 'REQUEST_REJECTED_OR_FAILED', 'error': str(error), 'inference_succeeded': False}
    text = ''.join(p.get('text', '') for item in response['output'] for p in item.get('content', []) or []
                   if isinstance(p, dict) and p.get('type') == 'output_text')
    fields = _fields(text)
    checks = {k: bool(fields) and isinstance(fields.get(k), str) and (v in fields[k] if k == 'destination' else fields[k] == v)
              for k, v in EXPECTED.items()}
    return {'status': 'PASSED' if all(checks.values()) else 'MODEL_RESPONDED_FIELDS_MISMATCH',
            'inference_succeeded': True, 'response_id': response['id'], 'model': response['model'],
            'usage': response.get('usage', {}), 'extracted': fields, 'expected': EXPECTED, 'field_checks': checks,
            'note': 'Fictional card. Request shape (input_image data URL) is an assumption until this probe passes.'}


def run(root, image=True):
    settings.load_env(root)
    _base()
    models = list_models()
    ids = models['model_ids']
    def availability(pattern):
        if models['status'] != 'LISTED':
            return {'status': 'UNKNOWN_MODEL_LIST_UNAVAILABLE', 'candidates': []}
        found = [x for x in ids if pattern.search(x)]
        return {'status': 'LISTED' if found else 'NOT_LISTED', 'candidates': found,
                'request_sent': False, 'request_format_verified': False}
    result = {'probe_version': 1, 'timestamp': progress.now(), 'endpoint': 'https://api.meta.ai/v1',
              'configured_model': settings.model(), 'models': models,
              'image_input': image_probe(root) if image else {'status': 'SKIPPED'},
              'sam_segmentation': availability(SEGMENT), 'speech': availability(SPEECH),
              'paid_inference_calls': 1 if image else 0}
    out = Path(root) / 'workspace' / 'probes' / ('probe_' + result['timestamp'].replace(':', '').replace('+', '_') + '.json')
    progress.atomic_write(out, result)
    result['saved_to'] = str(out.relative_to(root))
    return result
