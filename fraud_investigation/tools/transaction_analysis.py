
from pathlib import Path
import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def analyze_transactions(customer_id: str, alert_id: str) -> dict:
    """Analyse historical behaviour and alert-triggering transactions."""

    transactions = pd.read_csv(
        DATA_DIR / "transactions.csv",
        parse_dates=["timestamp"],
        date_format="%d-%m-%Y %H:%M"
    )
    alerts = pd.read_csv(DATA_DIR / "alerts.csv")

    # Find the selected alert
    alert_rows = alerts[
        (alerts["alert_id"] == alert_id)
        & (alerts["customer_id"] == customer_id)
    ]

    if alert_rows.empty:
        return {"error": "Alert not found for this customer."}

    alert = alert_rows.iloc[0]
    trigger_ids = str(alert["trigger_transaction_ids"]).split("|")

    # Historical transactions only (May–October 2026)
    history = transactions[
        (transactions["customer_id"] == customer_id)
        & (transactions["timestamp"] < "2026-11-01")
    ].copy()

    # Calculate monthly credits and debits
    history["month"] = history["timestamp"].dt.to_period("M")

    monthly = history.pivot_table(
        index="month",
        columns="direction",
        values="amount_inr",
        aggfunc="sum",
        fill_value=0
    )

    monthly_credit = monthly.get("credit", pd.Series(dtype=float))
    monthly_debit = monthly.get("debit", pd.Series(dtype=float))

    avg_credit = float(monthly_credit.mean())
    avg_debit = float(monthly_debit.mean())

    median_credit = float(monthly_credit.median())
    median_debit = float(monthly_debit.median())


    # Retrieve alert-triggering transactions
    triggered = transactions[
        (transactions["customer_id"] == customer_id)
        & (transactions["transaction_id"].isin(trigger_ids))
    ].copy()

    if len(triggered) != len(trigger_ids):
        return {"error": "Some triggering transactions were not found."}

    total_credit = float(
        triggered.loc[
            triggered["direction"] == "credit", "amount_inr"
        ].sum()
    )

    total_debit = float(
        triggered.loc[
            triggered["direction"] == "debit", "amount_inr"
        ].sum()
    )

    credit_ratio = (
        round(total_credit / avg_credit, 2)
        if avg_credit > 0 else None
    )

    debit_ratio = (
        round(total_debit / avg_debit, 2)
        if avg_debit > 0 else None
    )


    # AML Spcific Condition: 1. Identify new counterparties
    historical_counterparties = set(history["counterparty_id"].dropna())

    new_counterparties = [
        cp for cp in triggered["counterparty_id"].dropna().unique()
        if cp not in historical_counterparties
    ]

    # AML Spcific Condition:2. Identify international transfers
    international_transfers = triggered[
        (triggered["direction"] == "debit")
        & (triggered["country"] != "IN")
    ]

    # AML Spcific Condition: 3. Detect rapid movement of funds
    credits = triggered[triggered["direction"] == "credit"]
    debits = triggered[triggered["direction"] == "debit"]

    rapid_movements = []

    for _, credit in credits.iterrows():
        subsequent_debits = debits[
            (debits["timestamp"] > credit["timestamp"])
            & (
                debits["timestamp"]
                <= credit["timestamp"] + pd.Timedelta(hours=24)
            )
        ]

        if not subsequent_debits.empty:
            outgoing = float(subsequent_debits["amount_inr"].sum())
            percentage = round(outgoing / credit["amount_inr"] * 100, 2)

            rapid_movements.append({
                "incoming_transaction": credit["transaction_id"],
                "outgoing_transactions": subsequent_debits[
                    "transaction_id"
                ].tolist(),
                "hours_to_first_transfer": round(
                    (
                        subsequent_debits["timestamp"].min()
                        - credit["timestamp"]
                    ).total_seconds() / 3600,
                    2
                ),
                "funds_transferred_percentage": percentage
            })


    return {
        "alert_id": alert_id,
        
        "customer_id": customer_id,
        "historical_avg_monthly_credit": round(avg_credit, 2),
        "historical_avg_monthly_debit": round(avg_debit, 2),
        "historical_median_monthly_credit": round(median_credit, 2),
        "historical_median_monthly_debit": round(median_debit, 2),
        "alert_total_credit": total_credit,
        "alert_total_debit": total_debit,
        "credit_to_monthly_average_ratio": credit_ratio,
        "debit_to_monthly_average_ratio": debit_ratio,
        "credit_to_median_ratio": round(total_credit / median_credit, 2) if median_credit > 0 else None,
        "debit_to_median_ratio": round(total_debit / median_debit, 2) if median_debit > 0 else None,
        "new_counterparties": new_counterparties,
        "international_transfer_count": len(international_transfers),
        "rapid_fund_movements": rapid_movements,
        "triggering_transactions": triggered[
            [
                "transaction_id",
                "timestamp",
                "amount_inr",
                "direction",
                "counterparty_id",
                "country"
            ]
        ].assign(
            timestamp=lambda df: df["timestamp"].astype(str)
        ).to_dict(orient="records")
    }
