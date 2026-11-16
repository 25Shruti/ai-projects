
from datetime import datetime, timezone
from uuid import uuid4


ALLOWED_ACTIONS = {"escalate_case", "request_information", "close_alert", "freeze_account"}


def request_approval(alert_id: str, customer_id: str, action: str) -> dict:
    """Create a pending approval request without executing an action."""
    if action not in ALLOWED_ACTIONS:
        return {"error": "Action not permitted"}

    return {
        "request_id": str(uuid4()),
        "alert_id": alert_id,
        "customer_id": customer_id,
        "action": action,
        "status": "PENDING",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "decided_at": None,
        "decided_by": None,
    }


def decide_approval(request: dict, decision: str, analyst: str) -> dict:
    """Record a human decision on a pending request."""
    if request.get("status") != "PENDING":
        return {"error": "Request is not pending"}

    if decision not in {"APPROVED", "REJECTED", "FURTHER_REVIEW"}:
        return {"error": "Invalid decision"}

    if not analyst.strip():
        return {"error": "Analyst identity required"}

    return {
        **request,
        "status": decision,
        "decided_at": datetime.now(timezone.utc).isoformat(),
        "decided_by": analyst.strip(),
    }



def execute_approved_action(request: dict) -> dict:
    """Execute simulated escalation or record an approved recommendation."""

    if request.get("status") != "APPROVED":
        return {"error": "Execution blocked: human approval required"}

    if request.get("action") not in ALLOWED_ACTIONS:
        return {"error": "Action not permitted"}

    if not request.get("decided_by") or not request.get("decided_at"):
        return {"error": "Missing approval evidence"}

    # Advisory recommendations: record approval without execution.
    if request["action"] in {"request_information", "close_alert"}:
        return {
            "execution_id": str(uuid4()),
            "request_id": request["request_id"],
            "action": request["action"],
            "status": "REVIEW_RECORDED",
            "message": "Human approval recorded. No operational action executed.",
            "executed_at": datetime.now(timezone.utc).isoformat(),
        }

    # Escalation or account freeze: simulated execution only.
    return {
        "execution_id": str(uuid4()),
        "request_id": request["request_id"],
        "action": request["action"],
        "status": "SIMULATED_SUCCESS",
        "executed_at": datetime.now(timezone.utc).isoformat(),
    }
