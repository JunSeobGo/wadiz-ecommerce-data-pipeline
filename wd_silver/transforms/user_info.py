from __future__ import annotations

import json
from typing import Any

import pandas as pd

from wd_silver.date_utils import to_timestamp
from wd_silver.pii import hash_series
from wd_silver.schemas import get_schema
from wd_silver.transforms.base import (
    coalesce_columns,
    double_nested_value,
    enforce_schema,
    extract_user_id_from_source_key,
    nested_value,
    normalize_columns,
)


def _interest_count(series: pd.Series) -> pd.Series:
    def count(value: Any) -> int:
        if isinstance(value, list):
            return len(value)
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return len(parsed)
            except json.JSONDecodeError:
                return 0
        return 0
    return series.map(count).astype('Int64')


def _derive_user_segment(total_funding_count: pd.Series, signature_count: pd.Series, interest_count: pd.Series) -> pd.Series:
    total_funding = pd.to_numeric(total_funding_count, errors='coerce').fillna(0)
    signature = pd.to_numeric(signature_count, errors='coerce').fillna(0)
    interests = pd.to_numeric(interest_count, errors='coerce').fillna(0)

    def segment(row: pd.Series) -> str:
        if row['total_funding'] >= 10:
            return 'high_value_backer'
        if row['total_funding'] >= 3:
            return 'repeat_backer'
        if row['total_funding'] >= 1:
            return 'backer'
        if row['signature'] >= 3:
            return 'active_supporter'
        if row['interests'] >= 3:
            return 'interest_rich_user'
        return 'light_user'

    temp = pd.DataFrame({'total_funding': total_funding, 'signature': signature, 'interests': interests})
    return temp.apply(segment, axis=1).astype('string')


def transform(df: pd.DataFrame, *, dt: str, hash_salt: str = '') -> pd.DataFrame:
    schema = get_schema('user_info')
    df = normalize_columns(df)
    out = pd.DataFrame(index=df.index)

    data_user_id = double_nested_value(df, 'data', 'userInfo', 'userId')
    source_user_id = coalesce_columns(df, ['user_id','userId','userid','encUserId','enc_user_id','_parent_user_id']).fillna(data_user_id)
    if '_source_s3_key' in df.columns:
        source_user_id = source_user_id.fillna(extract_user_id_from_source_key(df['_source_s3_key']))
    out['user_id_hash'] = hash_series(source_user_id, salt=hash_salt).astype('string')

    out['signature_count'] = coalesce_columns(df, ['signature_count','signatureCnt','signaturecnt']).fillna(nested_value(df, 'data', 'signatureCnt'))
    out['total_funding_count'] = coalesce_columns(df, ['total_funding_count','totalFundingCount','totalfundingcount']).fillna(nested_value(df, 'data', 'totalFundingCount'))
    out['follower_cnt'] = coalesce_columns(df, ['follower_cnt','followerCnt','followercnt']).fillna(nested_value(df, 'data', 'followerCnt'))
    out['following_cnt'] = coalesce_columns(df, ['following_cnt','followingCnt','followingcnt']).fillna(nested_value(df, 'data', 'followingCnt'))

    interest_keywords = coalesce_columns(df, ['interestKeyword','interest_keyword','interests']).fillna(nested_value(df, 'data', 'interestKeyword'))
    out['interest_count'] = _interest_count(interest_keywords)

    out['is_membership_user'] = coalesce_columns(df, ['is_membership_user','isValidJoinedPremiumMembership','hasMembership','has_membership']).fillna(nested_value(df, 'data', 'isValidJoinedPremiumMembership'))

    collected_at = coalesce_columns(df, ['collected_at','collectedAt','_parent_collected_at','snapshot_at','snapshotAt'])
    collected_ts = to_timestamp(collected_at)
    out['snapshot_dt'] = collected_ts.dt.strftime('%Y%m%d').fillna(dt)

    out['user_segment'] = _derive_user_segment(out['total_funding_count'], out['signature_count'], out['interest_count'])
    return enforce_schema(out, schema, dt)
