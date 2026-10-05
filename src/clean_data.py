"""Validate raw data without fitting global thresholds or imputing labels."""
from pathlib import Path
import pandas as pd
PROJECT_ROOT=Path(__file__).resolve().parents[1]
RAW_PATH=PROJECT_ROOT/'data/raw/finance_operations_raw.csv'
CLEAN_PATH=PROJECT_ROOT/'data/processed/clean_finance_operations.csv'

def clean_finance_operations(raw_path=RAW_PATH):
    df=pd.read_csv(raw_path)
    if df.transaction_id.duplicated().any():
        raise ValueError('Duplicate transaction IDs require source reconciliation.')
    for col in ['transaction_date','invoice_date','approval_date']:
        df[col]=pd.to_datetime(df[col],errors='raise')
    return df

if __name__=='__main__':
    CLEAN_PATH.parent.mkdir(parents=True,exist_ok=True)
    clean_finance_operations().to_csv(CLEAN_PATH,index=False)
