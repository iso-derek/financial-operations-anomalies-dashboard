import unittest
import tempfile
from pathlib import Path
import numpy as np
import pandas as pd
from src.generate_data import generate_finance_operations
from src.audit_research import study,prepare,demo_rates,normalize_currency,top_budget
from src.cases import save_case,get_case,history

class AuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw=generate_finance_operations(1200)
        cls.scored,cls.metrics,cls.metadata=study(cls.raw,demo_rates())
    def test_holdout_labels_never_change_fit_or_selection(self):
        changed=self.raw.copy()
        ids=self.scored.loc[self.scored.split.eq('test'),'transaction_id']
        mask=changed.transaction_id.isin(ids)
        changed.loc[mask,'is_anomaly']=1-changed.loc[mask,'is_anomaly']
        scored,_,metadata=study(changed,demo_rates())
        np.testing.assert_allclose(scored.hybrid_score,self.scored.hybrid_score)
        self.assertEqual(metadata,self.metadata)
    def test_future_amounts_do_not_change_training_scores(self):
        changed=self.raw.copy()
        ids=self.scored.loc[self.scored.split.eq('test'),'transaction_id']
        changed.loc[changed.transaction_id.isin(ids),'amount']*=100
        scored,_,metadata=study(changed,demo_rates())
        np.testing.assert_allclose(scored.loc[scored.split.eq('train'),'ml_score'],self.scored.loc[self.scored.split.eq('train'),'ml_score'])
        self.assertEqual(metadata['train_high_value_usd'],self.metadata['train_high_value_usd'])
    def test_partition_chronology_and_invoice_purge(self):
        kept=self.scored[~self.scored.purged]
        self.assertLess(kept[kept.split.eq('train')].available_at.max(),kept[kept.split.eq('validation')].available_at.min())
        self.assertLess(kept[kept.split.eq('validation')].available_at.max(),kept[kept.split.eq('test')].available_at.min())
        self.assertEqual(kept.groupby(['vendor_id','invoice_id']).split.nunique().max(),1)
    def test_equal_budget(self):
        self.assertEqual(self.metrics.reviewed.nunique(),1)
        self.assertTrue(self.metrics.precision_at_budget.between(0,1).all())
    def test_fx_no_future_or_missing_currency(self):
        rates=demo_rates();rates['rate_date']='2030-01-01'
        with self.assertRaises(ValueError):normalize_currency(self.raw,rates)
        with self.assertRaises(ValueError):normalize_currency(self.raw,demo_rates().query('currency != "NGN"'))
        converted=normalize_currency(self.raw,demo_rates())
        np.testing.assert_allclose(converted.amount_base,converted.amount*converted.usd_per_unit)
    def test_case_persistence_and_conflict(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'cases.db'
            save_case(path,'T1','In review','Derek','Check invoice',0)
            save_case(path,'T1','Resolved','Derek','Verified',1)
            self.assertEqual(get_case(path,'T1')['version'],2)
            self.assertEqual(len(history(path,'T1')),2)
            with self.assertRaises(ValueError):save_case(path,'T1','New','','',1)
    def test_dashboard(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'dashboard/app.py'),default_timeout=60).run()
        self.assertEqual(len(app.exception),0)
        self.assertEqual(len(app.tabs),4)
