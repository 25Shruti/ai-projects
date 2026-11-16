
from fraud_investigation.evals.golden_dataset import GOLDEN_DATASET
from fraud_investigation.evals.agent_evaluator import precision_recall_f1
from fraud_investigation.evals.eval_store import save_evaluation

from fraud_investigation.evals.agent_evaluator import (
    precision_recall_f1,
    reciprocal_rank,
)

def record_investigation(customer_id, alert_id, result):
    case = next(
        (
            c for c in GOLDEN_DATASET
            if c["alert_id"] == alert_id
            and c["customer_id"] == customer_id
        ),
        None,
    )

    trace = result.get("trace", [])

    actual_tools = [
        e["details"]["tool"]
        for e in trace
        if e["event"] == "tool_requested"
    ]

    actual_policies = list(dict.fromkeys(
        p["policy_id"]
        for p in result.get("retrieved_policies", [])
    ))

    diagnostics = result.get("policy_diagnostics") or {}

    record = {
        "alert_id": alert_id,
        "customer_id": customer_id,
        "trace_id": result.get("trace_id"),
        "status": "ERROR" if "error" in result else "COMPLETED",
        "error": result.get("error"),
        "actual_tools": actual_tools,
        "actual_policies": actual_policies,
        "rag_query": diagnostics.get("query"),
        "tool_metrics": None,
        "policy_metrics": None,
    }

    if case and "error" not in result:
        record["tool_metrics"] = precision_recall_f1(
            case["expected_tools"], actual_tools
        )
        record["policy_metrics"] = precision_recall_f1(
            case["expected_policy_ids"], actual_policies
        )
        record["policy_mrr"] = reciprocal_rank(
            case["expected_policy_ids"], actual_policies
        )

    run_id = save_evaluation(record)
    record["run_id"] = run_id
    return record
