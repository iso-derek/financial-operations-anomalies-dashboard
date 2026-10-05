"""Chronological retrospective audit; labels never enter feature fitting."""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

FEATURES = ['amount_base', 'approval_level', 'account_age_days', 'vendor_risk_score',
            'previous_failed_payments', 'urgent_payment_flag', 'approval_delay_days']


def demo_rates():
    return pd.DataFrame([{'currency': c, 'rate_date': '2020-01-01', 'usd_per_unit': v,
                          'source': 'Fictional fixed demonstration rate'}
                         for c,v in {'USD':1,'GBP':1.25,'EUR':1.1,'NGN':.0007,'INR':.012}.items()])


def normalize_currency(frame, rates):
    df = frame.copy()
    rates = rates.copy()
    if not {'currency','rate_date','usd_per_unit','source'} <= set(rates):
        raise ValueError('FX data require currency, rate_date, usd_per_unit and source.')
    if df.currency.isna().any() or rates[['currency','rate_date','usd_per_unit','source']].isna().any().any():
        raise ValueError('Currency and rate provenance cannot be missing.')
    rates['usd_per_unit']=pd.to_numeric(rates.usd_per_unit,errors='raise')
    rates['rate_date'] = pd.to_datetime(rates.rate_date, utc=True)
    if rates.duplicated(['currency','rate_date']).any() or not np.isfinite(rates.usd_per_unit).all() or (rates.usd_per_unit <= 0).any():
        raise ValueError('FX rates must be unique, positive and finite.')
    df['transaction_date'] = pd.to_datetime(df.transaction_date, utc=True, errors='raise')
    parts=[]
    for currency, rows in df.groupby('currency', dropna=False):
        lookup=rates[rates.currency.eq(currency)].drop(columns='currency')
        if lookup.empty:
            raise ValueError(f'Missing FX rates: {currency}')
        joined=pd.merge_asof(rows.sort_values('transaction_date'), lookup.sort_values('rate_date'),
                             left_on='transaction_date', right_on='rate_date', direction='backward')
        if joined.usd_per_unit.isna().any():
            raise ValueError(f'No historically available FX rate: {currency}')
        parts.append(joined)
    df=pd.concat(parts, ignore_index=True)
    df['amount_base']=pd.to_numeric(df.amount, errors='raise')*df.usd_per_unit
    if not np.isfinite(df.amount_base).all() or (df.amount_base<0).any():
        raise ValueError('Amounts must be finite and nonnegative.')
    return df


def prepare(frame, rates):
    df=normalize_currency(frame, rates)
    if df.transaction_id.isna().any() or df.transaction_id.duplicated().any():
        raise ValueError('Transaction IDs must be unique.')
    for col in ['approval_date','invoice_date']:
        df[col]=pd.to_datetime(df[col],utc=True,errors='raise')
    if df[['transaction_date','approval_date','invoice_date']].isna().any().any():
        raise ValueError('Dates cannot be missing.')
    df['transaction_month']=df.transaction_date.dt.strftime('%Y-%m')
    df['failed_payment_flag']=df.payment_status.str.lower().eq('failed').astype(int)
    df['available_at']=df[['transaction_date','approval_date']].max(axis=1)
    df['approval_delay_days']=(df.approval_date-df.invoice_date).dt.total_seconds()/86400
    df=df.sort_values(['available_at','transaction_id']).reset_index(drop=True)
    if len(df)<100 or not df.is_anomaly.isin([0,1]).all():
        raise ValueError('Need at least 100 transactions with binary evaluation labels.')
    times=df.available_at.drop_duplicates().sort_values().tolist()
    if len(times)<10:
        raise ValueError('Need at least ten distinct audit times.')
    df['split']=np.where(df.available_at<times[int(len(times)*.6)],'train',
                        np.where(df.available_at<times[int(len(times)*.8)],'validation','test'))
    # Keep an invoice group in its earliest partition; purge later repeats from evaluation.
    group=df.vendor_id.astype(str)+'|'+df.invoice_id.astype(str)
    earliest=df.groupby(group)['split'].transform('first')
    df['purged']=df.split.ne(earliest)
    df['duplicate_observed']=group.duplicated().astype(int)
    return df


def top_budget(frame, column, fraction):
    if not 0<fraction<=1:
        raise ValueError('Review fraction must be in (0,1].')
    k=max(1,int(np.ceil(len(frame)*fraction)))
    return frame.sort_values([column,'transaction_id'],ascending=[False,True]).head(k)


def study(frame, rates, budget=.1):
    df=prepare(frame,rates)
    train=df[df.split.eq('train') & ~df.purged]
    val=df[df.split.eq('validation') & ~df.purged]
    test=df[df.split.eq('test') & ~df.purged]
    if min(map(len,[train,val,test]))<10:
        raise ValueError('Each partition needs at least ten retained transactions.')
    high=float(train.amount_base.quantile(.95))
    df['rules_score']=(2*(df.amount_base>=high)+2*(df.vendor_risk_score>=75)
                       +3*df.duplicate_observed+2*df.payment_status.str.lower().eq('failed')
                       +df.urgent_payment_flag).astype(float)
    pipeline=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),
                           IsolationForest(n_estimators=150,contamination='auto',random_state=42,n_jobs=1))
    pipeline.fit(df.loc[train.index,FEATURES])
    df['ml_raw']=-pipeline.score_samples(df[FEATURES])
    for name,source in [('ml_score','ml_raw'),('rules_rank','rules_score')]:
        reference=np.sort(df.loc[train.index,source].to_numpy())
        df[name]=np.searchsorted(reference,df[source],side='right')/len(reference)
    candidates=[]
    for weight in [0,.25,.5,.75,1]:
        df['candidate']=weight*df.ml_score+(1-weight)*df.rules_rank
        chosen=top_budget(df.loc[val.index],'candidate',budget)
        candidates.append((float(chosen.is_anomaly.mean()),weight))
    weight=max(candidates,key=lambda x:(x[0],-abs(x[1]-.5)))[1]
    df['hybrid_score']=weight*df.ml_score+(1-weight)*df.rules_rank
    df=df.drop(columns='candidate')
    methods=['rules_score','ml_score','hybrid_score']
    selected=max(methods,key=lambda m:top_budget(df.loc[val.index],m,budget).is_anomaly.mean())
    df['anomaly_score']=df[selected]
    df['model_prediction']=0
    for partition in ['train','validation','test']:
        eligible=df[df.split.eq(partition) & ~df.purged]
        df.loc[top_budget(eligible,selected,budget).index,'model_prediction']=1
    metrics=[]
    for method in methods:
        reviewed=top_budget(df.loc[test.index],method,budget)
        positives=int(df.loc[test.index,'is_anomaly'].sum())
        metrics.append({'method':method,'reviewed':len(reviewed),'precision_at_budget':float(reviewed.is_anomaly.mean()),
                        'recall_at_budget':float(reviewed.is_anomaly.sum()/positives) if positives else None,
                        'labelled_anomaly_value_usd':float(reviewed.loc[reviewed.is_anomaly.eq(1),'amount_base'].sum())})
    metadata={'budget':budget,'hybrid_ml_weight':weight,'selected_on_validation':selected,
              'train_high_value_usd':high,'purged':int(df.purged.sum()),
              'partition_counts':df.loc[~df.purged,'split'].value_counts().to_dict(),
              'interpretation':'Retrospective synthetic audit; captured labelled value is not fraud loss or savings.'}
    return df,pd.DataFrame(metrics),metadata
