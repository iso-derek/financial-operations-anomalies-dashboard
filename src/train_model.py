"""Run the chronological audit benchmark; preserve the command-line workflow."""
import json
from pathlib import Path
import pandas as pd
try:
    from src.audit_research import study, demo_rates
except ModuleNotFoundError:
    from audit_research import study, demo_rates
ROOT=Path(__file__).resolve().parents[1]

def train_and_score(df):
    scored,metrics,metadata=study(df,demo_rates())
    return scored,{'comparison':metrics.to_dict('records'),**metadata}

if __name__=='__main__':
    output=ROOT/'data/processed'
    output.mkdir(parents=True,exist_ok=True)
    scored,metrics=train_and_score(pd.read_csv(output/'clean_finance_operations.csv'))
    scored.to_csv(output/'scored_finance_operations.csv',index=False)
    (output/'model_summary.json').write_text(json.dumps(metrics,indent=2))
    print(json.dumps(metrics,indent=2))
