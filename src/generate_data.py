"""Generate a synthetic finance operations dataset.

The data is synthetic and designed for portfolio/demo use only. It contains
normal finance operations activity plus planted anomaly patterns that mirror
common audit and risk review scenarios.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
RAW_PATH = RAW_DIR / "finance_operations_raw.csv"

RANDOM_SEED = 42
N_ROWS = 25_000
ANOMALY_RATE = 0.065


def _random_dates(rng: np.random.Generator, n_rows: int) -> pd.Series:
    start = datetime(2024, 1, 1)
    end = datetime(2026, 5, 31)
    span_days = (end - start).days
    day_offsets = rng.integers(0, span_days + 1, size=n_rows)
    hour_offsets = rng.integers(8, 19, size=n_rows)
    minute_offsets = rng.integers(0, 60, size=n_rows)
    return pd.Series(
        [
            start + timedelta(days=int(d), hours=int(h), minutes=int(m))
            for d, h, m in zip(day_offsets, hour_offsets, minute_offsets)
        ]
    )


def generate_finance_operations(n_rows: int = N_ROWS) -> pd.DataFrame:
    rng = np.random.default_rng(RANDOM_SEED)

    departments = [
        "Finance",
        "Procurement",
        "IT",
        "Operations",
        "Marketing",
        "Legal",
        "Facilities",
        "Human Resources",
        "Sales",
        "Customer Support",
    ]
    categories = [
        "Software",
        "Professional Services",
        "Travel",
        "Office Supplies",
        "Facilities",
        "Contractors",
        "Media Rights",
        "Cloud Infrastructure",
        "Training",
        "Logistics",
    ]
    countries = {
        "United Kingdom": "EMEA",
        "United States": "Americas",
        "Canada": "Americas",
        "Germany": "EMEA",
        "France": "EMEA",
        "Nigeria": "EMEA",
        "India": "APAC",
        "Singapore": "APAC",
        "Australia": "APAC",
        "Brazil": "Americas",
    }
    payment_methods = ["Bank Transfer", "Card", "Wire", "ACH", "Cheque"]
    statuses = ["Paid", "Paid", "Paid", "Paid", "Pending", "Failed", "Cancelled"]

    vendor_count = 950
    vendor_ids = [f"V{idx:05d}" for idx in range(1, vendor_count + 1)]
    vendor_names = [
        f"{prefix} {suffix}"
        for prefix, suffix in zip(
            rng.choice(
                [
                    "Northstar",
                    "Pinnacle",
                    "Apex",
                    "Vertex",
                    "Bluewave",
                    "Cobalt",
                    "Sterling",
                    "NexGen",
                    "Meridian",
                    "Summit",
                ],
                size=vendor_count,
            ),
            rng.choice(
                [
                    "Analytics",
                    "Consulting",
                    "Supplies",
                    "Media",
                    "Systems",
                    "Logistics",
                    "Partners",
                    "Services",
                ],
                size=vendor_count,
            ),
        )
    ]
    vendor_base_risk = np.clip(rng.beta(2.0, 6.0, vendor_count) * 100, 1, 98)
    vendor_lookup = pd.DataFrame(
        {
            "vendor_id": vendor_ids,
            "vendor_name": vendor_names,
            "vendor_base_risk": vendor_base_risk,
        }
    )

    transaction_dates = _random_dates(rng, n_rows)
    invoice_lag = rng.integers(0, 25, size=n_rows)
    approval_lag = rng.integers(1, 18, size=n_rows)
    invoice_dates = transaction_dates - pd.to_timedelta(invoice_lag, unit="D")
    approval_dates = invoice_dates + pd.to_timedelta(approval_lag, unit="D")

    selected_vendors = vendor_lookup.iloc[rng.integers(0, vendor_count, size=n_rows)].reset_index(drop=True)
    selected_countries = rng.choice(list(countries.keys()), size=n_rows)

    base_amount = rng.lognormal(mean=7.45, sigma=0.85, size=n_rows)
    amount = np.clip(base_amount, 30, 85_000).round(2)

    df = pd.DataFrame(
        {
            "transaction_id": [f"TXN{idx:08d}" for idx in range(1, n_rows + 1)],
            "invoice_id": [f"INV{idx:08d}" for idx in range(1, n_rows + 1)],
            "vendor_id": selected_vendors["vendor_id"],
            "vendor_name": selected_vendors["vendor_name"],
            "department": rng.choice(departments, size=n_rows),
            "project_code": [f"PRJ-{rng.integers(100, 999)}" for _ in range(n_rows)],
            "transaction_date": transaction_dates,
            "invoice_date": invoice_dates,
            "approval_date": approval_dates,
            "amount": amount,
            "currency": rng.choice(["GBP", "USD", "EUR", "NGN", "INR"], size=n_rows, p=[0.35, 0.28, 0.2, 0.1, 0.07]),
            "payment_method": rng.choice(payment_methods, size=n_rows, p=[0.46, 0.18, 0.16, 0.15, 0.05]),
            "payment_status": rng.choice(statuses, size=n_rows, p=[0.74, 0.06, 0.04, 0.03, 0.07, 0.045, 0.015]),
            "country": selected_countries,
            "region": [countries[country] for country in selected_countries],
            "expense_category": rng.choice(categories, size=n_rows),
            "approver_id": [f"APR{rng.integers(1, 220):04d}" for _ in range(n_rows)],
            "approval_level": rng.choice([1, 2, 3, 4], size=n_rows, p=[0.42, 0.34, 0.18, 0.06]),
            "account_age_days": rng.integers(30, 3650, size=n_rows),
            "vendor_risk_score": np.clip(selected_vendors["vendor_base_risk"] + rng.normal(0, 8, size=n_rows), 1, 100).round(1),
            "previous_failed_payments": rng.poisson(0.25, size=n_rows),
            "duplicate_invoice_flag": rng.choice([0, 1], size=n_rows, p=[0.985, 0.015]),
            "urgent_payment_flag": rng.choice([0, 1], size=n_rows, p=[0.92, 0.08]),
        }
    )

    df["weekend_payment_flag"] = df["transaction_date"].dt.dayofweek.isin([5, 6]).astype(int)
    df["days_to_approve"] = (df["approval_date"] - df["invoice_date"]).dt.days
    df["is_anomaly"] = 0

    anomaly_count = int(n_rows * ANOMALY_RATE)
    anomaly_indices = rng.choice(df.index, size=anomaly_count, replace=False)
    anomaly_types = rng.choice(
        [
            "high_payment",
            "duplicate_invoice",
            "failed_payments",
            "high_risk_vendor",
            "urgent_high_amount",
            "weekend_payment",
            "fast_approval",
            "suspicious_combo",
        ],
        size=anomaly_count,
    )

    for idx, anomaly_type in zip(anomaly_indices, anomaly_types):
        df.loc[idx, "is_anomaly"] = 1
        if anomaly_type == "high_payment":
            df.loc[idx, "amount"] = round(float(rng.uniform(90_000, 375_000)), 2)
            df.loc[idx, "approval_level"] = int(rng.choice([1, 2], p=[0.65, 0.35]))
        elif anomaly_type == "duplicate_invoice":
            source_idx = int(rng.integers(0, n_rows))
            df.loc[idx, "invoice_id"] = df.loc[source_idx, "invoice_id"]
            df.loc[idx, "vendor_id"] = df.loc[source_idx, "vendor_id"]
            df.loc[idx, "vendor_name"] = df.loc[source_idx, "vendor_name"]
            df.loc[idx, "amount"] = df.loc[source_idx, "amount"]
            df.loc[idx, "duplicate_invoice_flag"] = 1
        elif anomaly_type == "failed_payments":
            df.loc[idx, "payment_status"] = "Failed"
            df.loc[idx, "previous_failed_payments"] = int(rng.integers(3, 9))
        elif anomaly_type == "high_risk_vendor":
            df.loc[idx, "vendor_risk_score"] = round(float(rng.uniform(82, 99)), 1)
            df.loc[idx, "account_age_days"] = int(rng.integers(10, 180))
        elif anomaly_type == "urgent_high_amount":
            df.loc[idx, "urgent_payment_flag"] = 1
            df.loc[idx, "amount"] = round(float(rng.uniform(55_000, 250_000)), 2)
            df.loc[idx, "vendor_risk_score"] = round(float(rng.uniform(65, 98)), 1)
        elif anomaly_type == "weekend_payment":
            df.loc[idx, "weekend_payment_flag"] = 1
            base_date = pd.Timestamp(df.loc[idx, "transaction_date"])
            days_until_sat = (5 - base_date.dayofweek) % 7
            df.loc[idx, "transaction_date"] = base_date + pd.Timedelta(days=int(days_until_sat))
            df.loc[idx, "vendor_risk_score"] = round(float(rng.uniform(60, 95)), 1)
        elif anomaly_type == "fast_approval":
            df.loc[idx, "amount"] = round(float(rng.uniform(40_000, 180_000)), 2)
            df.loc[idx, "approval_date"] = df.loc[idx, "invoice_date"]
            df.loc[idx, "days_to_approve"] = 0
        elif anomaly_type == "suspicious_combo":
            df.loc[idx, "amount"] = round(float(rng.uniform(70_000, 300_000)), 2)
            df.loc[idx, "vendor_risk_score"] = round(float(rng.uniform(80, 100)), 1)
            df.loc[idx, "approval_level"] = int(rng.choice([1, 2]))
            df.loc[idx, "urgent_payment_flag"] = 1
            df.loc[idx, "previous_failed_payments"] = int(rng.integers(2, 7))

    for col in ["transaction_date", "invoice_date", "approval_date"]:
        df[col] = pd.to_datetime(df[col]).dt.strftime("%Y-%m-%d %H:%M:%S")

    return df


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    df = generate_finance_operations()
    df.to_csv(RAW_PATH, index=False)
    print(f"Generated {len(df):,} synthetic transactions at {RAW_PATH}")
    print(f"Anomaly rate: {df['is_anomaly'].mean():.2%}")


if __name__ == "__main__":
    main()
