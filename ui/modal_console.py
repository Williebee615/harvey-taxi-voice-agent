"""Password-gated bridge to the unchanged loopback console, for Modal only."""
import os
import secrets
import threading
from contextlib import asynccontextmanager
from urllib.parse import urlsplit


def create_app(root, commit=lambda: None):
    import httpx
    from fastapi import FastAPI, Request
    from fastapi.responses import Response
    from fastapi.security.utils import get_authorization_scheme_param
    import base64
    from ui.ui import ConsoleServer

    password = os.environ.get('HARVEY_DEMO_PASSWORD', '')
    if len(password) < 16:
        raise ValueError('Set HARVEY_DEMO_PASSWORD to at least 16 characters in Modal Secrets')
    server = ConsoleServer(('127.0.0.1', 0), root=root)
    base = f'http://127.0.0.1:{server.server_port}'
    @asynccontextmanager
    async def lifespan(app):
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        yield
        server.shutdown()
        server.server_close()
    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware('http')
    async def gate(request: Request, call_next):
        scheme, value = get_authorization_scheme_param(request.headers.get('authorization'))
        try:
            username, supplied = base64.b64decode(value, validate=True).decode().split(':', 1)
        except (ValueError, UnicodeError):
            username, supplied = '', ''
        if scheme.lower() != 'basic' or not secrets.compare_digest(username, 'reviewer') or not secrets.compare_digest(supplied.encode(), password.encode()):
            return Response('Reviewer access required', 401, headers={'WWW-Authenticate': 'Basic realm="Harvey Taxi demo"', 'Cache-Control': 'no-store'})
        if request.method not in ('GET', 'POST'):
            return Response(status_code=405)
        origin = request.headers.get('origin')
        if origin and urlsplit(origin).netloc != request.headers.get('host'):
            return Response('Same-origin requests required', 403)
        limit = 2_100_000 if request.url.path == '/api/transcribe' else 128000
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > limit:
                return Response('Request too large', 413)
        headers = {k: request.headers[k] for k in ('content-type', 'x-console-token') if k in request.headers}
        if origin:
            headers['Origin'] = base
        target = base + request.url.path
        if request.url.query:
            target += '?' + request.url.query
        try:
            async with httpx.AsyncClient(timeout=180, follow_redirects=False, trust_env=False) as client:
                result = await client.request(request.method, target, headers=headers, content=bytes(body))
            if request.method == 'POST':
                commit()
            if request.url.path == '/api/config' and result.status_code == 200:
                import json
                config = result.json()
                config['hosting'] = 'modal'
                result = httpx.Response(200, json=config, headers=result.headers)
            returned = {k: v for k, v in result.headers.items() if k in ('content-type', 'cache-control', 'x-content-type-options', 'content-security-policy')}
            return Response(result.content, status_code=result.status_code, headers=returned)
        except Exception:
            return Response('Operation failed; inspect the saved run before retrying.', 503)
    return app
