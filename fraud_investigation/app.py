
import sys
from pathlib import Path

import pandas as pd
import streamlit as st 

from fraud_investigation.governance.approval import (
    request_approval,
    decide_approval,
    execute_approved_action,
)

from fraud_investigation.evals.llm_judge import evaluate_investigation
from fraud_investigation.evals.eval_store import (
    save_judge_result,
    load_judge_result,
)

from fraud_investigation.agents.orchestrator import run_investigation
from fraud_investigation.rag.policy_retriever import search_aml_policy
from fraud_investigation.evals.record_evaluation import record_investigation
from fraud_investigation.evals.dashboard import show_evaluation_dashboard
from fraud_investigation.observability.telemetry import configure_telemetry


configure_telemetry()

# Allow imports from the project root
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fraud_investigation.tools.transaction_analysis import analyze_transactions

DATA_DIR = Path(__file__).resolve().parent / "data"

st.set_page_config(
    page_title="AML Investigation Copilot",
    page_icon="🔎",
    layout="wide"
)

st.title("🔎 AML Investigation Copilot")
st.caption("AI-assisted investigation | Synthetic demonstration data")

alerts = pd.read_csv(DATA_DIR / "alerts.csv")
customers = pd.read_csv(DATA_DIR / "customers.csv")

# Alert selection
alert_id = st.selectbox("Select AML Alert", alerts["alert_id"].tolist())

alert = alerts[alerts["alert_id"] == alert_id].iloc[0]
customer_id = alert["customer_id"]
customer = customers[customers["customer_id"] == customer_id].iloc[0]

st.subheader("Alert & Customer Details")

col1, col2, col3 = st.columns(3)
col1.metric("Alert Severity", alert["alert_severity"])
col2.metric("Customer", customer["customer_name"])
col3.metric("KYC Risk Rating", customer["kyc_risk_rating"])

st.write("**Alert description:**", alert["alert_description"])
st.write("**Customer type:**", customer["customer_type"])
st.write("**Occupation:**", customer["occupation"])

if st.button("🔍 Investigate Alert", type="primary"):
    # Clear previous approval and execution for this alert
    st.session_state.pop(f"approval_{alert_id}", None)
    st.session_state.pop(f"execution_{alert_id}", None)

    with st.spinner("Investigating alert..."):
        agent_result = run_investigation(customer_id, alert_id)

        st.session_state["latest_investigation"] = agent_result
        st.session_state["latest_alert_id"] = alert_id

        evaluation_record = record_investigation(customer_id, alert_id, agent_result)
        st.session_state["latest_run_id"] = evaluation_record["run_id"]


    if "error" in agent_result:
        st.error(agent_result["error"])

        with st.expander("🔍 Error Diagnostics", expanded=True):
            st.json(agent_result.get("trace", []))
    else:
        st.session_state["investigation"] = agent_result["analysis"]
        st.session_state["ai_report"] = agent_result["report"]
        st.session_state["execution_trace"] = agent_result["trace"]
        st.session_state["investigated_alert_id"] = alert_id
        st.session_state["report_alert_id"] = alert_id
        st.session_state["policy_diagnostics"] = agent_result.get(
                "policy_diagnostics"
            )

# Only show results for the currently selected alert
if st.session_state.get("investigated_alert_id") == alert_id:
    result = st.session_state["investigation"]

    if "error" in result:
        st.error(result["error"])
    else:
        st.divider()
        st.subheader("Transaction Behaviour Analysis")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric(
            "Avg Monthly Credit",
            f"₹{result['historical_avg_monthly_credit']:,.0f}"
        )
        c2.metric(
            "Alert Credit",
            f"₹{result['alert_total_credit']:,.0f}"
        )
        c3.metric(
            "Avg Monthly Debit",
            f"₹{result['historical_avg_monthly_debit']:,.0f}"
        )
        c4.metric(
            "Alert Debit",
            f"₹{result['alert_total_debit']:,.0f}"
        )

        st.subheader("Behavioural Indicators")

        st.write(
            "**Credit / Historical Median:**",
            result["credit_to_median_ratio"]
        )
        st.write(
            "**Debit / Historical Median:**",
            result["debit_to_median_ratio"]
        )
        st.write(
            "**New Counterparties:**",
            result.get("new_counterparties", [])
        )
        st.write(
            "**International Transfers:**",
            result.get("international_transfer_count", 0)
        )

        st.subheader("Rapid Fund Movements")
        movements = result.get("rapid_fund_movements", [])

        if movements:
            st.dataframe(pd.DataFrame(movements), use_container_width=True)
        else:
            st.info("No rapid fund movements detected.")

        st.subheader("Alert-Triggering Transactions")
        st.dataframe(
            pd.DataFrame(result["triggering_transactions"]),
            use_container_width=True
        )

        st.divider()
        st.subheader("AML Policy Retreival")

        policy_results = st.session_state.get("policy_diagnostics")

        
        if policy_results:
            for search_type, heading in [
                ("investigation_search", "Investigation Policy Search"),
                ("disposition_search", "Disposition Policy Search")
            ]:
                search = policy_results[search_type]

                st.markdown(f"### {heading}")
                st.caption(f"Search query: {search['query']}")

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.markdown("**BM25 Keyword Search**")
                    st.dataframe(
                        pd.DataFrame(search["bm25_ranking"]),
                        hide_index=True,
                        use_container_width=True
                    )

                with col2:
                    st.markdown("**ChromaDB Semantic Search**")
                    st.dataframe(
                        pd.DataFrame(search["semantic_ranking"]),
                        hide_index=True,
                        use_container_width=True
                    )

                with col3:
                    st.markdown("**Final RRF Ranking**")
                    st.dataframe(
                        pd.DataFrame(search["rrf_ranking"]),
                        hide_index=True,
                        use_container_width=True
                    )

            st.markdown("**Combined Retrieved AML Policy Evidence**")

            for policy in policy_results["results"]:
                with st.expander(
                    f"{policy['policy_id']} | RRF: {policy['rrf_score']:.5f}"
                ):
                    st.markdown(policy["content"])

        else:
            st.info("No AML policies retrieved for this investigation.")


        st.divider()
        st.subheader("AI Investigation Assessment")
        st.markdown(st.session_state["ai_report"])

        st.divider()
        st.subheader("Human-in-the-Loop Approval")

        st.caption(
            "Sensitive actions require explicit analyst approval. "
            "All actions are simulated."
        )

        analyst = st.text_input(
            "Analyst ID",
            value="analyst_demo",
            key=f"analyst_{alert_id}"
        )

        recommended_action = st.session_state["latest_investigation"].get("recommended_action")

        st.write(
            "**Agent Recommended Action:**",
            recommended_action or "No valid recommendation generated"
        )

        action = recommended_action
        if action == "escalate_case":
            st.info("Agent recommends escalation. Human approval is required.")
        elif action == "request_information":
            st.info("Agent recommends requesting additional information.")
        elif action == "close_alert":
            st.info("Agent recommends closure, subject to human review.")
        else:
            st.error("No valid agent action available.")


        if recommended_action is None:
            st.warning(
                "Agent recommendation unavailable or invalid. "
                "Do not treat the selected action as an agent recommendation."
            )

        approval_key = f"approval_{alert_id}"
        execution_key = f"execution_{alert_id}"

        if st.button("Request Approval", key=f"request_{alert_id}", disabled=(action not in { "escalate_case", "request_information", "close_alert"})):
            st.session_state[approval_key] = request_approval(
                alert_id, customer_id, action
            )
            st.session_state.pop(execution_key, None)

        approval = st.session_state.get(approval_key)

        if approval:
            st.write("**Approval Status:**", approval["status"])
            st.write("**Requested Action:**", approval["action"])

            if approval["status"] == "PENDING":
                c1, c2, c3 = st.columns(3)

                with c1:
                    if st.button("Approve", key=f"approve_{alert_id}"):
                        st.session_state[approval_key] = decide_approval(
                            approval, "APPROVED", analyst
                        )
                        st.rerun()

                with c2:
                    if st.button("Reject", key=f"reject_{alert_id}"):
                        st.session_state[approval_key] = decide_approval(
                            approval, "REJECTED", analyst
                        )
                        st.rerun()

                with c3:
                    if st.button(
                        "Request Further Review",
                        key=f"review_{alert_id}"
                    ):
                        st.session_state[approval_key] = decide_approval(
                            approval, "FURTHER_REVIEW", analyst
                        )
                        st.rerun()

            if st.button(
                "Record Approved Decision / Execute Simulation",
                key=f"execute_{alert_id}",
                disabled=(approval.get("status") != "APPROVED")
            ):
                st.session_state[execution_key] = (
                    execute_approved_action(approval)
                )

            if execution_key in st.session_state:
                execution = st.session_state[execution_key]

                if "error" in execution:
                    st.error(execution["error"])
                else:
                    st.success(
                        f"Simulated action completed: {execution['action']}"
                    )

            with st.expander("Approval Audit Record"):
                st.json(st.session_state[approval_key])

        with st.expander("🔍 Execution Trace"):
            st.json(st.session_state["execution_trace"])


with st.expander("Agent Evaluation Dashboard", expanded=False):
    show_evaluation_dashboard()



st.divider()
st.subheader("LLM-as-a-Judge Evaluation")

result = st.session_state.get("latest_investigation")
run_id = st.session_state.get("latest_run_id")

if result and run_id and "error" not in result:
    st.caption(f"Investigation Run ID: {run_id}")

    saved_judgement = load_judge_result(run_id)

    if saved_judgement is None:
        if st.button("Run LLM Judge", key=f"judge_{run_id}"):
            with st.spinner("Evaluating investigation quality..."):
                try:
                    judgement = evaluate_investigation(
                        report=result["report"],
                        analysis=result["analysis"],
                        policies=result["retrieved_policies"],
                    )

                    save_judge_result(run_id, judgement)
                    st.success("Evaluation completed and saved.")
                    st.rerun()

                except Exception as exc:
                    st.error(f"Judge evaluation failed: {exc}")

    else:
        col1, col2 = st.columns(2)

        col1.metric(
            "Groundedness",
            f"{saved_judgement['groundedness_score']:.1%}"
        )
        col2.metric(
            "Decision Quality",
            f"{saved_judgement['decision_quality_score']:.1%}"
        )

        st.write(
            "**Recommended Decision:**",
            saved_judgement["recommended_decision"]
        )
        st.write(
            "**Decision Assessment:**",
            saved_judgement["decision_explanation"]
        )

        with st.expander("Claim-Level Evaluation"):
            st.dataframe(
                saved_judgement["claims"],
                use_container_width=True,
                hide_index=True,
            )

else:
    st.info("Run an investigation to enable LLM-as-a-Judge.")
