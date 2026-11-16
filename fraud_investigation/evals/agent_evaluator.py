
from fraud_investigation.agents.orchestrator import run_investigation
from fraud_investigation.evals.golden_dataset import GOLDEN_DATASET


def precision_recall_f1(expected, actual):
    """Set-based precision, recall and F1."""
    expected = set(expected)
    actual = set(actual)

    correct = len(expected & actual)

    precision = correct / len(actual) if actual else 0.0
    recall = correct / len(expected) if expected else 0.0

    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall > 0 else 0.0
    )

    return {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
    }

def reciprocal_rank(expected, actual):
    expected = set(expected)

    for rank, policy_id in enumerate(actual, start=1):
        if policy_id in expected:
            return round(1 / rank, 3)

    return 0.0


def evaluate_case(case):
    """Run the actual agent and evaluate its tool and retrieval choices."""

    result = run_investigation(
        case["customer_id"],
        case["alert_id"]
    )

    if "error" in result:
        return {
            "alert_id": case["alert_id"],
            "status": "ERROR",
            "error": result["error"],
        }

    # Extract actual tool calls from execution trace
    actual_tools = [
        event["details"]["tool"]
        for event in result["trace"]
        if event["event"] == "tool_requested"
    ]

    # Extract actual policies returned by agent-selected RAG
    actual_policies = [
        item["policy_id"]
        for item in result.get("retrieved_policies", [])
    ]

    rag_diagnostics = result.get("policy_diagnostics") or {}
    actual_query = rag_diagnostics.get("query", "No query generated")

    tool_metrics = precision_recall_f1(
        case["expected_tools"],
        actual_tools
    )

    policy_metrics = precision_recall_f1(
        case["expected_policy_ids"],
        actual_policies
    )

    return {
        "alert_id": case["alert_id"],
        "status": "COMPLETED",
        "actual_tools": actual_tools,
        "actual_policies": actual_policies,
        "tool_precision": tool_metrics["precision"],
        "tool_recall": tool_metrics["recall"],
        "tool_f1": tool_metrics["f1"],
        "policy_precision": policy_metrics["precision"],
        "policy_recall": policy_metrics["recall"],
        "policy_f1": policy_metrics["f1"],
        "rag_query": actual_query,
        "report": result["report"],
    }


def run_all_evaluations():
    return [
        evaluate_case(case)
        for case in GOLDEN_DATASET
    ]


if __name__ == "__main__":
    results = run_all_evaluations()

    for result in results:
        print(f"\nAlert: {result['alert_id']}")
        print(f"Status: {result['status']}")

        if result["status"] == "COMPLETED":
            print(f"Tools: {result['actual_tools']}")
            print(f"Policies: {result['actual_policies']}")
            print(f"RAG Query: {result['rag_query']}")
            print(f"Tool F1: {result['tool_f1']}")
            print(f"Policy Recall: {result['policy_recall']}")
        else:
            print(f"Error: {result['error']}")
