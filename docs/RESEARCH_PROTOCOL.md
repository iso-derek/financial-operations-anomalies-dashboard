# Audit yield at a fixed review budget

**Question:** Does a validation-selected rules/Isolation Forest mixture recover more planted anomalies in later transactions than either component alone, at a fixed 10% review budget?

1. Convert original currency using the last supplied rate dated on or before the transaction. Retain rate date and source. No future-rate fill. Rates are assumed available on their stated date; for published rates with release lags, supply their actual availability date.
2. Define audit availability as max(transaction date, approval date). Split unique ordered availability timestamps at 60%/80%. Keep a vendor/invoice group only in its earliest partition, purging later repeats. Compute duplicate evidence from earlier observable invoices, not the planted duplicate flag.
3. Fit median imputation, standardisation and 150-tree Isolation Forest on training rows only, contamination=auto. Fit the 95th-percentile amount rule and empirical rank scales on the same rows. Vendor history attributes are assumed contemporaneously available; a real dataset must verify this.
4. Compare ML weights {0,.25,.5,.75,1} using validation precision at the fixed budget. Freeze the mixture and preferred method. Labels are used for validation selection and final evaluation, never unsupervised feature fitting or contamination estimation.
5. Evaluate all three rankings on retained test rows, with ceil(.1 × test count) reviews and transaction-ID tie breaks. Report precision, recall and labelled anomaly USD value. Do not interpret this value as prevented fraud.
6. Preserve partitioned predictions, metadata, source hash and purged count in `outputs/`. Investigation notes never feed back into this frozen benchmark.

This is an exploratory single-seed synthetic experiment, not a claim of novel detection accuracy. No confidence interval or multi-dataset significance claim is made. Follow-up research should lock the method before collecting independently adjudicated cases, vary review budgets and repeat across time windows and organisations. Cross-invoice purging means the reported population excludes later repeat groups and cannot evaluate every duplicate-payment pattern.

Run `python scripts/run_research.py`. Tests explicitly change final-test labels and amounts to verify fitting/selection invariance, check chronological and invoice separation, enforce FX availability, and verify persistent case history and stale-write rejection.
