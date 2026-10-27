"""Evaluates whether the verified booking memo is ready for human sign-off and release."""
from __future__ import annotations
from typing import Any

def evaluate_release_readiness(checklist_verified: int, signature_checks_passed: bool, fare_usd: float) -> dict[str, Any]:
    expected_fare = 2.50 + (1.50 * 6)
    ready = (checklist_verified >= 5) and signature_checks_passed and abs(fare_usd - expected_fare) < 0.001
    return {
        "ready_for_signoff": ready,
        "expected_fare_usd": expected_fare,
        "actual_fare_usd": fare_usd,
        "terminal_status": "awaiting_signoff" if ready else "needs_input"
    }
