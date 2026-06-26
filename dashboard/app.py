"""Streamlit dashboard for finance operations anomaly detection."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

from analysis import (  # noqa: E402
    add_anomaly_explanations,
    anomaly_rate,
    average_transaction_value,
    duplicate_invoice_rate,
    failed_payment_rate,
    load_scored_data,
    monthly_anomaly_trends,
    monthly_transaction_trends,
    top_high_risk_vendors,
    total_spend,
    total_transactions,
)


st.set_page_config(
    page_title="Finance Operations Anomaly Detection Dashboard",
    page_icon="",
    layout="wide",
)


@st.cache_data(show_spinner=False)
def get_data() -> pd.DataFrame:
    df = add_anomaly_explanations(load_scored_data())
    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    df["vendor_risk_band"] = pd.cut(
        df["vendor_risk_score"],
        bins=[0, 40, 70, 100],
        labels=["Low", "Medium", "High"],
        include_lowest=True,
    ).astype(str)
    return df


def format_money(value: float) -> str:
    if value >= 1_000_000:
        return f"${value / 1_000_000:,.1f}M"
    return f"${value:,.0f}"


def metric_card(label: str, value: str, help_text: str | None = None) -> None:
    st.metric(label=label, value=value, help=help_text)


def filter_data(df: pd.DataFrame) -> pd.DataFrame:
    with st.sidebar:
        st.header("Filters")
        departments = st.multiselect("Department", sorted(df["department"].unique()))
        countries = st.multiselect("Country", sorted(df["country"].unique()))
        regions = st.multiselect("Region", sorted(df["region"].unique()))
        categories = st.multiselect("Expense category", sorted(df["expense_category"].unique()))
        statuses = st.multiselect("Payment status", sorted(df["payment_status"].unique()))
        risk_bands = st.multiselect("Vendor risk band", ["Low", "Medium", "High"])
        min_date = df["transaction_date"].min().date()
        max_date = df["transaction_date"].max().date()
        date_range = st.date_input("Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date)

    filtered = df.copy()
    if departments:
        filtered = filtered[filtered["department"].isin(departments)]
    if countries:
        filtered = filtered[filtered["country"].isin(countries)]
    if regions:
        filtered = filtered[filtered["region"].isin(regions)]
    if categories:
        filtered = filtered[filtered["expense_category"].isin(categories)]
    if statuses:
        filtered = filtered[filtered["payment_status"].isin(statuses)]
    if risk_bands:
        filtered = filtered[filtered["vendor_risk_band"].isin(risk_bands)]
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
        filtered = filtered[
            (filtered["transaction_date"] >= start_date)
            & (filtered["transaction_date"] <= end_date + pd.Timedelta(days=1))
        ]
    return filtered


def render_executive_summary(df: pd.DataFrame) -> None:
    st.subheader("Executive Summary")
    cols = st.columns(6)
    with cols[0]:
        metric_card("Transactions", f"{total_transactions(df):,}")
    with cols[1]:
        metric_card("Total spend", format_money(total_spend(df)))
    with cols[2]:
        metric_card("Anomaly rate", f"{anomaly_rate(df):.1%}")
    with cols[3]:
        metric_card("Failed payments", f"{failed_payment_rate(df):.1%}")
    with cols[4]:
        metric_card("Duplicate invoices", f"{duplicate_invoice_rate(df):.1%}")
    with cols[5]:
        metric_card("Avg value", format_money(average_transaction_value(df)))


def render_transaction_trends(df: pd.DataFrame) -> None:
    st.subheader("Transaction Trends")
    monthly = monthly_transaction_trends(df)
    monthly_anomalies = monthly_anomaly_trends(df)
    cols = st.columns(3)
    with cols[0]:
        st.plotly_chart(
            px.line(monthly, x="transaction_month", y="transactions", markers=True, title="Monthly Transaction Volume"),
            use_container_width=True,
        )
    with cols[1]:
        st.plotly_chart(
            px.bar(monthly, x="transaction_month", y="spend", title="Monthly Spend"),
            use_container_width=True,
        )
    with cols[2]:
        st.plotly_chart(
            px.line(monthly_anomalies, x="transaction_month", y="anomaly_rate", markers=True, title="Monthly Anomaly Rate"),
            use_container_width=True,
        )


def render_anomaly_breakdown(df: pd.DataFrame) -> None:
    st.subheader("Anomaly Breakdown")
    anomalies = df[df["model_prediction"] == 1]
    cols = st.columns(2)
    with cols[0]:
        dept = anomalies.groupby("department", as_index=False).size().rename(columns={"size": "anomalies"})
        st.plotly_chart(px.bar(dept.sort_values("anomalies"), x="anomalies", y="department", orientation="h", title="Anomalies by Department"), use_container_width=True)
        category = anomalies.groupby("expense_category", as_index=False).size().rename(columns={"size": "anomalies"})
        st.plotly_chart(px.bar(category.sort_values("anomalies"), x="anomalies", y="expense_category", orientation="h", title="Anomalies by Expense Category"), use_container_width=True)
    with cols[1]:
        country = anomalies.groupby("country", as_index=False).size().rename(columns={"size": "anomalies"})
        st.plotly_chart(px.bar(country.sort_values("anomalies"), x="anomalies", y="country", orientation="h", title="Anomalies by Country"), use_container_width=True)
        method = anomalies.groupby("payment_method", as_index=False).size().rename(columns={"size": "anomalies"})
        st.plotly_chart(px.bar(method, x="payment_method", y="anomalies", title="Anomalies by Payment Method"), use_container_width=True)
    st.plotly_chart(
        px.histogram(df, x="anomaly_score", color="model_prediction", nbins=60, title="Anomaly Score Distribution"),
        use_container_width=True,
    )


def render_vendor_risk(df: pd.DataFrame) -> None:
    st.subheader("Vendor Risk")
    cols = st.columns([1.1, 1, 1])
    with cols[0]:
        vendors = top_high_risk_vendors(df, n=12)
        st.dataframe(
            vendors.style.format({"total_spend": "${:,.0f}", "avg_vendor_risk": "{:.1f}"}),
            use_container_width=True,
            hide_index=True,
        )
    with cols[1]:
        vendor_chart = (
            df.groupby(["vendor_id", "vendor_name"], as_index=False)
            .agg(total_spend=("amount", "sum"), anomaly_count=("model_prediction", "sum"), avg_vendor_risk=("vendor_risk_score", "mean"))
            .sort_values("total_spend", ascending=False)
            .head(50)
        )
        st.plotly_chart(
            px.scatter(
                vendor_chart,
                x="total_spend",
                y="anomaly_count",
                color="avg_vendor_risk",
                hover_name="vendor_name",
                title="Vendor Spend vs Anomaly Count",
            ),
            use_container_width=True,
        )
    with cols[2]:
        st.plotly_chart(px.histogram(df, x="vendor_risk_score", nbins=40, title="Vendor Risk Score Distribution"), use_container_width=True)


def render_transaction_explorer(df: pd.DataFrame) -> None:
    st.subheader("Transaction Explorer")
    query = st.text_input("Search transactions, vendors, invoices, departments, or explanations")
    explorer = df.copy()
    if query:
        q = query.lower()
        text_cols = ["transaction_id", "invoice_id", "vendor_id", "vendor_name", "department", "anomaly_explanation"]
        mask = explorer[text_cols].astype(str).apply(lambda col: col.str.lower().str.contains(q, na=False)).any(axis=1)
        explorer = explorer[mask]

    show_only_anomalies = st.toggle("Show flagged anomalies only", value=True)
    if show_only_anomalies:
        explorer = explorer[explorer["model_prediction"] == 1]

    display_cols = [
        "transaction_id",
        "invoice_id",
        "vendor_name",
        "department",
        "country",
        "expense_category",
        "payment_status",
        "amount",
        "vendor_risk_score",
        "anomaly_score",
        "model_prediction",
        "anomaly_explanation",
    ]

    def highlight_anomaly_row(row: pd.Series) -> list[str]:
        if row["model_prediction"] == 1:
            return [
                "background-color: #3a2417; color: #fff7ed; border-color: #5b3a24"
                for _ in row
            ]
        return ["" for _ in row]

    table = (
        explorer[display_cols]
        .sort_values(["model_prediction", "anomaly_score"], ascending=[False, False])
        .head(1_000)
    )
    st.dataframe(
        table.style.apply(highlight_anomaly_row, axis=1).format(
            {"amount": "${:,.2f}", "vendor_risk_score": "{:.1f}", "anomaly_score": "{:.4f}"}
        ),
        use_container_width=True,
        hide_index=True,
        height=520,
    )


def render_model_explanation() -> None:
    st.subheader("Model Explanation")
    st.write(
        """
        Anomaly detection identifies transactions that look unusual compared with the broader finance operations population.
        This dashboard uses Isolation Forest, an unsupervised machine learning method that isolates unusual records quickly
        because their feature combinations are rare.

        The model uses transaction amount, approval level, account age, vendor risk, previous failed payments, duplicate and
        urgent payment flags, weekend activity, approval speed, payment status, department, country, region, expense category,
        payment method, transaction day, and engineered risk indicators.

        Higher anomaly scores should be treated as investigation priorities, not automatic evidence of fraud. The tool supports
        audit triage, duplicate payment review, vendor risk monitoring, and compliance reporting, while finance professionals
        still make the final judgement using invoices, approvals, contracts, and business context.
        """
    )


def render_use_cases() -> None:
    st.subheader("Professional Use Cases")
    st.write(
        """
        This type of dashboard can support finance operations monitoring, internal audit planning, duplicate payment detection,
        vendor risk review, fraud investigation, compliance reporting, and management dashboards. It gives teams a repeatable
        way to move from raw transactions to prioritized investigation queues with clear business explanations.
        """
    )


def main() -> None:
    st.title("Finance Operations Anomaly Detection Dashboard")
    try:
        df = get_data()
    except FileNotFoundError as exc:
        st.error(str(exc))
        st.info("Run the pipeline first: python src/generate_data.py, python src/clean_data.py, python src/database.py, python src/train_model.py")
        st.stop()

    filtered = filter_data(df)
    if filtered.empty:
        st.warning("No transactions match the current filters.")
        st.stop()

    render_executive_summary(filtered)
    st.divider()
    render_transaction_trends(filtered)
    st.divider()
    render_anomaly_breakdown(filtered)
    st.divider()
    render_vendor_risk(filtered)
    st.divider()
    render_transaction_explorer(filtered)
    st.divider()
    render_model_explanation()
    render_use_cases()


if __name__ == "__main__":
    main()
