"""Small, stateless Meta Responses API adapter. No synthetic success or provider fallback."""
from __future__ import annotations
import json
import urllib.error
import urllib.request
from types import SimpleNamespace
from agent_kit import settings


class ModelError(RuntimeError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Responses:
    def create(self, *, model, instructions, input, tools):
        key = settings.api_key().strip()
        if not key or key.startswith('YOUR_'):
            raise ModelError('Meta key missing or placeholder. Set MODEL_API_KEY locally.')
        base = settings.base_url().rstrip('/')
        if base != 'https://api.meta.ai/v1':
            raise ModelError('This adapter only sends credentials to https://api.meta.ai/v1.')
        payload = {'model': model, 'instructions': instructions, 'input': input,
                   'store': False, 'include': ['reasoning.encrypted_content'],
                   'max_output_tokens': 4096}
        if tools:
            payload.update(tools=tools, tool_choice='auto', parallel_tool_calls=False)
        request = urllib.request.Request(base + '/responses', data=json.dumps(payload).encode(),
            headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
        try:
            with urllib.request.build_opener(NoRedirect()).open(request, timeout=45) as result:
                data = json.load(result)
        except urllib.error.HTTPError as error:
            # Do not expose remote error bodies, request headers, or credentials.
            hints = {
                400: 'Request format rejected; check supported API parameters and tool schemas.',
                401: 'Authentication rejected; check the local Meta credential.',
                402: 'Billing or credits required; check the Meta dashboard.',
                403: 'Access denied; check model and project permissions.',
                404: 'Endpoint or model not found; check the configured model.',
                429: 'Rate limit reached; pause and retry explicitly.',
            }
            hint = hints.get(error.code, 'Provider error; retry explicitly after checking service status.')
            raise ModelError(f'Meta HTTP {error.code}; {hint}') from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise ModelError('Meta network/TLS connection failed or timed out; retry explicitly.') from None
        except (ValueError, TypeError):
            raise ModelError('Meta returned an invalid JSON response.') from None
        if not isinstance(data, dict) or not isinstance(data.get('output'), list) or not data.get('model') or not data.get('id'):
            raise ModelError('Meta response is missing output, model, or request ID.')
        if any(not isinstance(item, dict) for item in data['output']):
            raise ModelError('Meta returned malformed output items.')
        if data.get('status') != 'completed':
            raise ModelError('Meta response was incomplete; no tool was executed.')
        return data


def create():
    settings.load_env()
    return SimpleNamespace(responses=Responses())
