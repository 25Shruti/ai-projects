
import json
import time
from datetime import datetime, timezone


# Only synthetic customer records are available in this prototype.
CUSTOMER_DATA = {
    "C101": [
        {"id": "T001", "amount": 1500, "type": "debit",
         "merchant": "Grocery Store"},
        {"id": "T002", "amount": 25000, "type": "debit",
         "merchant": "Electronics Store"},
        {"id": "T003", "amount": 95000, "type": "credit",
         "merchant": "Unknown Account"},
        {"id": "T004", "amount": 48000, "type": "debit",
         "merchant": "International Transfer"},
        {"id": "T005", "amount": 2200, "type": "debit",
         "merchant": "Restaurant"}
    ], 

    "C102": [
        {"id": "T001", "amount": 1500, "type": "debit",
         "merchant": "Grocery Store"},
        {"id": "T002", "amount": 25000, "type": "debit",
         "merchant": "Electronics Store"},
        {"id": "T003", "amount": 95000, "type": "credit",
         "merchant": "Unknown Account"},
        {"id": "T004", "amount": 48000, "type": "debit",
         "merchant": "International Transfer"},
        {"id": "T005", "amount": 2200, "type": "debit",
         "merchant": "Restaurant"}
    ]
}


def get_customer_transactions(customer_id: str, days: int = 7) -> dict:
    """Retrieve synthetic customer transactions for investigation."""

    start_time = time.perf_counter()

    # TRACE 1: Record what the LLM requested
    print("\n========== EXECUTION TRACE ==========")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print("Tool requested: get_customer_transactions")
    print(f"Arguments: customer_id={customer_id}, days={days}")

    # GUARDRAIL 1: Validate customer ID
    if not isinstance(customer_id, str) or customer_id not in CUSTOMER_DATA:
        result = {
            "status": "rejected",
            "error": "Customer ID is invalid or not authorised."
        }
        print("Validation: FAILED - Invalid customer ID")
        print("Tool execution: BLOCKED")
        return result

    # GUARDRAIL 2: Validate transaction period
    if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= 30:
        result = {
            "status": "rejected",
            "error": "Transaction period must be an integer between 1 and 30 days."
        }
        print("Validation: FAILED - Invalid transaction period")
        print("Tool execution: BLOCKED")
        return result

    print("Validation: PASSED")
    print("Tool execution: APPROVED")

    # Execute the approved tool
    transactions = CUSTOMER_DATA[customer_id]

    result = {
        "status": "success",
        "customer_id": customer_id,
        "period_days": days,
        "transactions": transactions
    }

    duration = round(time.perf_counter() - start_time, 4)

    # TRACE 2: Record what the tool returned
    print(f"Tool result: {json.dumps(result, indent=2)}")
    print(f"Execution duration: {duration} seconds")
    print("====================================\n")

    return result
