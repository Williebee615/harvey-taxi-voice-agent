"""Local-only console API. No arbitrary filesystem serving, CORS, or credential exposure."""
from __future__ import annotations
import json
import secrets
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from agent_kit import client, evidence, progress, settings, speech

MAX_AUDIO_BYTES = 2_100_000   # about 65 s of 16 kHz mono 16-bit WAV
MAX_AUDIO_SECONDS = 60
DRAIN_LIMIT_BYTES = 8_000_000  # read and discard oversized uploads up to this size so the client gets a clean 413
TRANSCRIPT_TTL_SECONDS = 30 * 60
from harvey_agent.loop import approve_run, resume_run, run_agent


class ConsoleServer(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, address, root=ROOT, token=None):
        super().__init__(address, Handler)
        self.root = Path(root)
        # A hosted deployment passes a token that survives container restarts; locally it is random per process.
        self.token = token or secrets.token_urlsafe(32)
        self.mutation_lock = threading.Lock()
        # Meta transcripts held server-side until the reviewer confirms one, so the browser
        # cannot submit altered text under the Meta label.
        self.transcripts = {}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # Do not log request paths or source evidence.

    def send(self, status, data, content_type='application/json; charset=utf-8'):
        out = data if isinstance(data, bytes) else json.dumps(data, allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(out)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(out)

    def allowed_host(self):
        port = self.server.server_port
        return self.headers.get('Host') in (f'127.0.0.1:{port}', f'localhost:{port}')

    def do_GET(self):
        if not self.allowed_host():
            return self.send(403, {'error': 'Local host required'})
        parsed = urlsplit(self.path)
        static = {'/': ('index.html', 'text/html; charset=utf-8'),
                  '/index.html': ('index.html', 'text/html; charset=utf-8'),
                  '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                  '/console.css': ('console.css', 'text/css; charset=utf-8')}
        if parsed.path in static:
            path, kind = static[parsed.path]
            return self.send(200, (ROOT / path).read_bytes(), kind)
        try:
            if parsed.path == '/api/config':
                cases = sorted(p.name for p in (self.server.root / 'cases').iterdir() if not p.is_symlink() and (p / 'inbox').is_dir())
                case_images = {c: list(evidence.images(self.server.root, c)) for c in cases}
                return self.send(200, {'token': self.server.token, 'model': settings.model(), 'key_configured': bool(settings.api_key()), 'cases': cases,
                                       'case_images': {c: names for c, names in case_images.items() if names}, 'dispatch_enabled': False})
            if parsed.path == '/api/case-image':
                query = parse_qs(parsed.query)
                case, name = query.get('case', [''])[0], query.get('name', [''])[0]
                image = evidence.images(self.server.root, case).get(name)
                if image is None:
                    raise ValueError('Unknown image')
                return self.send(200, image, evidence.IMAGE_TYPES[Path(name).suffix.lower()])
            if parsed.path == '/api/run':
                rid = parse_qs(parsed.query).get('id', ['run_latest'])[0]
                return self.send(200, progress.public_record(progress.load_progress(self.server.root, rid)))
            if parsed.path == '/api/runs':
                runs = []
                for path in progress.directory(self.server.root).glob('run_*.json'):
                    try:
                        record = json.loads(path.read_text())
                        progress.run_path(self.server.root, record['run_id'])
                        if record.get('schema_version') != 2:
                            continue
                        runs.append({k: record.get(k) for k in ('run_id', 'case', 'status', 'timestamp', 'requested_mode')})
                    except (ValueError, KeyError):
                        continue
                runs = {r['run_id']: r for r in runs}
                return self.send(200, sorted(runs.values(), key=lambda x: x['timestamp'] or '', reverse=True)[:50])
        except (ValueError, OSError, KeyError):
            return self.send(404, {'error': 'Run or case not found'})
        self.send(404, {'error': 'Not found'})

    def do_POST(self):
        port = self.server.server_port
        origin = self.headers.get('Origin')
        if not self.allowed_host() or origin not in (None, f'http://127.0.0.1:{port}', f'http://localhost:{port}'):
            return self.send(403, {'error': 'Local console token and origin required'})
        if not secrets.compare_digest(self.headers.get('X-Console-Token', ''), self.server.token):
            # Host and origin are fine, so the page holds a token from an earlier server process.
            return self.send(403, {'error': 'Console session expired. Nothing was sent.', 'code': 'session_expired'})
        if self.path == '/api/transcribe':
            return self.transcribe()
        if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            return self.send(415, {'error': 'Use application/json'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 128_000:
                return self.send(413, {'error': 'Invalid request size'})
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError('Expected JSON object')
        except (ValueError, TypeError):
            return self.send(400, {'error': 'Invalid JSON request'})
        if not self.server.mutation_lock.acquire(blocking=False):
            return self.send(409, {'error': 'An agent step is already running'})
        try:
            root = self.server.root
            if self.path == '/api/run':
                spoken, source = body.get('spoken_request') or None, None
                if body.get('transcription_id') is not None:
                    if spoken is not None or body.get('transcript_confirmed') is not True:
                        raise ValueError('A Meta transcript must be confirmed and sent without separate text')
                    try:
                        held = self.take_transcript(body['transcription_id'])
                    except ValueError:
                        return self.send(410, {'error': 'This Meta transcript was already used, has expired, or the console restarted. Record again; nothing was sent for review.', 'code': 'transcript_expired'})
                    spoken, source = held['transcript'], {**held['source'], 'confirmed_by_reviewer': True}
                result = run_agent(root, turns=1, objective=body.get('objective'), case_name=body.get('case'), mode=body.get('mode', 'simulation'),
                                   spoken_request=spoken, speech_source=source)
            elif self.path == '/api/continue':
                message = body.get('message', '')
                if not isinstance(message, str):
                    raise ValueError('Follow-up must be text')
                result = resume_run(root, body.get('run_id', ''), message=message, turns=1)
            elif self.path == '/api/approve':
                result = approve_run(root, body.get('run_id', ''), body.get('signature', ''))
            else:
                return self.send(404, {'error': 'Unknown endpoint'})
            self.send(200, progress.public_record(result))
        except (ValueError, TypeError, KeyError, OSError):
            self.send(400, {'error': 'Request refused. Check the run status, source evidence, reviewer name and inputs.'})
        except Exception:
            self.send(500, {'error': 'Agent operation failed; inspect the saved run and retry explicitly.'})
        finally:
            self.server.mutation_lock.release()


    def take_transcript(self, transcription_id):
        now = time.monotonic()
        for key in [k for k, v in self.server.transcripts.items() if now - v['created'] > TRANSCRIPT_TTL_SECONDS]:
            del self.server.transcripts[key]
        held = self.server.transcripts.pop(transcription_id, None) if isinstance(transcription_id, str) else None
        if held is None:
            raise ValueError('Unknown or expired transcript')
        return held

    def transcribe(self):
        """Send one browser recording to Meta Muse Voice Transcribe. The key stays on this server."""
        if self.headers.get('Content-Type', '').split(';')[0] != 'audio/wav':
            return self.send(415, {'error': 'Use audio/wav'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            length = 0
        if not 44 < length <= MAX_AUDIO_BYTES:
            # Replying before the body is read can reset the connection mid-upload (seen on macOS),
            # turning a clear 413 into a network error. Drain moderately sized bodies first.
            if 0 < length <= DRAIN_LIMIT_BYTES:
                remaining = length
                while remaining > 0:
                    chunk = self.rfile.read(min(65536, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
            else:
                self.close_connection = True
            return self.send(413, {'error': 'Recording must be at most 60 seconds'})
        audio = self.rfile.read(length)
        try:
            seconds = speech.wav_info(audio)['seconds']
            if not 0.3 <= seconds <= MAX_AUDIO_SECONDS:
                raise ValueError('Recording must be between 0.3 and 60 seconds')
        except ValueError as error:
            return self.send(400, {'error': str(error)})
        if not self.server.mutation_lock.acquire(blocking=False):
            return self.send(409, {'error': 'An agent step is already running'})
        try:
            heard = speech.transcribe(audio)
        except client.ModelError as error:
            return self.send(502, {'error': str(error)})
        finally:
            self.server.mutation_lock.release()
        source = {k: heard[k] for k in ('model', 'session_id', 'audio_duration_ms', 'latency_ms', 'billed_seconds_estimate', 'cost_usd_estimate')}
        transcription_id = 'tx_' + uuid.uuid4().hex
        if len(self.server.transcripts) >= 20:
            self.server.transcripts.pop(next(iter(self.server.transcripts)))
        self.server.transcripts[transcription_id] = {'transcript': heard['transcript'], 'source': source, 'created': time.monotonic()}
        return self.send(200, {'transcription_id': transcription_id, 'transcript': heard['transcript'], **source})


def main(port=8765):
    settings.load_env(ROOT)
    server = ConsoleServer(('127.0.0.1', port))
    print(f'Harvey Taxi Console -> http://127.0.0.1:{server.server_port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
