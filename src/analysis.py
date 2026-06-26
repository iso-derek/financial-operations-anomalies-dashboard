"""Business analysis helpers for the finance anomaly dashboard."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCORED_PATH = PROJECT_ROOT / "data" / "processed" / "scored_finance_operations.csv"


def load_scored_data(path: Path = SCORED_PATH) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Scored data not found at {path}. Run `python src/train_model.py` first."
        )
    df = pd.read_csv(path)
    for col in ["transaction_date", "invoice_date", "approval_date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def total_transactions(df: pd.DataFrame) -> int:
    return int(len(df))


def total_spend(df: pd.DataFrame) -> float:
    return float(df["amount"].sum())


def average_transaction_value(df: pd.DataFrame) -> float:
    return float(df["amount"].mean()) if len(df) else 0.0


def anomaly_rate(df: pd.DataFrame) -> float:
    col = "model_prediction" if "model_prediction" in df.columns else "is_anomaly"
    return float(df[col].mean()) if len(df) else 0.0


def failed_payment_rate(df: pd.DataFrame) -> float:
    return float(df["failed_payment_flag"].mean()) if len(df) else 0.0


def duplicate_invoice_rate(df: pd.DataFrame) -> float:
    return float(df["duplicate_invoice_flag"].mean()) if len(df) else 0.0


def urgent_payment_rate(df: pd.DataFrame) -> float:
    return float(df["urgent_payment_flag"].mean()) if len(df) else 0.0


def weekend_payment_rate(df: pd.DataFrame) -> float:
    return float(df["weekend_payment_flag"].mean()) if len(df) else 0.0


def top_high_risk_vendors(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    return (
        df.groupby(["vendor_id", "vendor_name"], as_index=False)
        .agg(
            total_spend=("amount", "sum"),
            avg_vendor_risk=("vendor_risk_score", "mean"),
            anomaly_count=("model_prediction", "sum"),
            transaction_count=("transaction_id", "count"),
        )
        .sort_values(["avg_vendor_risk", "anomaly_count", "total_spend"], ascending=[False, False, False])
        .head(n)
    )


def top_anomalous_departments(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("department", as_index=False)
        .agg(anomaly_count=("model_prediction", "sum"), transactions=("transaction_id", "count"), spend=("amount", "sum"))
        .assign(anomaly_rate=lambda x: x["anomaly_count"] / x["transactions"])
        .sort_values("anomaly_count", ascending=False)
    )


def department_spend_summary(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("department", as_index=False)
        .agg(total_spend=("amount", "sum"), avg_transaction=("amount", "mean"), transactions=("transaction_id", "count"))
        .sort_values("total_spend", ascending=False)
    )


def vendor_risk_summary(df: pd.DataFrame) -> pd.DataFrame:
    bins = [0, 40, 70, 100]
    labels = ["Low", "Medium", "High"]
    temp = df.copy()
    temp["vendor_risk_band"] = pd.cut(temp["vendor_risk_score"], bins=bins, labels=labels, include_lowest=True)
    return (
        temp.groupby("vendor_risk_band", observed=False, as_index=False)
        .agg(transactions=("transaction_id", "count"), total_spend=("amount", "sum"), anomaly_count=("model_prediction", "sum"))
        .assign(anomaly_rate=lambda x: x["anomaly_count"] / x["transactions"])
    )


def country_level_anomaly_rate(df: pd.DataFrame) -> pd.DataFrame:
    return _grouped_anomaly_rate(df, "country")


def expense_category_anomaly_rate(df: pd.DataFrame) -> pd.DataFrame:
    return _grouped_anomaly_rate(df, "expense_category")


def _grouped_anomaly_rate(df: pd.DataFrame, column: str) -> pd.DataFrame:
    return (
        df.groupby(column, as_index=False)
        .agg(anomaly_count=("model_prediction", "sum"), transactions=("transaction_id", "count"), spend=("amount", "sum"))
        .assign(anomaly_rate=lambda x: x["anomaly_count"] / x["transactions"])
        .sort_values("anomaly_rate", ascending=False)
    )


def monthly_transaction_trends(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("transaction_month", as_index=False)
        .agg(transactions=("transaction_id", "count"), spend=("amount", "sum"))
        .sort_values("transaction_month")
    )


def monthly_anomaly_trends(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("transaction_month", as_index=False)
        .agg(anomaly_count=("model_prediction", "sum"), transactions=("transaction_id", "count"))
        .assign(anomaly_rate=lambda x: x["anomaly_count"] / x["transactions"])
        .sort_values("transaction_month")
    )


def approval_delay_summary(df: pd.DataFrame) -> pd.DataFrame:
    return df["approval_delay_days"].describe().reset_index().rename(columns={"index": "metric", "approval_delay_days": "days"})


def explain_anomaly(row: pd.Series) -> str:
    reasons: list[str] = []
    if row.get("duplicate_invoice_flag", 0) == 1:
        reasons.append("Possible duplicate invoice")
    if row.get("urgent_payment_flag", 0) == 1 and row.get("amount", 0) >= 50_000 and row.get("vendor_risk_score", 0) >= 70:
        reasons.append("High-value urgent payment to high-risk vendor")
    elif row.get("urgent_payment_flag", 0) == 1 and row.get("amount", 0) >= 50_000:
        reasons.append("Urgent high-value payment")
    if row.get("weekend_payment_flag", 0) == 1 and row.get("vendor_risk_score", 0) >= 60:
        reasons.append("Weekend payment with elevated vendor risk")
    if row.get("approval_delay_days", 99) <= 1 and row.get("amount", 0) >= 40_000:
        reasons.append("Very fast approval for unusually high amount")
    if row.get("previous_failed_payments", 0) >= 3 or row.get("failed_payment_flag", 0) == 1:
        reasons.append("Repeated failed payments linked to vendor")
    if row.get("vendor_risk_score", 0) >= 80:
        reasons.append("High vendor risk score")
    if not reasons and row.get("amount_zscore", 0) >= 3:
        reasons.append("Transaction amount is unusually high versus peers")
    if not reasons and row.get("model_prediction", 0) == 1:
        reasons.append("Unusual transaction pattern detected by model")
    if not reasons:
        reasons.append("No major rule-based risk indicator")
    return "; ".join(dict.fromkeys(reasons))


def add_anomaly_explanations(df: pd.DataFrame) -> pd.DataFrame:
    output = df.copy()
    output["anomaly_explanation"] = output.apply(explain_anomaly, axis=1)
    return output
