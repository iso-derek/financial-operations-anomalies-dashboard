"""Clean and feature-engineer the synthetic finance operations data."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = PROJECT_ROOT / "data" / "raw" / "finance_operations_raw.csv"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
CLEAN_PATH = PROCESSED_DIR / "clean_finance_operations.csv"


def risk_rule_score(row: pd.Series) -> int:
    score = 0
    score += int(row["high_value_flag"]) * 2
    score += int(row["high_vendor_risk_flag"]) * 2
    score += int(row["failed_payment_flag"]) * 2
    score += int(row["duplicate_invoice_flag"]) * 3
    score += int(row["urgent_payment_flag"])
    score += int(row["weekend_payment_flag"])
    score += int(row["approval_speed_flag"]) * 2
    if row["amount"] > 50_000 and row["approval_level"] <= 2:
        score += 2
    return score


def clean_finance_operations(raw_path: Path = RAW_PATH) -> pd.DataFrame:
    if not raw_path.exists():
        raise FileNotFoundError(
            f"Raw data not found at {raw_path}. Run `python src/generate_data.py` first."
        )

    df = pd.read_csv(raw_path)
    df = df.drop_duplicates(subset=["transaction_id"]).copy()

    date_cols = ["transaction_date", "invoice_date", "approval_date"]
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], errors="coerce")

    categorical_cols = [
        "vendor_id",
        "vendor_name",
        "department",
        "project_code",
        "currency",
        "payment_method",
        "payment_status",
        "country",
        "region",
        "expense_category",
        "approver_id",
    ]
    for col in categorical_cols:
        df[col] = df[col].fillna("Unknown")

    numeric_cols = [
        "amount",
        "approval_level",
        "account_age_days",
        "vendor_risk_score",
        "previous_failed_payments",
        "duplicate_invoice_flag",
        "urgent_payment_flag",
        "weekend_payment_flag",
        "days_to_approve",
        "is_anomaly",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        df[col] = df[col].fillna(df[col].median())

    for col in date_cols:
        df[col] = df[col].fillna(df[col].median())

    df["transaction_month"] = df["transaction_date"].dt.to_period("M").astype(str)
    df["transaction_day"] = df["transaction_date"].dt.day_name()
    df["transaction_hour"] = df["transaction_date"].dt.hour

    amount_std = df["amount"].std(ddof=0)
    df["amount_zscore"] = 0.0 if amount_std == 0 else (df["amount"] - df["amount"].mean()) / amount_std
    df["approval_delay_days"] = (df["approval_date"] - df["invoice_date"]).dt.days.clip(lower=0)
    df["failed_payment_flag"] = (df["payment_status"].str.lower() == "failed").astype(int)
    df["high_value_flag"] = (df["amount"] >= df["amount"].quantile(0.95)).astype(int)
    df["high_vendor_risk_flag"] = (df["vendor_risk_score"] >= 75).astype(int)
    df["approval_speed_flag"] = ((df["approval_delay_days"] <= 1) & (df["amount"] >= df["amount"].quantile(0.80))).astype(int)
    df["risk_rule_score"] = df.apply(risk_rule_score, axis=1)

    ordered_cols = [
        "transaction_id",
        "invoice_id",
        "vendor_id",
        "vendor_name",
        "department",
        "project_code",
        "transaction_date",
        "invoice_date",
        "approval_date",
        "amount",
        "currency",
        "payment_method",
        "payment_status",
        "country",
        "region",
        "expense_category",
        "approver_id",
        "approval_level",
        "account_age_days",
        "vendor_risk_score",
        "previous_failed_payments",
        "duplicate_invoice_flag",
        "urgent_payment_flag",
        "weekend_payment_flag",
        "days_to_approve",
        "is_anomaly",
        "transaction_month",
        "transaction_day",
        "transaction_hour",
        "amount_zscore",
        "approval_delay_days",
        "failed_payment_flag",
        "high_value_flag",
        "high_vendor_risk_flag",
        "approval_speed_flag",
        "risk_rule_score",
    ]
    return df[ordered_cols]


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df = clean_finance_operations()
    df.to_csv(CLEAN_PATH, index=False)
    print(f"Cleaned {len(df):,} transactions at {CLEAN_PATH}")


if __name__ == "__main__":
    main()
