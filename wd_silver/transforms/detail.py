from __future__ import annotations

import pandas as pd

from wd_silver.date_utils import to_timestamp
from wd_silver.schemas import get_schema
from wd_silver.transforms.base import coalesce_columns, enforce_schema, normalize_columns


def transform(df: pd.DataFrame, *, dt: str, hash_salt: str = '') -> pd.DataFrame:
    schema = get_schema('detail')
    df = normalize_columns(df)
    out = pd.DataFrame(index=df.index)
    out['campaign_id'] = coalesce_columns(df, ['campaign_id','campaignId','project_id','projectId','id'])
    out['raw_title'] = coalesce_columns(df, ['raw_title','title'])
    out['crawl_status'] = coalesce_columns(df, ['crawl_status','status'])
    out['collected_ts'] = to_timestamp(coalesce_columns(df, ['collected_ts','collectedAt','crawl_ts']))
    out['is_error'] = coalesce_columns(df, ['is_error','isError'])
    out['error_type'] = coalesce_columns(df, ['error_type','errorType'])
    return enforce_schema(out, schema, dt)
