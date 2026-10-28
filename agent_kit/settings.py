from __future__ import annotations
import os
from pathlib import Path
MODEL_API_MODEL = os.environ.get('MODEL_API_MODEL', 'muse-spark-1.5')
FIREWORKS_MODEL = os.environ.get('FIREWORKS_MODEL', 'accounts/fireworks/models/muse-glimmer-30b')
CASE_DIR = os.environ.get('CASE_DIR', 'cases/harvey-taxi-ada-doctor-visit')
VERIFICATION = os.environ.get('VERIFICATION', 'on')
def model() -> str:
    if os.environ.get('FIREWORKS_API_KEY'):
        return os.environ.get('FIREWORKS_MODEL', 'accounts/fireworks/models/muse-glimmer-30b')
    return os.environ.get('MODEL_API_MODEL', MODEL_API_MODEL)
def base_url() -> str:
    if os.environ.get('FIREWORKS_API_KEY'):
        return os.environ.get('FIREWORKS_BASE_URL', 'https://api.fireworks.ai/inference/v1')
    return os.environ.get('MODEL_API_BASE', 'https://api.meta.ai/v1')
def verification_enabled() -> bool:
    return os.environ.get('VERIFICATION', VERIFICATION).lower() in ('on', 'true', '1', 'yes')
def case_dir(root: str | Path | None = None) -> Path:
    base = Path(root) if root else Path(__file__).resolve().parent.parent
    return base / os.environ.get('CASE_DIR', CASE_DIR)
