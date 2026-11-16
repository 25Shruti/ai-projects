import streamlit as st
import pandas as pd

st.title("Intelligent Cost & Budget Analyst")

st.write("Upload your departmental budget data to get started.")

uploaded_file = st.file_uploader(
    "Upload your budget CSV",
    type=["csv"]
)

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    st.subheader("Uploaded Budget Data")
    st.dataframe(df)

    st.write("Dataset dimensions:", df.shape)

    # Calculate overall budget performance
    total_budget = df["Budget"].sum()
    total_actual = df["Actual"].sum()
    variance = total_actual - total_budget

    st.subheader("Budget Performance")

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Budget", f"₹{total_budget:,.0f}")
    col2.metric("Actual Spend", f"₹{total_actual:,.0f}")
    col3.metric(
        "Budget Variance",
        f"₹{variance:,.0f}",
        delta=f"{variance:,.0f}",
        delta_color="inverse"
    )

        # Department-wise budget analysis
    department_summary = df.groupby("Department")[
        ["Budget", "Actual"]
    ].sum().reset_index()

    department_summary["Variance"] = (
        department_summary["Actual"] - department_summary["Budget"]
    )

    st.subheader("Department-wise Budget Analysis")

    st.dataframe(department_summary)

        # Budget vs Actual chart
    st.subheader("Budget vs Actual by Department")

    chart_data = department_summary.set_index("Department")[
        ["Budget", "Actual"]
    ]

    st.bar_chart(chart_data)

        # Identify departments exceeding their budget
    st.subheader("Budget Alerts")

    overspending = department_summary[
        department_summary["Variance"] > 0
    ]

    if not overspending.empty:
        st.warning("The following departments are exceeding their budgets:")
        st.dataframe(overspending)
    else:
        st.success("All departments are within their allocated budgets.")

        # Generate business insights
    st.subheader("Business Insights")

    if not overspending.empty:
        for _, row in overspending.iterrows():
            overspend_pct = (
                row["Variance"] / row["Budget"]
            ) * 100

            st.write(
                f"⚠️ {row['Department']} is over budget by "
                f"₹{row['Variance']:,.0f} "
                f"({overspend_pct:.1f}%)."
            )
    else:
        st.success("No departments are exceeding their budgets.")
