"""Real US federal contract spending from USAspending.gov (public domain).

USAspending publishes every federal contract action: recipient, amount, date,
awarding office and what was bought. There are no fraud labels, because no
public source has them, so this module only *ranks* payments that look unusual
and explains why. A flag is a prompt for a closer look, never evidence of
wrongdoing by the named recipient.

Downloads are cached in data/cache/usaspending (git-ignored).
"""
from __future__ import annotations

import json
import re
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

API = "https://api.usaspending.gov/api/v2/search/spending_by_transaction/"
CACHE = Path(__file__).resolve().parents[1] / "data" / "cache" / "usaspending"
CACHE_DAYS = 7
SOURCE_URL = "https://www.usaspending.gov"
CITATION = "USAspending.gov, U.S. Department of the Treasury (public domain U.S. government data)."
AGENCIES = {
    "hhs": "Department of Health and Human Services",
    "va": "Department of Veterans Affairs",
    "dhs": "Department of Homeland Security",
    "nasa": "National Aeronautics and Space Administration",
    "doe": "Department of Energy",
    "doi": "Department of the Interior",
    "dot": "Department of Transportation",
    "usda": "Department of Agriculture",
    "ed": "Department of Education",
    "state": "Department of State",
}
FIELDS = ["Award ID", "Mod", "Recipient Name", "Recipient UEI", "Action Date", "Transaction Amount", "Awarding Agency",
          "Awarding Sub Agency", "Award Type", "Transaction Description", "naics_description", "product_or_service_description"]
REVIEW_SHARE = 0.10


def fiscal_year_dates(year: int) -> tuple[str, str]:
    """US federal fiscal year `year` runs 1 Oct (year-1) to 30 Sep (year)."""
    return f"{year - 1}-10-01", f"{year}-09-30"


def month_windows(fiscal_year: int) -> list[tuple[str, str]]:
    first = pd.Timestamp(f"{fiscal_year - 1}-10-01")
    return [((first + pd.DateOffset(months=i)).strftime("%Y-%m-%d"),
             (first + pd.DateOffset(months=i + 1) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")) for i in range(12)]


def _request(body: dict) -> dict:
    request = urllib.request.Request(API, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "User-Agent": "audit-desk/1.0 (educational research)"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.loads(response.read())
        except OSError:
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))
    return {}


def fetch(agency: str, fiscal_year: int, per_month: int = 100, refresh: bool = False) -> list[dict]:
    """Up to `per_month` most recent contract actions from each month of the fiscal year.

    Sampling month by month spreads the data across the year instead of only the
    busy final days of September.
    """
    if agency not in AGENCIES:
        raise ValueError("Choose one of the listed agencies.")
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{agency}_{fiscal_year}.json"
    if path.exists() and not refresh and time.time() - path.stat().st_mtime < CACHE_DAYS * 86400:
        return json.loads(path.read_text(encoding="utf-8"))
    rows: list[dict] = []
    for start, end in month_windows(fiscal_year):
        body = {"filters": {"award_type_codes": ["A", "B", "C", "D"], "time_period": [{"start_date": start, "end_date": end}],
                            "agencies": [{"type": "awarding", "tier": "toptier", "name": AGENCIES[agency]}]},
                "fields": FIELDS, "limit": per_month, "page": 1, "sort": "Action Date", "order": "desc"}
        rows += _request(body).get("results", [])
    if not rows:
        raise ValueError("USAspending returned no contract actions for that agency and year.")
    path.with_suffix(".part").write_text(json.dumps(rows), encoding="utf-8")
    path.with_suffix(".part").replace(path)
    return rows


def prepare(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    df = pd.DataFrame({
        "transaction_id": df["Award ID"].astype(str) + "-" + df["Mod"].astype(str),
        "award_id": df["Award ID"].astype(str),
        "modification": df["Mod"].astype(str),
        "vendor_name": df["Recipient Name"].fillna("Unknown recipient").str.title(),
        "vendor_id": df["Recipient UEI"],
        "department": df["Awarding Sub Agency"].fillna(df["Awarding Agency"]),
        "expense_category": df["product_or_service_description"].fillna("Not stated").str.capitalize(),
        "industry": df["naics_description"].fillna("Not stated").str.capitalize(),
        "award_type": df["Award Type"].fillna("Not stated").str.capitalize(),
        "description": df["Transaction Description"].fillna(""),
        "amount": pd.to_numeric(df["Transaction Amount"], errors="coerce"),
        "transaction_date": pd.to_datetime(df["Action Date"], utc=True),
        "link": "https://www.usaspending.gov/award/" + df["generated_internal_id"].astype(str),
    })
    df = df.dropna(subset=["amount"]).drop_duplicates("transaction_id").reset_index(drop=True)
    df["currency"] = "USD"
    df["amount_base"] = df.amount
    df["transaction_month"] = df.transaction_date.dt.strftime("%Y-%m")
    return df


def score(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Rank unusual payments. Returns the frame and metadata compatible with the audit app."""
    df = df.copy()
    positive = df.amount > 0
    large = float(df.loc[positive, "amount"].quantile(0.95)) if positive.any() else np.inf
    df["is_large"] = df.amount >= large
    df["is_round"] = (df.amount >= 100_000) & (df.amount % 10_000 == 0)
    df["is_weekend"] = df.transaction_date.dt.dayofweek >= 5
    df["is_deobligation"] = df.amount < 0
    ordered = df.sort_values("transaction_date")
    same = ordered.groupby(["vendor_name", "amount"]).transaction_date.diff().dt.days
    df["is_repeat"] = (same.reindex(df.index) <= 7) & positive
    vendor_counts = df.vendor_name.map(df.vendor_name.value_counts())
    # Weekend dates are common for contract records (e.g. month-ends), so they carry little weight.
    df["rules_score"] = (3 * df.is_large + 2 * df.is_repeat + 1 * df.is_round + 0.5 * df.is_weekend).astype(float)

    # The pattern model learns from actual payments only; returned money (de-obligations) is routine and never queued.
    payments = df[positive]
    features = pd.DataFrame({"log_amount": np.log1p(payments.amount), "vendor_frequency": np.log1p(vendor_counts[positive]),
                             "is_modification": (payments.modification != "0").astype(int)})
    forest = IsolationForest(n_estimators=200, random_state=42, n_jobs=1).fit(features)
    df["ml_score"] = 0.0
    df.loc[positive, "ml_score"] = pd.Series(-forest.score_samples(features), index=payments.index).rank(pct=True)
    df["rules_rank"] = df.rules_score.rank(pct=True)
    df["hybrid_score"] = np.where(positive, 0.5 * df.ml_score + 0.5 * df.rules_rank, 0.0)
    df["anomaly_score"] = df.hybrid_score
    k = max(1, int(np.ceil(len(df) * REVIEW_SHARE)))
    df["model_prediction"] = 0
    df.loc[df.sort_values(["hybrid_score", "transaction_id"], ascending=[False, True]).head(k).index, "model_prediction"] = 1
    df["flag_reasons"] = [reasons(row) for row in df.itertuples(index=False)]
    # Columns the audit app expects; real data has no evaluation labels or time partitions.
    df["split"], df["purged"], df["is_anomaly"] = "test", False, 0
    meta = {"budget": REVIEW_SHARE, "selected_on_validation": "hybrid_score", "hybrid_ml_weight": 0.5, "labelled": False,
            "large_payment_threshold": large, "purged": 0, "partition_counts": {"test": int(len(df))},
            "interpretation": "Real public spending without fraud labels: flags rank unusual payments for review and are not evidence of wrongdoing.",
            "retrieved_at": datetime.now(timezone.utc).isoformat()}
    return df, meta


def reasons(row) -> list[str]:
    found = []
    if row.is_large:
        found.append("Among this agency's largest 5%")
    if row.is_repeat:
        found.append("Same amount to the same recipient within 7 days")
    if row.is_round:
        found.append("Round amount")
    if row.is_weekend:
        found.append("Recorded on a weekend")
    if row.is_deobligation:
        found.append("Money returned (de-obligation)")
    return found or ["Unusual pattern compared with this agency's other payments"]


def load(agency: str, fiscal_year: int) -> tuple[pd.DataFrame, dict]:
    df, meta = score(prepare(fetch(agency, fiscal_year)))
    meta.update(agency=AGENCIES[agency], fiscal_year=fiscal_year, source=CITATION, source_url=SOURCE_URL)
    return df, meta


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
