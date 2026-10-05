# Financial Operations Audit Research Lab

A Python/Streamlit project connecting accounting controls to anomaly detection and a persistent investigation workflow. The research question is whether combining rules and an unsupervised model improves audit yield at a fixed reviewer budget.

## Run

```bash
pip install -r requirements.txt
streamlit run dashboard/app.py
python -m unittest discover -s tests -v
python scripts/run_research.py
```

The dashboard generates a 5,000-record synthetic demonstration. The reproducible CLI benchmark uses 25,000 records. Neither represents a real organisation. Upload transaction and dated FX CSVs to study another labelled dataset.

## Implemented

- Chronological training/validation/test partitions, ordered by when transaction and approval information are both available; cross-partition invoice groups are purged.
- Median imputation, scaling, Isolation Forest and high-value thresholds fit only on training data. No label-based contamination estimate.
- Rules, ML and hybrid rankings compared on the same final holdout with the same 10% review budget. Validation chooses the hybrid weight and preferred method.
- Original amount/currency retained alongside USD equivalent and dated FX provenance. Future rates and missing currencies are rejected. Demonstration rates are explicitly fictional.
- Holdout spending summaries, department filtering, trends and vendor review; fixed-budget review queue and downloadable scores.
- SQLite investigation status, reviewer notes, version conflict detection and append-only application change history.

The older batch entry points remain available: `python src/generate_data.py`, `python src/clean_data.py`, `python src/train_model.py`. Their output is now chronological research scores and `data/processed/model_summary.json`. Case records live in `data/processed/investigations.db` and are excluded from Git.

## Interpretation

This is a retrospective audit, not real-time fraud prevention. Approval outcomes must be known before an item enters the study. An unusual transaction is not proven fraud. Captured labelled value is neither recovered loss nor savings. Rule explanations are rule evidence, not causal model explanations.

The synthetic generator embeds simple anomaly patterns and uses the same nominal amount distribution across currencies. Normalisation does not make those distributions economically realistic. FX staleness, historical vendor attributes, unobserved fraud, privacy, access control and external validity require further work with a suitable real dataset. Local case history is not a tamper-proof production audit log.

See [research protocol](docs/RESEARCH_PROTOCOL.md) and [measured results](docs/RESEARCH_RESULTS.md).
