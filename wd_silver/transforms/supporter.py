from __future__ import annotations

import pandas as pd

from wd_silver.date_utils import to_timestamp
from wd_silver.pii import hash_series
from wd_silver.schemas import get_schema
from wd_silver.transforms.base import coalesce_columns, enforce_schema, normalize_columns


def _flatten_raw(df: pd.DataFrame) -> pd.DataFrame:
    if 'raw_text' in df.columns:
        raw_df = pd.json_normalize(df['raw_text']).add_prefix('raw.')
        return pd.concat([df.reset_index(drop=True), raw_df.reset_index(drop=True)], axis=1)
    if 'raw' in df.columns:
        raw_df = pd.json_normalize(df['raw']).add_prefix('raw.')
        return pd.concat([df.reset_index(drop=True), raw_df.reset_index(drop=True)], axis=1)
    return df


def transform(df: pd.DataFrame, *, dt: str, hash_salt: str = '') -> pd.DataFrame:
    schema = get_schema('supporter')
    df = normalize_columns(_flatten_raw(df))
    out = pd.DataFrame(index=df.index)

    source_user_id = coalesce_columns(df, ['user_id','userId','memberId','supporterId','encUserId','raw.encUserId','raw.userInfo.userId'])
    out['user_id_hash'] = hash_series(source_user_id, salt=hash_salt).astype('string')
    out['campaign_id'] = coalesce_columns(df, ['campaign_id','campaignId','campaignid','project_id','projectId','commonId'])
    out['supporter_type'] = coalesce_columns(df, ['supporter_type','supportType','type','raw.type'])
    out['backing_amount'] = coalesce_columns(df, ['backing_amount','amount','fundingAmount','backedAmount','raw.backedAmount'])
    out['participated_at'] = to_timestamp(coalesce_columns(df, ['participated_at','participatedAt','createdAt','whenCreated','raw.whenCreated']))
    fallback = pd.to_datetime(f'{dt[0:4]}-{dt[4:6]}-{dt[6:8]} 00:00:00')
    out['participated_at'] = out['participated_at'].fillna(fallback)
    out['participated_date'] = out['participated_at'].dt.strftime('%Y%m%d')
    raw_type = out['supporter_type'].astype('string').fillna('')
    amount_num = pd.to_numeric(out['backing_amount'], errors='coerce').fillna(0)
    out['is_purchaser'] = raw_type.str.contains('purchase|fund|back|preorder|reward|구매|펀딩', case=False, regex=True) | (amount_num > 0)
    out['is_signer'] = raw_type.str.contains('sign|signature|지지', case=False, regex=True)
    out['raw_support_type'] = out['supporter_type']
    out['dont_show_amount'] = coalesce_columns(df, ['dont_show_amount','dontShowAmount','raw.dontShowAmount'])
    out['is_active_user'] = coalesce_columns(df, ['is_active_user','isActiveUser','activeUser','raw.activeUser'])
    out['has_membership'] = coalesce_columns(df, ['has_membership','hasMembership','raw.hasMembership'])
    return enforce_schema(out, schema, dt)
