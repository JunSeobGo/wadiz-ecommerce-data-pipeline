from __future__ import annotations

import logging
from typing import Any, Iterable

import pandas as pd

from wd_silver.date_utils import now_kst_timestamp, normalize_dt, to_timestamp
from wd_silver.null_rules import apply_null_rules
from wd_silver.schemas import TableSchema

logger = logging.getLogger(__name__)


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """원본 컬럼명을 보존하면서 앞뒤 공백만 제거합니다.

    Wadiz Bronze는 camelCase, snake_case, lower-case가 섞여 있어서
    강제로 lower-case로 바꾸지 않고 transform에서 후보 컬럼을 명시합니다.
    """
    if df is None:
        return pd.DataFrame()
    out = df.copy()
    out.columns = [str(c).strip() for c in out.columns]
    return out


def coalesce_columns(df: pd.DataFrame, candidates: Iterable[str], default: Any = None) -> pd.Series:
    if df is None or df.empty:
        return pd.Series(dtype='object')
    result = pd.Series([default] * len(df), index=df.index, dtype='object')
    for column in candidates:
        if column in df.columns:
            result = result.where(result.notna(), df[column])
    return result


def nested_value(df: pd.DataFrame, container_col: str, key: str, default: Any = None) -> pd.Series:
    if container_col not in df.columns:
        return pd.Series([default] * len(df), index=df.index, dtype='object')

    def extract(value: Any) -> Any:
        if isinstance(value, dict):
            return value.get(key, default)
        return default

    return df[container_col].map(extract)


def double_nested_value(df: pd.DataFrame, container_col: str, inner_col: str, key: str, default: Any = None) -> pd.Series:
    if container_col not in df.columns:
        return pd.Series([default] * len(df), index=df.index, dtype='object')

    def extract(value: Any) -> Any:
        if not isinstance(value, dict):
            return default
        inner = value.get(inner_col)
        if isinstance(inner, dict):
            return inner.get(key, default)
        return default

    return df[container_col].map(extract)


def extract_user_id_from_source_key(series: pd.Series) -> pd.Series:
    return series.astype('string').str.extract(r'user_id=([^/]+?)\.json', expand=False)


def _to_bool(series: pd.Series) -> pd.Series:
    def convert(value: Any) -> Any:
        if value is None:
            return pd.NA
        try:
            if pd.isna(value):
                return pd.NA
        except TypeError:
            pass
        if isinstance(value, bool):
            return value
        text = str(value).strip().lower()
        if text in {'true', '1', 'y', 'yes', 't'}:
            return True
        if text in {'false', '0', 'n', 'no', 'f'}:
            return False
        return pd.NA
    return series.map(convert).astype('boolean')


def _to_int(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors='coerce').astype('Int64')


def _to_float(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors='coerce').astype('float64')


def _to_string(series: pd.Series) -> pd.Series:
    return series.astype('string')


def _empty_series(index: pd.Index, dtype_name: str) -> pd.Series:
    normalized = dtype_name.lower()
    if normalized in {'int64', 'bigint', 'int', 'integer'}:
        return pd.Series([pd.NA] * len(index), index=index, dtype='Int64')
    if normalized in {'float64', 'double', 'float'}:
        return pd.Series([pd.NA] * len(index), index=index, dtype='float64')
    if normalized in {'boolean', 'bool'}:
        return pd.Series([pd.NA] * len(index), index=index, dtype='boolean')
    if normalized in {'timestamp', 'datetime', 'datetime64[ns]'}:
        return pd.Series(pd.NaT, index=index, dtype='datetime64[ns]')
    return pd.Series([pd.NA] * len(index), index=index, dtype='string')


def _apply_type(series: pd.Series, dtype_name: str) -> pd.Series:
    normalized = dtype_name.lower()
    if normalized in {'int64', 'bigint', 'int', 'integer'}:
        return _to_int(series)
    if normalized in {'float64', 'double', 'float'}:
        return _to_float(series)
    if normalized in {'boolean', 'bool'}:
        return _to_bool(series)
    if normalized in {'timestamp', 'datetime', 'datetime64[ns]'}:
        return to_timestamp(series)
    return _to_string(series)


def enforce_schema(df: pd.DataFrame, schema: TableSchema, dt: str) -> pd.DataFrame:
    if df is None:
        df = pd.DataFrame()
    out = df.copy()
    dt_clean = normalize_dt(dt)

    if 'silver_processed_at' not in out.columns:
        out['silver_processed_at'] = now_kst_timestamp()
    if 'dt' not in out.columns:
        out['dt'] = dt_clean
    else:
        out['dt'] = out['dt'].fillna(dt_clean).astype('string')

    out = apply_null_rules(out)

    for column in schema.columns:
        if column not in out.columns:
            dtype_name = schema.dtype_map.get(column, 'string')
            out[column] = _empty_series(out.index, dtype_name)

    for column in schema.columns:
        dtype_name = schema.dtype_map.get(column, 'string')
        out[column] = _apply_type(out[column], dtype_name)

    out['dt'] = out['dt'].fillna(dt_clean).astype('string')

    before = len(out)
    if schema.dedup_keys and all(key in out.columns for key in schema.dedup_keys):
        out = out.drop_duplicates(subset=schema.dedup_keys, keep='last')
    logger.info('Dedup completed. table=%s before=%s after=%s removed=%s', schema.table, before, len(out), before - len(out))

    if schema.sort_keys and all(key in out.columns for key in schema.sort_keys):
        out = out.sort_values(schema.sort_keys, kind='mergesort')

    return out[schema.columns].reset_index(drop=True)
