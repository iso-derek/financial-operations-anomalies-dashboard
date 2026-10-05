from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.generate_data import generate_finance_operations
from src.audit_research import study,demo_rates
raw=generate_finance_operations()
scored,metrics,metadata=study(raw,demo_rates())
metadata['input_sha256']=hashlib.sha256(raw.to_csv(index=False).encode()).hexdigest()
out=ROOT/'outputs';out.mkdir(exist_ok=True)
scored.to_csv(out/'audit_scores.csv',index=False)
metrics.to_csv(out/'audit_metrics.csv',index=False)
(out/'audit_metadata.json').write_text(json.dumps(metadata,indent=2))
print(metrics.to_string(index=False));print(json.dumps(metadata,indent=2))
