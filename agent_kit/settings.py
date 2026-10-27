from __future__ import annotations
import os
from pathlib import Path
DEFAULT_MODEL = 'muse-spark-1.5'
BASE_URL = 'https://api.meta.ai/v1'
def model() -> str:
    return os.environ.get('MODEL_NAME', DEFAULT_MODEL)
def base_url() -> str:
    return os.environ.get('MODEL_BASE_URL', BASE_URL)
def case_dir(root: str | Path) -> Path:
    return Path(root) / 'cases' / 'harvey-taxi-ada-doctor-visit'
