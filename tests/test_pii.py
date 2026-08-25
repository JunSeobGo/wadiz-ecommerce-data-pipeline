"""pii.py 해싱 테스트: 결정성 + salt 민감성 + None 처리."""

from __future__ import annotations

import pandas as pd

from wd_silver.pii import hash_series, hash_value


def test_hash_none_and_empty_returns_none():
    assert hash_value(None) is None
    assert hash_value("") is None
    assert hash_value("   ") is None
    assert hash_value(pd.NA) is None


def test_hash_is_deterministic_and_strips():
    assert hash_value("u1", salt="s") == hash_value("u1", salt="s")
    # 앞뒤 공백은 제거 후 해싱되므로 같은 결과
    assert hash_value(" u1 ", salt="s") == hash_value("u1", salt="s")


def test_hash_salt_changes_output():
    assert hash_value("u1", salt="a") != hash_value("u1", salt="b")


def test_hash_series_matches_elementwise():
    series = pd.Series(["u1", "u1", None, ""])
    hashed = hash_series(series, salt="a")
    assert hashed[0] == hashed[1]
    # pandas 버전에 따라 None 또는 NaN이 될 수 있어 pd.isna로 검사
    assert pd.isna(hashed[2])
    assert pd.isna(hashed[3])
    # salt가 다르면 값이 달라진다
    assert hashed[0] != hash_series(series, salt="b")[0]
