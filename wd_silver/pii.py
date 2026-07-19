from __future__ import annotations

import hashlib

import pandas as pd


def hash_value(value: object, salt: str = '') -> str | None:
    if value is None or pd.isna(value):
        return None
    normalized = str(value).strip()
    if normalized == '':
        return None
    return hashlib.sha256(f'{salt}:{normalized}'.encode('utf-8')).hexdigest()


def hash_series(series: pd.Series, salt: str = '') -> pd.Series:
    return series.apply(lambda value: hash_value(value, salt=salt))
