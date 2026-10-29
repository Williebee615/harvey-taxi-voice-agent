"""Meta Muse Voice Transcribe adapter (file endpoint) and a one-call speech probe.

Request shape follows Meta's documentation (dev.meta.ai/docs/speech-to-text,
read 2026-10-29): POST /v1/asr/transcribe, multipart/form-data with a JSON
`request` part and a WAV `audio` part (mono, 16-bit PCM, 16 or 24 kHz, at most
10 minutes, body at most 32 MB). Billing is $0.18 per hour of audio processed,
rounded down to whole seconds; failed and 429 requests are not billed.

The transcript is untrusted rider evidence. It never becomes an instruction.
"""
from __future__ import annotations
import json
import re
import struct
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from agent_kit import client, progress, settings

MODEL = 'muse-voice-transcribe-1.0'
MAX_BYTES = 32 * 1024 * 1024
MAX_SECONDS = 600
USD_PER_HOUR = 0.18
DEMO_AUDIO = Path('cases/demo-spoken-request/spoken_request.wav')
DEMO_SCRIPT = Path('cases/demo-spoken-request/spoken_request_script.txt')
# Facts the demo request must carry through transcription; each is a set of acceptable spellings.
KEY_FACTS = {
    'wheelchair': (r'wheel ?chair',),
    'service dog': (r'service dog',),
    'destination': (r'demo community clinic',),
    'date': (r'november (second|2nd|2)\b', r'\b11/2\b'),
    'arrive by': (r'nine forty[- ]?five', r'\b9:45\b', r'\b9 45\b'),
}


def wav_info(data):
    """Validate the documented WAV format and return its duration; raise ValueError otherwise."""
    if len(data) > MAX_BYTES or data[:4] != b'RIFF' or data[8:12] != b'WAVE':
        raise ValueError('Audio must be a RIFF/WAVE file of at most 32 MB')
    pos, fmt, size = 12, None, None
    while pos + 8 <= len(data):
        chunk, length = data[pos:pos + 4], struct.unpack('<I', data[pos + 4:pos + 8])[0]
        if chunk == b'fmt ':
            fmt = struct.unpack('<HHIIHH', data[pos + 8:pos + 24])
        elif chunk == b'data':
            size = min(length, len(data) - pos - 8)
            break
        pos += 8 + length + (length & 1)
    if not fmt or size is None:
        raise ValueError('WAV file is missing its format or data section')
    audio_format, channels, rate, _, _, bits = fmt
    if audio_format != 1 or channels != 1 or bits != 16 or rate not in (16000, 24000):
        raise ValueError('Audio must be mono 16-bit PCM at 16 kHz or 24 kHz')
    seconds = size / (rate * 2)
    if seconds > MAX_SECONDS:
        raise ValueError('Audio must be 10 minutes or shorter')
    return {'sample_rate': rate, 'seconds': round(seconds, 3)}


def _multipart(settings_json, audio):
    boundary = 'harvey-' + uuid.uuid4().hex
    parts = [f'--{boundary}\r\nContent-Disposition: form-data; name="request"\r\nContent-Type: application/json\r\n\r\n'.encode()
             + json.dumps(settings_json).encode() + b'\r\n',
             f'--{boundary}\r\nContent-Disposition: form-data; name="audio"; filename="request.wav"\r\nContent-Type: audio/wav\r\n\r\n'.encode()
             + audio + b'\r\n', f'--{boundary}--\r\n'.encode()]
    return b''.join(parts), 'multipart/form-data; boundary=' + boundary


def transcribe(audio, keywords=None, opener=None):
    """One file transcription. Returns the transcript and metadata; raises client.ModelError without remote bodies."""
    info = wav_info(audio)
    base = settings.base_url().rstrip('/')
    key = settings.api_key().strip()
    if base != 'https://api.meta.ai/v1':
        raise client.ModelError('This adapter only sends credentials to https://api.meta.ai/v1.')
    if not key or key.startswith('YOUR_'):
        raise client.ModelError('Meta key missing or placeholder. Set MODEL_API_KEY locally.')
    request_settings = {'model': MODEL, 'audioEncoding': 'WAV', 'mode': 'PUSH_TO_TALK'}
    if keywords:
        request_settings['keywords'] = list(keywords)
    body, content_type = _multipart(request_settings, audio)
    session = 'harvey-' + uuid.uuid4().hex[:12]
    request = urllib.request.Request(f'{base}/asr/transcribe?sessionId={session}', data=body, method='POST',
                                     headers={'Authorization': 'Bearer ' + key, 'Content-Type': content_type, 'Accept': 'application/json'})
    started = time.monotonic()
    try:
        with (opener or urllib.request.build_opener(client.NoRedirect())).open(request, timeout=60) as result:
            data = json.load(result)
    except urllib.error.HTTPError as error:
        hints = {400: 'Audio or request rejected; check the WAV format and settings.', 401: 'Authentication rejected.',
                 406: 'Unsupported Accept header.', 413: 'Audio too large.', 429: 'Rate or stream limit reached; not billed.',
                 500: 'Transcription failed on the server.'}
        raise client.ModelError(f'Meta HTTP {error.code}; {hints.get(error.code, "Provider error.")}') from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise client.ModelError('Meta network/TLS connection failed or timed out.') from None
    except (ValueError, TypeError):
        raise client.ModelError('Meta returned an invalid JSON response.') from None
    if not isinstance(data, dict) or not isinstance(data.get('transcript'), str):
        raise client.ModelError('Meta transcription response is missing the transcript.')
    duration_ms = data.get('audioDurationMs')
    billed = int(duration_ms // 1000) if isinstance(duration_ms, (int, float)) else None
    return {'transcript': data['transcript'], 'session_id': data.get('sessionId'), 'model': MODEL,
            'audio_duration_ms': duration_ms, 'local_audio_seconds': info['seconds'],
            'latency_ms': round((time.monotonic() - started) * 1000),
            'billed_seconds_estimate': billed,
            'cost_usd_estimate': round(billed * USD_PER_HOUR / 3600, 6) if billed is not None else None}


def _words(text):
    return re.sub(r"[^a-z0-9:' ]+", ' ', text.lower()).split()


def word_error_rate(reference, hypothesis):
    ref, hyp = _words(reference), _words(hypothesis)
    row = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        prev, row[0] = row[0], i
        for j, h in enumerate(hyp, 1):
            prev, row[j] = row[j], min(row[j] + 1, row[j - 1] + 1, prev + (r != h))
    return round(row[-1] / max(len(ref), 1), 3)


def key_fact_checks(transcript):
    text = ' '.join(_words(transcript))
    return {name: any(re.search(p, text) for p in patterns) for name, patterns in KEY_FACTS.items()}


def speech_probe(root):
    """Exactly one paid transcription of the fictional demo request; saves metadata to workspace/probes/."""
    settings.load_env(root)
    root = Path(root)
    script = (root / DEMO_SCRIPT).read_text().strip()
    result = {'probe_version': 1, 'kind': 'speech', 'timestamp': progress.now(), 'endpoint': 'https://api.meta.ai/v1/asr/transcribe',
              'model': MODEL, 'audio': str(DEMO_AUDIO), 'audio_source': 'synthetic voice (espeak-ng) reading a fictional script',
              'keywords_sent': False, 'paid_inference_calls': 1}
    try:
        out = transcribe((root / DEMO_AUDIO).read_bytes())
    except client.ModelError as error:
        result.update(status='REQUEST_REJECTED_OR_FAILED', error=str(error), inference_succeeded=False)
    else:
        facts = key_fact_checks(out['transcript'])
        result.update(out, status='PASSED' if all(facts.values()) else 'TRANSCRIBED_WITH_MISSING_FACTS',
                      inference_succeeded=True, reference_script=script,
                      word_error_rate=word_error_rate(script, out['transcript']), key_fact_checks=facts)
    path = root / 'workspace' / 'probes' / ('speech_' + result['timestamp'].replace(':', '').replace('+', '_') + '.json')
    progress.atomic_write(path, result)
    result['saved_to'] = str(path.relative_to(root))
    return result
