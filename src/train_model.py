"""Train an Isolation Forest model and score finance operations anomalies."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import IsolationForest
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLEAN_PATH = PROJECT_ROOT / "data" / "processed" / "clean_finance_operations.csv"
SCORED_PATH = PROJECT_ROOT / "data" / "processed" / "scored_finance_operations.csv"
SUMMARY_PATH = PROJECT_ROOT / "data" / "processed" / "model_summary.txt"

NUMERIC_FEATURES = [
    "amount",
    "approval_level",
    "account_age_days",
    "vendor_risk_score",
    "previous_failed_payments",
    "duplicate_invoice_flag",
    "urgent_payment_flag",
    "weekend_payment_flag",
    "approval_delay_days",
    "failed_payment_flag",
    "high_value_flag",
    "high_vendor_risk_flag",
    "approval_speed_flag",
    "risk_rule_score",
    "transaction_hour",
    "amount_zscore",
]
CATEGORICAL_FEATURES = [
    "department",
    "currency",
    "payment_method",
    "payment_status",
    "country",
    "region",
    "expense_category",
    "transaction_day",
]


def load_clean_data(clean_path: Path = CLEAN_PATH) -> pd.DataFrame:
    if not clean_path.exists():
        raise FileNotFoundError(
            f"Clean data not found at {clean_path}. Run `python src/clean_data.py` first."
        )
    return pd.read_csv(clean_path)


def build_pipeline(contamination: float) -> Pipeline:
    preprocess = ColumnTransformer(
        transformers=[
            ("numeric", StandardScaler(), NUMERIC_FEATURES),
            ("categorical", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
        ]
    )
    model = IsolationForest(
        n_estimators=250,
        contamination=contamination,
        random_state=42,
        n_jobs=-1,
    )
    return Pipeline(steps=[("preprocess", preprocess), ("model", model)])


def train_and_score(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    contamination = float(np.clip(df["is_anomaly"].mean(), 0.03, 0.10))
    pipeline = build_pipeline(contamination=contamination)
    features = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    pipeline.fit(df[features])

    raw_prediction = pipeline.predict(df[features])
    decision_score = pipeline.decision_function(df[features])

    scored = df.copy()
    scored["anomaly_score"] = (-decision_score).round(6)
    scored["model_prediction"] = (raw_prediction == -1).astype(int)

    y_true = scored["is_anomaly"].astype(int)
    y_pred = scored["model_prediction"].astype(int)
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    metrics = {
        "rows": len(scored),
        "contamination": contamination,
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1_score": f1_score(y_true, y_pred, zero_division=0),
        "confusion_matrix": cm,
        "features": features,
    }
    return scored, metrics


def write_model_summary(metrics: dict[str, object], summary_path: Path = SUMMARY_PATH) -> None:
    cm = metrics["confusion_matrix"]
    lines = [
        "Finance Operations Anomaly Detection Model Summary",
        "=" * 56,
        f"Rows scored: {metrics['rows']:,}",
        f"Isolation Forest contamination: {metrics['contamination']:.2%}",
        f"Precision: {metrics['precision']:.3f}",
        f"Recall: {metrics['recall']:.3f}",
        f"F1 score: {metrics['f1_score']:.3f}",
        "",
        "Confusion matrix, labels [normal, anomaly]:",
        str(cm),
        "",
        "Features used:",
        ", ".join(metrics["features"]),
        "",
        "Interpretation:",
        "Higher anomaly_score values indicate transactions that look more unusual",
        "relative to the rest of the synthetic finance operations population.",
    ]
    summary_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    SCORED_PATH.parent.mkdir(parents=True, exist_ok=True)
    df = load_clean_data()
    scored, metrics = train_and_score(df)
    scored.to_csv(SCORED_PATH, index=False)
    write_model_summary(metrics)
    print(f"Scored data saved to {SCORED_PATH}")
    print(f"Model summary saved to {SUMMARY_PATH}")
    print(f"Precision={metrics['precision']:.3f} Recall={metrics['recall']:.3f} F1={metrics['f1_score']:.3f}")


if __name__ == "__main__":
    main()
