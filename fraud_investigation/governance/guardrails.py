
import re


def validate_investigation(customer_id: str, alert_id: str) -> dict:
    """Validate investigation identifiers before invoking the agent."""

    if not isinstance(customer_id, str) or not re.fullmatch(r"C\d{3,8}", customer_id):
        return {"error": "Invalid customer ID"}

    if not isinstance(alert_id, str) or not re.fullmatch(r"AML-\d{3,8}", alert_id):
        return {"error": "Invalid alert ID"}

    return {"valid": True}


def validate_policy_search(query: str, top_k: int) -> dict:
    """Validate RAG tool arguments."""

    if not isinstance(query, str) or not query.strip():
        return {"error": "Policy search query cannot be empty"}

    if len(query) > 500:
        return {"error": "Policy search query exceeds 500 characters"}

    if type(top_k) is not int or not 1 <= top_k <= 6:
        return {"error": "top_k must be an integer between 1 and 6"}

    return {"valid": True}


def redact_pii(text: str) -> str:
    """Mask common sensitive identifiers in log text."""

    if not isinstance(text, str):
        return text

    text = re.sub(
        r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b",
        "[REDACTED_EMAIL]",
        text
    )

    text = re.sub(
        r"\b(?:\+91[\s-]?)?[6-9]\d{9}\b",
        "[REDACTED_PHONE]",
        text
    )

    return text


def sanitize_trace(value):
    """Recursively redact PII in trace dictionaries and lists."""

    if isinstance(value, dict):
        return {
            key: sanitize_trace(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [sanitize_trace(item) for item in value]

    if isinstance(value, str):
        return redact_pii(value)

    return value
