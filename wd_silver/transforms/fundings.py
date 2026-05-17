from __future__ import annotations

from typing import Any

import pandas as pd

from wd_silver.date_utils import to_timestamp
from wd_silver.pii import hash_series
from wd_silver.schemas import get_schema
from wd_silver.transforms.base import coalesce_columns, enforce_schema, extract_user_id_from_source_key, normalize_columns


def _amount_tier(amount: pd.Series) -> pd.Series:
    amount_num = pd.to_numeric(amount, errors='coerce').fillna(0)

    def bucket(value: float) -> str:
        if value <= 0:
            return 'unknown'
        if value < 30000:
            return 'under_30k'
        if value < 100000:
            return '30k_100k'
        if value < 300000:
            return '100k_300k'
        return 'over_300k'

    return amount_num.map(bucket).astype('string')


def _normalize_action_type(product_type: pd.Series) -> pd.Series:
    def normalize(value: Any) -> str:
        if value is None:
            return 'funding'
        try:
            if pd.isna(value):
                return 'funding'
        except TypeError:
            pass
        text = str(value).strip().upper()
        if text in {'REWARD', 'PREORDER', 'FUNDING'}:
            return 'funding'
        return text.lower() if text else 'funding'

    return product_type.map(normalize).astype('string')


def transform(df: pd.DataFrame, *, dt: str, hash_salt: str = '') -> pd.DataFrame:
    schema = get_schema('fundings')
    df = normalize_columns(df)
    out = pd.DataFrame(index=df.index)

    source_user_id = coalesce_columns(df, ['user_id','userId','userid','encUserId','enc_user_id','_parent_user_id'])
    if '_source_s3_key' in df.columns:
        source_user_id = source_user_id.fillna(extract_user_id_from_source_key(df['_source_s3_key']))
    out['user_id_hash'] = hash_series(source_user_id, salt=hash_salt).astype('string')

    out['campaign_id'] = coalesce_columns(df, ['campaign_id','campaignId','campaignid','project_id','projectId','id'])
    out['amount'] = coalesce_columns(df, ['amount','backedAmount','backed_amount','funding_amount','fundingAmount'])
    out['campaign_title'] = coalesce_columns(df, ['campaign_title','campaignTitle','title','projectTitle'])
    out['product_type'] = coalesce_columns(df, ['product_type','productType','producttype'])
    out['action_type'] = _normalize_action_type(out['product_type'])

    funded_at_source = coalesce_columns(df, ['funded_at','fundedAt','created_at','createdAt','whenCreated','collected_at','collectedAt','_parent_collected_at'])
    out['funded_at'] = to_timestamp(funded_at_source)
    fallback = pd.to_datetime(f'{dt[0:4]}-{dt[4:6]}-{dt[6:8]} 00:00:00')
    out['funded_at'] = out['funded_at'].fillna(fallback)
    out['funded_date'] = out['funded_at'].dt.strftime('%Y%m%d')
    out['funded_hour'] = out['funded_at'].dt.hour
    out['funded_dow'] = out['funded_at'].dt.dayofweek
    out['amount_tier'] = _amount_tier(out['amount'])
    out['remaining_day_at_snapshot'] = coalesce_columns(df, ['remaining_day_at_snapshot','remainingDay','remainingday','remaining_day'])
    out['achievement_rate_at_snapshot'] = coalesce_columns(df, ['achievement_rate_at_snapshot','achievementRate','achievementrate'])
    return enforce_schema(out, schema, dt)
