"""Settings loader for Meta Model API (https://api.meta.ai/v1) and case environment."""
from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path

@dataclass
class Settings:
    base_url: str = "https://api.meta.ai/v1"
    provider: str = "meta"
    model_name: str = "muse-spark-1.5"
    verification: bool = True
    case_dir: str = "cases/harvey-taxi-ada-doctor-visit"

    def model(self) -> str:
        return self.model_name

    @classmethod
    def from_env(cls, root: Path | None = None) -> "Settings":
        verif_raw = os.environ.get("VERIFICATION", "on").lower()
        return cls(
            base_url=os.environ.get("META_BASE_URL", "https://api.meta.ai/v1"),
            provider="meta",
            model_name=os.environ.get("MODEL_NAME", "muse-spark-1.5"),
            verification=verif_raw in ("on", "true", "1", "yes"),
            case_dir=os.environ.get("CASE_DIR", "cases/harvey-taxi-ada-doctor-visit"),
        )
