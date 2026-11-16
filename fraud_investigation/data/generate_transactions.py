
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)
transactions = []

# Six months of historical activity
start_date = datetime(2026, 5, 1)

profiles = {
    "C101": {"count": 35, "min": 500, "max": 12000},
    "C102": {"count": 45, "min": 10000, "max": 180000},
    "C103": {"count": 25, "min": 2000, "max": 85000},
}

for customer_id, profile in profiles.items():
    for month in range(6):
        month_start = datetime(2026, 5 + month, 1)

        for i in range(profile["count"]):
            date = month_start + timedelta(
                days=random.randint(0, 27),
                hours=random.randint(8, 20)
            )

            direction = random.choice(["credit", "debit"])
            amount = random.randint(profile["min"], profile["max"])

            transactions.append({
                "transaction_id": f"H{customer_id}{month:02d}{i:03d}",
                "customer_id": customer_id,
                "timestamp": date.strftime("%Y-%m-%d %H:%M:%S"),
                "amount_inr": amount,
                "direction": direction,
                "counterparty_id": "CP_EXISTING",
                "country": "IN",
                "channel": "Bank Transfer"
            })

# Alert-triggering transactions
alert_transactions = [
    # AML-001: Rapid movement of funds
    ("T101", "C101", "2026-11-10 09:00:00", 950000, "credit", "CP_NEW1", "IN"),
    ("T102", "C101", "2026-11-10 11:30:00", 800000, "debit", "CP_FOREIGN1", "AE"),

    # AML-002: Legitimate international business payment
    ("T201", "C102", "2026-11-11 09:30:00", 1200000, "debit", "CP_SUPPLIER", "SG"),

    # AML-003: Ambiguous activity
    ("T301", "C103", "2026-11-12 10:00:00", 600000, "credit", "CP_NEW2", "IN"),
    ("T302", "C103", "2026-11-12 11:15:00", 250000, "debit", "CP_UNKNOWN1", "IN"),
    ("T303", "C103", "2026-11-12 14:20:00", 200000, "debit", "CP_UNKNOWN2", "IN"),
]

for tid, cid, timestamp, amount, direction, cp, country in alert_transactions:
    transactions.append({
        "transaction_id": tid,
        "customer_id": cid,
        "timestamp": timestamp,
        "amount_inr": amount,
        "direction": direction,
        "counterparty_id": cp,
        "country": country,
        "channel": "Bank Transfer"
    })

# Save CSV
output_path = Path(__file__).parent / "transactions.csv"

with open(output_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=transactions[0].keys())
    writer.writeheader()
    writer.writerows(transactions)

print(f"Generated {len(transactions)} transactions")
print(f"Saved to: {output_path}")
