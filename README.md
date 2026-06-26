# Finance Operations Anomaly Detection Dashboard

## Overview

`finance-operations-anomaly-dashboard` is a complete Python data science portfolio project for detecting suspicious activity in finance operations data. It uses a fully synthetic transaction dataset, SQLite, feature engineering, Isolation Forest anomaly detection, and a Streamlit dashboard designed for accounting, audit, risk, and finance operations teams.

The project demonstrates how a data scientist can turn raw payment and invoice activity into a practical investigation workflow: generate realistic data, clean and engineer risk features, persist records in SQL, train an anomaly detection model, score transactions, and explain potential issues in business language.

## Business Problem

Finance departments process high volumes of invoices, vendor payments, project costs, approvals, refunds, and failed transactions. Unusual activity can lead to duplicate payments, financial loss, compliance exceptions, fraud exposure, and audit concerns.

This project focuses on detecting and explaining patterns such as:

- Unusually high payments
- Duplicate invoice references
- Repeated failed payments
- High-risk vendors
- Urgent high-value payments
- Weekend payments
- Very fast approvals for large amounts
- Suspicious combinations of vendor risk, payment value, approval level, and payment history

## Why Finance Anomaly Detection Matters

Traditional finance controls often rely on sampled audits, manual spreadsheet checks, and rule-based exception reports. Those methods are useful, but they can miss complex combinations of risk indicators. Anomaly detection helps teams prioritize transactions that deserve review, even when each individual field may appear plausible on its own.

This type of project is relevant for graduate data science roles, fraud and risk analytics roles, anti-piracy or media protection analytics organizations, finance operations teams, internal audit teams, and MSc Finance/Data Science applications.

## Target Users

- Finance operations analysts
- Accounts payable teams
- Internal audit teams
- Fraud and risk analytics teams
- Compliance reporting teams
- Finance transformation and data science teams
- Managers who need exception monitoring dashboards

## Dataset Description

The dataset is synthetic and contains at least 20,000 finance operations transactions. No confidential or real financial records are used.

Core fields include transaction identifiers, invoice identifiers, vendor details, department, project code, transaction and approval dates, amount, currency, payment method, payment status, country, region, expense category, approver, approval level, account age, vendor risk score, previous failed payments, duplicate invoice flags, urgent payment flags, weekend payment flags, days to approve, and a planted anomaly label.

Additional engineered features include:

- `transaction_month`
- `transaction_day`
- `transaction_hour`
- `amount_zscore`
- `approval_delay_days`
- `failed_payment_flag`
- `high_value_flag`
- `high_vendor_risk_flag`
- `approval_speed_flag`
- `risk_rule_score`
- `anomaly_score`
- `model_prediction`
- Business-friendly anomaly explanations

## Project Structure

```text
finance-operations-anomaly-dashboard/
  data/
    raw/
    processed/
  notebooks/
  src/
    generate_data.py
    clean_data.py
    database.py
    train_model.py
    analysis.py
  dashboard/
    app.py
  assets/
  README.md
  requirements.txt
  .gitignore
```

## Tech Stack

- Python
- pandas
- numpy
- SQLite
- SQL
- scikit-learn
- Isolation Forest
- Streamlit
- Plotly
- datetime
- pathlib

## How To Run

From the project root:

```bash
pip install -r requirements.txt
python src/generate_data.py
python src/clean_data.py
python src/database.py
python src/train_model.py
streamlit run dashboard/app.py
```

The pipeline creates:

- `data/raw/finance_operations_raw.csv`
- `data/processed/clean_finance_operations.csv`
- `data/processed/finance_operations.db`
- `data/processed/scored_finance_operations.csv`
- `data/processed/model_summary.txt`

## Dashboard Features

### Executive Summary

KPI cards show total transactions, total spend, anomaly rate, failed payment rate, duplicate invoice rate, and average transaction value.

### Filters

Users can filter by department, country, region, expense category, payment status, vendor risk band, and date range.

### Transaction Trends

The dashboard includes monthly transaction volume, monthly spend, and monthly anomaly rate charts.

### Anomaly Breakdown

Charts show anomalies by department, country, expense category, payment method, and anomaly score distribution.

### Vendor Risk

The vendor risk section includes top high-risk vendors, vendor spend versus anomaly count, and vendor risk score distribution.

### Transaction Explorer

A searchable table highlights flagged transactions and includes model scores plus business-friendly explanations such as:

- High-value urgent payment to high-risk vendor
- Possible duplicate invoice
- Weekend payment with elevated vendor risk
- Very fast approval for unusually high amount
- Repeated failed payments linked to vendor

### Model Explanation

The dashboard explains anomaly detection, why Isolation Forest is useful, which features are used, how finance teams should interpret anomaly scores, and why the model supports audit review without replacing human judgement.

## Model Approach

The model uses Isolation Forest, an unsupervised anomaly detection algorithm. It is well suited to this use case because suspicious finance transactions are expected to be rare and structurally different from the majority of normal transactions.

Features include transaction value, approval level, account age, vendor risk score, failed payment history, duplicate invoice indicators, urgency indicators, weekend payment indicators, approval delay, engineered rule scores, department, currency, payment method, payment status, country, region, expense category, transaction day, and transaction hour.

The synthetic `is_anomaly` label is used for evaluation only. The model outputs:

- `anomaly_score`: higher values indicate more unusual transactions
- `model_prediction`: 1 for model-flagged anomalies, 0 for normal transactions
- Precision, recall, F1 score, and confusion matrix in `model_summary.txt`

## Key Business Insights

The project is designed to surface practical finance questions:

- Which departments generate the most unusual transactions?
- Are duplicate invoice flags concentrated among specific vendors?
- Do urgent payments have higher anomaly rates?
- Are high-risk vendors associated with larger transaction values?
- Do failed payments cluster around specific payment methods or countries?
- Are large payments being approved unusually quickly?

## Example Use Cases

- Finance operations monitoring: prioritize unusual transactions for review.
- Internal audit: identify high-risk areas before detailed testing.
- Duplicate payment detection: flag repeated invoice references and vendor-amount combinations.
- Vendor risk review: monitor high-risk vendors with unusual spend patterns.
- Fraud investigation: create an explainable queue of suspicious transactions.
- Compliance reporting: summarize exceptions by department, country, category, and month.
- Management dashboards: provide leadership with anomaly trends and risk indicators.

## Screenshots

Add screenshots of the Streamlit dashboard here after running the app locally.

Suggested screenshots:

- Executive summary and filters
- Monthly trends
- Anomaly breakdown
- Vendor risk section
- Transaction explorer with explanations

## Limitations

- The dataset is synthetic and does not represent any real organization.
- Planted anomaly labels are useful for evaluation but simplify real-world ambiguity.
- Isolation Forest identifies unusual patterns, not proven fraud.
- Thresholds and risk rules would need validation from finance professionals.
- Currency conversion is not normalized in this demo.
- The dashboard is designed for portfolio review and prototyping, not production deployment.

## Future Improvements

- Add currency normalization using exchange rates.
- Add user authentication and role-based access.
- Add invoice attachment review workflow.
- Add case management fields for investigation status and reviewer notes.
- Compare Isolation Forest with Local Outlier Factor, One-Class SVM, and supervised models.
- Add SHAP-style model interpretation for richer explanations.
- Add SQL-based audit tests for duplicate invoices and approval policy exceptions.
- Deploy the dashboard to Streamlit Community Cloud or an internal analytics environment.

## Resume Bullet Examples

- Built an end-to-end finance operations anomaly detection dashboard using Python, pandas, SQLite, scikit-learn, Isolation Forest, Streamlit, and Plotly.
- Generated and modeled 25,000 synthetic invoice and payment records to detect duplicate payments, high-risk vendors, failed payments, urgent high-value transactions, and suspicious approval patterns.
- Engineered finance risk features and produced business-friendly anomaly explanations to support audit triage, fraud investigation, and vendor risk review.
- Designed an interactive dashboard with executive KPIs, transaction trends, anomaly breakdowns, vendor risk analysis, and a searchable investigation queue.
- Evaluated anomaly detection performance using precision, recall, F1 score, and confusion matrix against planted synthetic labels.
