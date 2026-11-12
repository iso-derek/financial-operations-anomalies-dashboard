"""JSON API for the Audit Desk web app.

Scoring comes from ``src.audit_research.study`` and the case register from
``src.cases``; this layer adds plain-English reasons, filtering and uploads.

Run for development:  .venv/Scripts/python -m uvicorn api.main:app --reload
"""
from __future__ import annotations

import hashlib
import io
import os
import sys
import threading
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.audit_research import demo_rates, study, top_budget  # noqa: E402
from src.cases import STATUSES, connect, get_case, history, save_case  # noqa: E402
from src.generate_data import generate_finance_operations  # noqa: E402

Method = Literal["rules_score", "ml_score", "hybrid_score"]
METHOD_NAMES = {"rules_score": "Audit rules", "ml_score": "Machine learning", "hybrid_score": "Rules + machine learning"}
METHOD_BLURBS = {
    "rules_score": "Points for large amounts, risky vendors, duplicates, failed and urgent payments.",
    "ml_score": "An isolation forest that spots transactions unlike the usual pattern.",
    "hybrid_score": "A blend of both, weighted on the validation period.",
}
DB_PATH = Path(os.environ.get("AUDIT_DB_PATH", ROOT / "data" / "processed" / "investigations.db"))

app = FastAPI(title="Audit Desk API", version="1.0.0")
_lock = threading.Lock()
_datasets: dict[str, tuple[pd.DataFrame, pd.DataFrame, dict]] = {}


def dataset(key: str) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    with _lock:
        if key == "demo" and key not in _datasets:
            _datasets[key] = study(generate_finance_operations(5000), demo_rates())
        if key not in _datasets:
            raise HTTPException(404, "That uploaded dataset is no longer available. Please upload it again.")
        return _datasets[key]


def num(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if np.isfinite(value) else None


def evaluated(df: pd.DataFrame) -> pd.DataFrame:
    """The untouched chronological test period, excluding purged repeats."""
    return df[df.split.eq("test") & ~df.purged]


def reasons(row: pd.Series, meta: dict) -> list[str]:
    found = []
    if row.amount_base >= meta["train_high_value_usd"]:
        found.append("Unusually large payment")
    if row.vendor_risk_score >= 75:
        found.append("High-risk vendor")
    if row.duplicate_observed:
        found.append("Possible duplicate invoice")
    if str(row.payment_status).lower() == "failed":
        found.append("Payment failed")
    if row.urgent_payment_flag:
        found.append("Marked urgent")
    if row.approval_delay_days < 0:
        found.append("Approved before invoice date")
    if not found:
        found.append("Unusual combination of details")
    return found


def case_statuses() -> dict[str, dict]:
    with connect(DB_PATH) as conn:
        return {row["transaction_id"]: dict(row) for row in conn.execute("SELECT * FROM cases")}


def summary_row(row: pd.Series, meta: dict, method: str, cases: dict) -> dict:
    case = cases.get(str(row.transaction_id))
    return {
        "id": str(row.transaction_id), "vendor": row.vendor_name, "department": row.department,
        "category": row.get("expense_category"), "date": row.transaction_date.strftime("%Y-%m-%d"),
        "amount": num(row.amount), "currency": row.currency, "amount_usd": num(row.amount_base),
        "score": num(row[method]), "reasons": reasons(row, meta), "status": case["status"] if case else "New",
        "labelled_anomaly": bool(row.is_anomaly),
    }


# ---------------------------------------------------------------- overview
@app.get("/api/overview")
def overview(dataset_key: str = Query("demo", alias="dataset"), department: str = ""):
    df, metrics, meta = dataset(dataset_key)
    test = evaluated(df)
    view = test[test.department.eq(department)] if department else test
    monthly = view.groupby("transaction_month").amount_base.sum()
    vendors = (view.groupby("vendor_name").agg(spend=("amount_base", "sum"), flagged=("model_prediction", "sum"),
                                               transactions=("transaction_id", "count"))
               .sort_values(["flagged", "spend"], ascending=False).head(10))
    return {
        "departments": sorted(test.department.unique().tolist()),
        "kpis": {"transactions": int(len(view)), "spend": num(view.amount_base.sum()),
                 "flagged": int(view.model_prediction.sum()), "currencies": int(view.currency.nunique()),
                 "start": test.transaction_date.min().strftime("%Y-%m-%d"), "end": test.transaction_date.max().strftime("%Y-%m-%d")},
        "by_department": [{"department": d, "spend": num(v)} for d, v in
                          view.groupby("department").amount_base.sum().sort_values(ascending=False).items()],
        "monthly": [{"month": m, "spend": num(v)} for m, v in monthly.items()],
        "vendors": [{"vendor": name, "spend": num(r.spend), "flagged": int(r.flagged), "transactions": int(r.transactions)}
                    for name, r in vendors.iterrows()],
        "method": METHOD_NAMES[meta["selected_on_validation"]],
    }


# ---------------------------------------------------------------- review queue
@app.get("/api/queue")
def queue(dataset_key: str = Query("demo", alias="dataset"), method: Method | None = None, department: str = "", status: str = ""):
    df, _, meta = dataset(dataset_key)
    method = method or meta["selected_on_validation"]
    picked = top_budget(evaluated(df), method, meta["budget"])
    if department:
        picked = picked[picked.department.eq(department)]
    cases = case_statuses()
    rows = [summary_row(row, meta, method, cases) for _, row in picked.iterrows()]
    if status:
        rows = [row for row in rows if row["status"] == status]
    return {
        "method": method, "budget": meta["budget"], "selected": meta["selected_on_validation"],
        "methods": [{"key": key, "label": label, "blurb": METHOD_BLURBS[key]} for key, label in METHOD_NAMES.items()],
        "statuses": STATUSES, "rows": rows,
    }


@app.get("/api/transactions/{transaction_id}")
def transaction(transaction_id: str, dataset_key: str = Query("demo", alias="dataset")):
    df, _, meta = dataset(dataset_key)
    match = df[df.transaction_id.astype(str).eq(transaction_id)]
    if match.empty:
        raise HTTPException(404, "No transaction has that ID.")
    row = match.iloc[0]
    case = get_case(DB_PATH, transaction_id)
    details = [
        ("Vendor", row.vendor_name), ("Vendor ID", row.vendor_id), ("Department", row.department),
        ("Category", row.get("expense_category")), ("Invoice", row.invoice_id), ("Project", row.get("project_code")),
        ("Payment method", row.get("payment_method")), ("Payment status", row.payment_status),
        ("Country", row.get("country")), ("Approver", row.get("approver_id")),
        ("Approval level", int(row.approval_level)), ("Vendor risk score", f"{row.vendor_risk_score:.0f} / 100"),
        ("Vendor account age", f"{int(row.account_age_days):,} days"),
        ("Earlier failed payments", int(row.previous_failed_payments)),
    ]
    return {
        **summary_row(row, meta, meta["selected_on_validation"], {transaction_id: case} if case else {}),
        "rate": num(row.usd_per_unit), "rate_source": row.source,
        "dates": {"invoice": row.invoice_date.strftime("%Y-%m-%d"), "approved": row.approval_date.strftime("%Y-%m-%d"),
                  "paid": row.transaction_date.strftime("%Y-%m-%d"), "approval_delay_days": num(row.approval_delay_days)},
        "details": [{"label": label, "value": None if value is None or (isinstance(value, float) and np.isnan(value)) else str(value)}
                    for label, value in details],
        "scores": [{"key": key, "label": label, "score": num(row[key]),
                    "in_queue": bool(row.transaction_id in set(top_budget(evaluated(df), key, meta["budget"]).transaction_id))}
                   for key, label in METHOD_NAMES.items()],
        "evaluated": bool(row.split == "test" and not row.purged),
        "case": case or {"status": "New", "reviewer": "", "notes": "", "version": 0},
        "history": history(DB_PATH, transaction_id),
    }


class CaseUpdate(BaseModel):
    status: str
    reviewer: str = Field("", max_length=120)
    notes: str = Field("", max_length=5000)
    version: int = Field(0, ge=0)


@app.put("/api/cases/{transaction_id}")
def update_case(transaction_id: str, update: CaseUpdate):
    if update.status not in STATUSES:
        raise HTTPException(400, f"Status must be one of: {', '.join(STATUSES)}.")
    try:
        saved = save_case(DB_PATH, transaction_id, update.status, update.reviewer.strip(), update.notes, update.version)
    except ValueError as exc:
        raise HTTPException(409, "Someone else changed this case. Reload it before saving again.") from exc
    return {"case": saved, "history": history(DB_PATH, transaction_id)}


@app.get("/api/cases")
def cases(dataset_key: str = Query("demo", alias="dataset")):
    df, _, meta = dataset(dataset_key)
    by_id = df.set_index(df.transaction_id.astype(str))
    rows = []
    for case in sorted(case_statuses().values(), key=lambda item: item["updated_at"], reverse=True):
        known = case["transaction_id"] in by_id.index
        row = by_id.loc[case["transaction_id"]] if known else None
        rows.append({**case, "vendor": row.vendor_name if known else None,
                     "amount_usd": num(row.amount_base) if known else None,
                     "reasons": reasons(row, meta) if known else []})
    return {"statuses": STATUSES, "rows": rows}


# ---------------------------------------------------------------- research
@app.get("/api/research")
def research(dataset_key: str = Query("demo", alias="dataset")):
    df, metrics, meta = dataset(dataset_key)
    test = evaluated(df)
    rows = []
    for item in metrics.to_dict("records"):
        rows.append({"key": item["method"], "label": METHOD_NAMES[item["method"]], "blurb": METHOD_BLURBS[item["method"]],
                     "reviewed": int(item["reviewed"]), "precision": num(item["precision_at_budget"]),
                     "recall": num(item["recall_at_budget"]), "value": num(item["labelled_anomaly_value_usd"]),
                     "selected": item["method"] == meta["selected_on_validation"]})
    return {
        "methods": rows, "budget": meta["budget"], "hybrid_weight": meta["hybrid_ml_weight"],
        "large_payment_threshold": meta["train_high_value_usd"], "purged": meta["purged"],
        "partitions": {key: int(value) for key, value in meta["partition_counts"].items()},
        "test_transactions": int(len(test)), "labelled_anomalies": int(test.is_anomaly.sum()),
        "interpretation": meta["interpretation"],
    }


# ---------------------------------------------------------------- uploads & downloads
class Upload(BaseModel):
    transactions_csv: str = Field(..., max_length=50_000_000)
    rates_csv: str = Field(..., max_length=5_000_000)


@app.post("/api/upload")
def upload(payload: Upload):
    try:
        frame = pd.read_csv(io.StringIO(payload.transactions_csv))
        rates = pd.read_csv(io.StringIO(payload.rates_csv))
        result = study(frame, rates)
    except (ValueError, KeyError, pd.errors.ParserError) as exc:
        message = f"Missing column: {exc}" if isinstance(exc, KeyError) else str(exc)
        raise HTTPException(422, f"The files couldn't be analysed. {message}") from exc
    key = "upload-" + hashlib.sha256((payload.transactions_csv + payload.rates_csv).encode()).hexdigest()[:12]
    with _lock:
        _datasets[key] = result
    return {"dataset": key, "transactions": int(len(result[0]))}


@app.get("/api/downloads/scores")
def download_scores(dataset_key: str = Query("demo", alias="dataset")):
    df, _, _ = dataset(dataset_key)
    return Response(df.to_csv(index=False), media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="audit_scores.csv"'})


@app.get("/api/health")
def health():
    return {"status": "ok"}


WEB_DIST = ROOT / "web" / "dist"
if WEB_DIST.exists():
    app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        candidate = (WEB_DIST / path).resolve()
        if path and candidate.is_file() and WEB_DIST.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(WEB_DIST / "index.html")
