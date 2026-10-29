"""Local-only console API. No arbitrary filesystem serving, CORS, or credential exposure."""
from __future__ import annotations
import json
import secrets
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from agent_kit import evidence, progress, settings
from harvey_agent.loop import approve_run, resume_run, run_agent


class ConsoleServer(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, address, root=ROOT):
        super().__init__(address, Handler)
        self.root = Path(root)
        self.token = secrets.token_urlsafe(32)
        self.mutation_lock = threading.Lock()


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
                cases = [p.name for p in (self.server.root / 'cases').iterdir() if not p.is_symlink() and (p / 'inbox').is_dir()]
                return self.send(200, {'token': self.server.token, 'model': settings.model(), 'key_configured': bool(settings.api_key()), 'cases': sorted(cases), 'dispatch_enabled': False})
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
        if not self.allowed_host() or origin not in (None, f'http://127.0.0.1:{port}', f'http://localhost:{port}') or not secrets.compare_digest(self.headers.get('X-Console-Token', ''), self.server.token):
            return self.send(403, {'error': 'Local console token and origin required'})
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
                result = run_agent(root, turns=1, objective=body.get('objective'), case_name=body.get('case'), mode=body.get('mode', 'simulation'))
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
