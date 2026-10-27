"""Meta Model API client (OpenAI SDK pointed at https://api.meta.ai/v1) — never logs API keys."""
from __future__ import annotations
import os
from typing import Any
from .settings import Settings

def get_client_config(settings: Settings | None = None) -> dict[str, Any]:
    s = settings or Settings.from_env()
    has_key = bool(os.environ.get("META_API_KEY") or os.environ.get("MODEL_API_KEY"))
    return {
        "provider": s.provider,
        "base_url": s.base_url,
        "model": s.model(),
        "api_key_configured": has_key,
        "cli_command": "muse --provider meta --base-url https://api.meta.ai/v1 --model muse-spark-1.5"
    }
