"""Retrospective audit research and persistent investigation workflow."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import pandas as pd
import streamlit as st
from src.generate_data import generate_finance_operations
from src.audit_research import study,demo_rates,top_budget
from src.cases import get_case,save_case,history,STATUSES

st.set_page_config(page_title='Audit research lab',layout='wide')
st.title('Financial operations audit lab')
st.caption('Retrospective audit: approval information is available before a transaction enters evaluation. Demo data and exchange rates are fictional.')
@st.cache_data
def run_demo():
    return study(generate_finance_operations(5000),demo_rates())

upload=st.sidebar.file_uploader('Transaction CSV',type='csv')
fx_upload=st.sidebar.file_uploader('Dated FX rates CSV',type='csv')
try:
    if upload:
        if not fx_upload:
            st.info('Upload rates with currency, rate_date, usd_per_unit and source columns.');st.stop()
        scored,metrics,metadata=study(pd.read_csv(upload),pd.read_csv(fx_upload))
    else:
        scored,metrics,metadata=run_demo()
except (ValueError,KeyError) as exc:
    st.error(str(exc));st.stop()
overview,research,triage,cases=st.tabs(['Overview','Research','Review queue','Investigation cases'])
test=scored[scored.split.eq('test') & ~scored.purged]
with overview:
    department=st.multiselect('Department',sorted(test.department.unique()))
    view=test[test.department.isin(department)] if department else test
    c1,c2,c3=st.columns(3)
    c1.metric('Holdout transactions',len(view))
    c2.metric('Total USD equivalent',f"{view.amount_base.sum():,.0f}")
    c3.metric('Flagged for review',int(view.model_prediction.sum()))
    st.bar_chart(view.groupby('department').amount_base.sum())
    st.line_chart(view.groupby('transaction_month').amount_base.sum())
    st.dataframe(view.groupby('vendor_name').agg(spend_usd=('amount_base','sum'),flagged=('model_prediction','sum')).sort_values('flagged',ascending=False).head(15))
    st.caption('Overview filters affect descriptive summaries only. The research holdout and review budget stay fixed.')
with research:
    st.subheader('Untouched chronological holdout')
    st.dataframe(metrics,hide_index=True)
    st.json(metadata)
    st.caption('All methods receive the same 10% review budget. Hybrid weight and preferred method are chosen on validation data. Labelled anomaly value is not proven fraud or money saved.')
    st.download_button('Download partitioned scores',scored.to_csv(index=False),'audit_scores.csv','text/csv')
with triage:
    method=st.selectbox('Ranking method',metrics.method.tolist(),index=metrics.method.tolist().index(metadata['selected_on_validation']))
    queue=top_budget(test,method,metadata['budget'])
    st.metric('Review slots',len(queue))
    st.dataframe(queue[['transaction_id','vendor_name','department','amount','currency','amount_base',method,'available_at']],hide_index=True)
    st.caption('Original amounts are retained; amount_base is USD converted using the last available supplied FX rate. Stale-rate suitability must be assessed for the intended dataset.')
with cases:
    txn=st.selectbox('Transaction',queue.transaction_id.tolist())
    db=ROOT/'data/processed/investigations.db'
    current=get_case(db,txn) or {'status':'New','reviewer':'','notes':'','version':0}
    with st.form(f'case_{txn}_{current["version"]}'):
        status=st.selectbox('Status',STATUSES,index=STATUSES.index(current['status']))
        reviewer=st.text_input('Reviewer',current['reviewer'])
        notes=st.text_area('Investigation notes',current['notes'])
        if st.form_submit_button('Save case'):
            try:
                save_case(db,txn,status,reviewer,notes,current['version']);st.success('Case saved.');st.rerun()
            except ValueError as exc:
                st.error(str(exc))
    st.dataframe(pd.DataFrame(history(db,txn)),hide_index=True)
    st.caption('Local case register with version checks and change history; shared production use requires authentication and access controls.')
