from __future__ import annotations

import re
from typing import Any

import pandas as pd

from wd_silver.date_utils import to_timestamp
from wd_silver.mappings import map_biz_model, map_category_name, map_status
from wd_silver.schemas import get_schema
from wd_silver.transforms.base import coalesce_columns, enforce_schema, normalize_columns


def _snapshot_from_source_key(df: pd.DataFrame, dt: str) -> pd.Series:
    if '_source_s3_key' not in df.columns:
        return pd.Series([pd.NaT] * len(df), index=df.index, dtype='datetime64[ns]')

    def parse(value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        hour_match = re.search(r'hour=(\d{2})', value)
        hour = hour_match.group(1) if hour_match else '00'
        return f'{dt[0:4]}-{dt[4:6]}-{dt[6:8]} {hour}:00:00'

    return to_timestamp(df['_source_s3_key'].map(parse))


def transform(df: pd.DataFrame, *, dt: str, hash_salt: str = '') -> pd.DataFrame:
    schema = get_schema('preorder')
    df = normalize_columns(df)
    out = pd.DataFrame(index=df.index)

    out['campaign_id'] = coalesce_columns(df, ['campaign_id','campaignId','campaignid','project_id','projectId','id'])
    out['maker_id'] = coalesce_columns(df, ['maker_id','makerId','userId','userid'])
    out['maker_name'] = coalesce_columns(df, ['maker_name','makerName','makername','nickName','nickname'])
    out['corp_name'] = coalesce_columns(df, ['corp_name','corpName','corpname'])
    out['title'] = coalesce_columns(df, ['title','campaignTitle','projectTitle'])
    out['category_code'] = coalesce_columns(df, ['category_code','categoryCode','categorycode','category','custValueCodeNm'])
    out['category_name'] = coalesce_columns(df, ['category_name','categoryName','categoryname','custValueCodeNm']).fillna(out['category_code'].apply(map_category_name))
    out['core_message'] = coalesce_columns(df, ['core_message','coreMessage','coremessage','summary'])
    out['open_ts'] = to_timestamp(coalesce_columns(df, ['open_ts','whenOpen','startDateTime','openDateTime']))
    out['close_ts'] = to_timestamp(coalesce_columns(df, ['close_ts','closeDateTime','endDateTime']))

    snapshot_source = coalesce_columns(df, ['snapshot_ts','collected_ts','collectedAt','crawl_ts','_parent_collected_at'])
    out['snapshot_ts'] = to_timestamp(snapshot_source)
    out['snapshot_ts'] = out['snapshot_ts'].fillna(_snapshot_from_source_key(df, dt))
    fallback_ts = pd.to_datetime(f'{dt[0:4]}-{dt[4:6]}-{dt[6:8]} 00:00:00')
    out['snapshot_ts'] = out['snapshot_ts'].fillna(fallback_ts)
    out['snapshot_dt'] = out['snapshot_ts'].dt.strftime('%Y%m%d').fillna(dt)

    out['remaining_day'] = coalesce_columns(df, ['remaining_day','remainingDay','remainingday'])
    out['remaining_days_at_snapshot'] = coalesce_columns(df, ['remaining_days_at_snapshot','remainingDay','remainingday','remaining_day'])
    out['achievement_rate'] = coalesce_columns(df, ['achievement_rate','achievementRate','achievementrate'])
    out['funding_ratio'] = coalesce_columns(df, ['funding_ratio','fundingRatio','fundingratio'])
    out['target_amount'] = coalesce_columns(df, ['target_amount','targetAmount','targetamount'])
    out['total_funding_amount'] = coalesce_columns(df, ['total_funding_amount','totalBackedAmount','totalbackedamount','funding_amount','fundingAmount','amount'])
    out['participation_cnt'] = coalesce_columns(df, ['participation_cnt','participationCnt','participationcnt','supporter_count','supporterCount'])
    out['signature_cnt'] = coalesce_columns(df, ['signature_cnt','signatureCnt','signaturecnt'])
    out['status_simplified'] = coalesce_columns(df, ['status_simplified','status']).apply(map_status)
    out['biz_model'] = coalesce_columns(df, ['biz_model','productType','product_type','producttype']).apply(map_biz_model)
    out['is_adult'] = coalesce_columns(df, ['is_adult','isAdult','adult'])
    out['has_coupon'] = coalesce_columns(df, ['has_coupon','hasCoupon','hascoupon'])
    out['maker_club_grade'] = coalesce_columns(df, ['maker_club_grade','makerClubGrade','makerclubgrade'])
    out['is_delivery_available'] = coalesce_columns(df, ['is_delivery_available','isDeliveryAvailable','isdeliveryavailable'])
    out['is_global_shipping_available'] = coalesce_columns(df, ['is_global_shipping_available','isGlobalShippingAvailable','isglobalshippingavailable'])
    out['thumbnail_url'] = coalesce_columns(df, ['thumbnail_url','photoUrl','imageUrl','thumbnail'])

    return enforce_schema(out, schema, dt)
