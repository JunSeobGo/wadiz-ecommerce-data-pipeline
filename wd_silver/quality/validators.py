from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd

from wd_silver.schemas import TableSchema

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    valid_df: pd.DataFrame
    error_df: pd.DataFrame
    metrics: dict


def validate_required_keys(df: pd.DataFrame, schema: TableSchema) -> pd.Series:
    if df.empty:
        return pd.Series([], dtype=bool)
    invalid = pd.Series(False, index=df.index)
    for key in schema.required_keys:
        if key not in df.columns:
            logger.error('Required key is missing. table=%s key=%s', schema.table, key)
            invalid = pd.Series(True, index=df.index)
            continue
        invalid = invalid | df[key].isna() | (df[key].astype(str).str.strip() == '')
    return invalid


def split_valid_and_error_rows(df: pd.DataFrame, schema: TableSchema) -> ValidationResult:
    metrics = {'input_rows': int(len(df)), 'required_keys': schema.required_keys}
    if df.empty:
        metrics.update({'valid_rows': 0, 'error_rows': 0})
        return ValidationResult(df.copy(), df.copy(), metrics)
    invalid = validate_required_keys(df, schema)
    error_df = df.loc[invalid].copy()
    valid_df = df.loc[~invalid].copy()
    if not error_df.empty:
        error_df['_silver_error_reason'] = 'missing_required_key'
    metrics.update({'valid_rows': int(len(valid_df)), 'error_rows': int(len(error_df))})
    logger.info('Validation completed. table=%s metrics=%s', schema.table, metrics)
    return ValidationResult(valid_df, error_df, metrics)


def log_quality_metrics(df: pd.DataFrame, schema: TableSchema) -> dict:
    duplicate_count = None
    if schema.dedup_keys and all(k in df.columns for k in schema.dedup_keys):
        duplicate_count = int(df.duplicated(subset=schema.dedup_keys).sum())
    metrics = {
        'rows': int(len(df)),
        'columns': list(df.columns),
        'null_counts': {c: int(df[c].isna().sum()) for c in df.columns},
        'duplicate_count_before_dedup': duplicate_count,
    }
    logger.info('Quality metrics. table=%s metrics=%s', schema.table, metrics)
    return metrics
