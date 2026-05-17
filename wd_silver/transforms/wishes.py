from __future__ import annotations

from typing import Any

import pandas as pd

from wd_silver.date_utils import to_timestamp
from wd_silver.pii import hash_series
from wd_silver.schemas import get_schema
from wd_silver.transforms.base import coalesce_columns, enforce_schema, extract_user_id_from_source_key, normalize_columns


def _derive_is_active(df: pd.DataFrame) -> pd.Series:
    end_yn = pd.to_numeric(coalesce_columns(df, ['endYn','endyn','end_yn','isEnded','is_ended']), errors='coerce')
    remaining = pd.to_numeric(coalesce_columns(df, ['remainingDay','remainingday','remaining_day','remaining_day_at_snapshot']), errors='coerce')
    result = end_yn.map(lambda value: pd.NA if pd.isna(value) else bool(value == 0))
    fallback = remaining.map(lambda value: pd.NA if pd.isna(value) else bool(value >= 0))
    return result.where(result.notna(), fallback)


def transform(df: pd.DataFrame, *, dt: str, hash_salt: str = '') -> pd.DataFrame:
    schema = get_schema('wishes')
    df = normalize_columns(df)
    out = pd.DataFrame(index=df.index)

    source_user_id = coalesce_columns(df, ['user_id','userId','userid','encUserId','enc_user_id','_parent_user_id'])
    if '_source_s3_key' in df.columns:
        source_user_id = source_user_id.fillna(extract_user_id_from_source_key(df['_source_s3_key']))
    out['user_id_hash'] = hash_series(source_user_id, salt=hash_salt).astype('string')

    out['campaign_id'] = coalesce_columns(df, ['campaign_id','campaignId','campaignid','project_id','projectId','id'])
    snapshot_source = coalesce_columns(df, ['snapshot_at','snapshotAt','collected_at','collectedAt','_parent_collected_at','created_at','createdAt','whenCreated'])
    out['snapshot_at'] = to_timestamp(snapshot_source)
    fallback = pd.to_datetime(f'{dt[0:4]}-{dt[4:6]}-{dt[6:8]} 00:00:00')
    out['snapshot_at'] = out['snapshot_at'].fillna(fallback)
    out['snapshot_dt'] = out['snapshot_at'].dt.strftime('%Y%m%d').fillna(dt)
    out['wish_snapshot_date'] = out['snapshot_dt']
    out['campaign_title'] = coalesce_columns(df, ['campaign_title','campaignTitle','title','projectTitle'])
    out['maker_name'] = coalesce_columns(df, ['maker_name','makerName','makername','nickName','nickname'])
    out['achievement_rate_at_wish_snapshot'] = coalesce_columns(df, ['achievement_rate_at_wish_snapshot','achievementRate','achievementrate','achievement_rate'])
    out['remaining_day_at_wish_snapshot'] = coalesce_columns(df, ['remaining_day_at_wish_snapshot','remainingDay','remainingday','remaining_day'])
    out['amount_at_wish_snapshot'] = coalesce_columns(df, ['amount_at_wish_snapshot','amount','totalBackedAmount','totalbackedamount','fundingAmount','funding_amount'])
    out['product_type'] = coalesce_columns(df, ['product_type','productType','producttype'])
    out['is_active_at_snapshot'] = _derive_is_active(df)
    return enforce_schema(out, schema, dt)
