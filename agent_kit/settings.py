from __future__ import annotations
import os
from pathlib import Path
DEFAULT_MODEL = 'muse-spark-1.5'
BASE_URL = 'https://api.meta.ai/v1'
def model() -> str:
    return os.environ.get('MODEL_API_MODEL') or os.environ.get('MODEL_NAME') or DEFAULT_MODEL
def base_url() -> str:
    return os.environ.get('MODEL_BASE_URL', BASE_URL)
def case_dir(root: str | Path) -> Path:
    c = os.environ.get('CASE_DIR', 'cases/northbridge-v-caldera')
    p = Path(root) / c
    return p if p.exists() else Path(root) / 'cases' / 'harvey-taxi-ada-doctor-visit'
def verification_enabled() -> bool:
    return os.environ.get('VERIFICATION', 'true').lower() not in ('0', 'false', 'no')
