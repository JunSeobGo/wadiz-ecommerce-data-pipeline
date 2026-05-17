from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd


def normalize_dt(value: str) -> str:
    value = str(value).strip()
    if len(value) == 8 and value.isdigit():
        return value
    if len(value) == 10 and value[4] == '-' and value[7] == '-':
        return value.replace('-', '')
    parsed = pd.to_datetime(value, errors='coerce')
    if pd.isna(parsed):
        raise ValueError(f'Invalid dt value: {value}')
    return parsed.strftime('%Y%m%d')


def dashed_dt(dt: str) -> str:
    clean = normalize_dt(dt)
    return f'{clean[0:4]}-{clean[4:6]}-{clean[6:8]}'


def to_timestamp(values: Any) -> pd.Series:
    """Athena TIMESTAMP와 호환되도록 timezone-naive datetime64[ns]로 변환합니다.

    Parquet에 timestamp 컬럼을 string으로 저장하면 Athena에서
    BINARY vs timestamp 타입 오류가 발생할 수 있어 여기서 강제 변환합니다.
    """
    if isinstance(values, pd.Series):
        series = values
    else:
        series = pd.Series(values)

    if series.empty:
        return pd.Series(dtype='datetime64[ns]')

    parsed = pd.to_datetime(series, errors='coerce', utc=True)
    try:
        parsed = parsed.dt.tz_convert('Asia/Seoul').dt.tz_localize(None)
    except Exception:
        parsed = pd.to_datetime(series, errors='coerce')
    return parsed.astype('datetime64[ns]')


def now_kst_timestamp() -> pd.Timestamp:
    return pd.Timestamp.utcnow().tz_convert('Asia/Seoul').tz_localize(None)


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
