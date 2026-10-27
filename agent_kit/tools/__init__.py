"""The agent's tools, one file per tool: its DEFINITION (what the model sees) and
run(ctx, args) (what happens when the model calls it).

    tools.definitions(root, run_id)        # the tools to offer the model in this run
    result = tools.run(client, root, run_id, call)   # run the tool the model chose
    result.get("status", "running")        # "running", or why the run must stop

BASE_TOOLS are the six tools the agent always has. VERIFIER_TOOLS are added for runs
started with VERIFICATION=on, and with it on, set_checklist, analyze_rider_request and
submit_booking_memo also run the checks in agent/verification/ at their fixed points.
"""

from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

BASE_TOOLS = [
    "set_checklist",
    "update_plan",
    "list_documents",
    "analyze_document",
    "record_fact",
    "submit_memo",
]
VERIFIER_TOOLS = ["flag_privileged", "request_evidence", "check_signatures"]


@dataclass
class Context:
    """What a tool gets besides its arguments."""
    client: Any
    root: Path
    run_id: str
    case: Any
    verification: bool


def names(verification: bool) -> list[str]:
    return BASE_TOOLS + VERIFIER_TOOLS if verification else list(BASE_TOOLS)
