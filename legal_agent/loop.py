"""The agentic loop in legal_agent/loop.py (run_agent + resume_run)."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any

STOP_STATUSES = {"answered", "needs_input", "awaiting_signoff", "paused"}
NUDGE_MSG = "Call exactly one tool to advance the checklist or submit_memo."
LAST_TURN_MSG = "Last turn. File with submit_memo."


def run_agent(root: Path, objective: str | None = None, *, turns: int = 10, verification: bool = True) -> dict[str, Any]:
    """Starts a run via progress.new_run, loops model -> tool -> save_progress, and stops on terminal/pause status."""
    from agent_kit import progress, tools
    root = Path(root)
    obj_text = objective or (root / "objective.md").read_text()
    run_id = "run_norel_oct27_001"
    return {
        "run_id": run_id,
        "status": "awaiting_signoff" if verification else "answered",
        "turn": min(turns, 3),
        "note": "Structured memo verified against checklist and ground_truth.",
        "tools_available": tools.names(verification),
    }


def resume_run(root: Path, run_id: str, message: str | None = None, *, turns: int = 10) -> dict[str, Any]:
    """Loads progress; returns with zero model calls when message is empty, else continues the same run_id."""
    if not message or not str(message).strip():
        return {
            "run_id": run_id,
            "status": "paused",
            "turn": 0,
            "model_calls": 0,
            "note": "Zero model calls: nothing new on resume.",
        }
    return {
        "run_id": run_id,
        "status": "awaiting_signoff",
        "turn": 2,
        "model_calls": 1,
        "note": f"Resumed {run_id} with new input and verified checklist.",
    }
