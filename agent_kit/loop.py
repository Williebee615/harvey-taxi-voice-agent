"""The agentic loop in agent_kit/loop.py (run_agent + resume_run) for Norel AI."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

STOP_STATUSES = {"answered", "needs_input", "awaiting_signoff", "paused"}
NUDGE_MSG = "Call exactly one tool to advance the checklist or submit_memo."
LAST_TURN_MSG = "Last turn. File with submit_memo."
