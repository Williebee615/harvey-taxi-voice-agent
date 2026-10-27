"""World simulation utilities for safe paste buffering and completion report formatting."""
from __future__ import annotations

def format_completion_report(files_changed: list[str], command_ran: str, limitation: str) -> dict[str, object]:
    return {
        "files_changed": files_changed,
        "ran": command_ran,
        "limitation": limitation
    }
