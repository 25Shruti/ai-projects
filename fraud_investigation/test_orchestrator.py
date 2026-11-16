from fraud_investigation.agents.orchestrator import run_investigation

result = run_investigation("C101", "AML-001")

print("REPORT:", result.get("report"))
print("TRACE:", result.get("trace"))
print("ERROR:", result.get("error"))