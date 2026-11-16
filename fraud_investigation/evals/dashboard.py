
import streamlit as st
import pandas as pd

from fraud_investigation.evals.eval_store import load_evaluations


def show_evaluation_dashboard():
    st.header("Agent Evaluation Dashboard")

    records = load_evaluations()

    if not records:
        st.info("No investigations recorded yet.")
        return

    rows = []

    for record in records:
        tool = record.get("tool_metrics") or {}
        policy = record.get("policy_metrics") or {}

        rows.append({
            "Run ID": record["run_id"],
            "Timestamp": record["timestamp"],
            "Alert": record["alert_id"],
            "Status": record["status"],
            "Tool F1": tool.get("f1"),
            "Policy Precision": policy.get("precision"),
            "Policy Recall": policy.get("recall"),
            "Policy RR": record.get("policy_mrr"),
            "Policy F1": policy.get("f1"),
        })

    df = pd.DataFrame(rows)
    evaluated = df[df["Policy Recall"].notna()]

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Investigations", len(df))
    col2.metric(
        "Average Tool F1",
        f"{df['Tool F1'].mean():.2%}"
        if df["Tool F1"].notna().any() else "N/A"
    )
    col3.metric(
        "Average Policy Recall",
        f"{evaluated['Policy Recall'].mean():.2%}"
        if not evaluated.empty else "N/A"
    )

    st.subheader("Investigation History")
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.subheader("Policy Retrieval Performance")

    mrr_values = df["Policy RR"].dropna()

    st.metric(
        "Mean Reciprocal Rank (MRR)",
        f"{mrr_values.mean():.2%}" if not mrr_values.empty else "N/A"
    )

    if not evaluated.empty:
        chart_df = evaluated.set_index("Run ID")[
            ["Policy Precision", "Policy Recall", "Policy F1"]
        ]
        st.line_chart(chart_df)

    st.subheader("Investigation Details")

    selected_run = st.selectbox(
        "Select investigation",
        options=[r["run_id"] for r in records]
    )

    selected = next(
        r for r in records if r["run_id"] == selected_run
    )

    st.write("**RAG Query:**", selected.get("rag_query"))
    st.write("**Tools Called:**", selected.get("actual_tools"))
    st.write("**Retrieved Policies:**", selected.get("actual_policies"))
    st.write("**Trace ID:**", selected.get("trace_id"))
