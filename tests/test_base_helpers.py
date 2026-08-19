"""base.py 순수 헬퍼 테스트."""

from __future__ import annotations

import pandas as pd

from wd_silver.transforms.base import (
    _to_bool,
    _to_int,
    coalesce_columns,
    extract_user_id_from_source_key,
    nested_value,
)


def test_coalesce_picks_first_non_null_per_cell():
    df = pd.DataFrame({"a": [None, "x"], "b": ["y", None]})
    result = coalesce_columns(df, ["a", "b"])
    assert list(result) == ["y", "x"]


def test_coalesce_missing_columns_returns_default():
    df = pd.DataFrame({"a": [1, 2]})
    result = coalesce_columns(df, ["nope1", "nope2"], default="d")
    assert list(result) == ["d", "d"]


def test_coalesce_empty_df_returns_empty():
    result = coalesce_columns(pd.DataFrame(), ["a"])
    assert len(result) == 0


def test_to_int_coerces_and_nulls_invalid():
    result = _to_int(pd.Series(["3", "abc", None]))
    assert result[0] == 3
    assert pd.isna(result[1])
    assert pd.isna(result[2])
    assert str(result.dtype) == "Int64"


def test_to_bool_recognizes_variants():
    result = _to_bool(pd.Series(["yes", "0", "maybe", None]))
    assert bool(result[0]) is True
    assert bool(result[1]) is False
    assert pd.isna(result[2])  # 인식 불가 값 → NA
    assert pd.isna(result[3])  # None → NA


def test_nested_value_extracts_key_from_dict():
    df = pd.DataFrame({"data": [{"x": 1}, {"y": 2}, "not-a-dict"]})
    result = nested_value(df, "data", "x")
    assert result[0] == 1
    assert pd.isna(result[1])  # 다른 key만 있는 dict → 기본값(None/NaN)
    assert pd.isna(result[2])  # dict가 아님 → 기본값


def test_nested_value_missing_container_returns_default():
    df = pd.DataFrame({"other": [1]})
    result = nested_value(df, "data", "x", default="d")
    assert list(result) == ["d"]


def test_extract_user_id_from_source_key():
    series = pd.Series(
        ["bronze/user_info/user_id=abc123.json", "no-match-here"]
    )
    result = extract_user_id_from_source_key(series)
    assert result[0] == "abc123"
    assert pd.isna(result[1])
