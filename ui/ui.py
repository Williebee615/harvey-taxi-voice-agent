from __future__ import annotations
import json, sys
from http.server import SimpleHTTPRequestHandler, HTTPServer
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from legal_agent.loop import run_agent, resume_run
class Handler(SimpleHTTPRequestHandler):
    def do_POST(self):
        ln = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(ln).decode() or '{}') if ln else {}
        if self.path == '/api/run':
            res = run_agent(ROOT, objective=body.get('prompt'), case_name=body.get('case'))
        elif self.path == '/api/resume':
            res = resume_run(ROOT, body.get('run_id', ''), body.get('message'))
        else:
            res = {'error': 'unknown endpoint'}
        out = json.dumps(res).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(out)
def main(port=8765):
    print(f'Agent Console -> http://127.0.0.1:{port}  (workshop: {ROOT})')
    if '--check' in sys.argv: return
    HTTPServer(('127.0.0.1', port), Handler).serve_forever()
if __name__ == '__main__':
    main()
