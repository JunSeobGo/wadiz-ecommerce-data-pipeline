"""모든 Silver transform이 공통으로 지켜야 하는 불변식(계약) 테스트.

6개 테이블에 parametrize로 일괄 적용한다.
"""

from __future__ import annotations

import pandas as pd
import pytest
from helpers import ALL_TABLES, DT, HASH_COLUMN, RAW_USER_ID, TRANSFORMS, make_bronze

from wd_silver.schemas import get_schema


@pytest.mark.parametrize("table", ALL_TABLES)
def test_output_columns_exactly_match_schema(table):
    out = TRANSFORMS[table](make_bronze(table), dt=DT)
    assert list(out.columns) == get_schema(table).columns


@pytest.mark.parametrize("table", ALL_TABLES)
def test_dt_partition_column_filled(table):
    out = TRANSFORMS[table](make_bronze(table, rows=2), dt=DT)
    assert (out["dt"] == DT).all()


@pytest.mark.parametrize("table", ALL_TABLES)
def test_empty_input_returns_empty_with_schema(table):
    out = TRANSFORMS[table](pd.DataFrame(), dt=DT)
    assert list(out.columns) == get_schema(table).columns
    assert len(out) == 0


@pytest.mark.parametrize("table", list(HASH_COLUMN))
def test_pii_raw_user_id_removed(table):
    out = TRANSFORMS[table](make_bronze(table), dt=DT)
    hash_col = HASH_COLUMN[table]
    # 해시는 생성되고
    assert out[hash_col].notna().all()
    # 원본 user id 문자열은 출력 어디에도 없어야 한다(모든 셀을 안전하게 문자열화해 검사)
    flat = out.astype(str).to_numpy().ravel()
    assert not any(RAW_USER_ID in str(cell) for cell in flat)


@pytest.mark.parametrize("table", list(HASH_COLUMN))
def test_identical_rows_deduplicated(table):
    out = TRANSFORMS[table](make_bronze(table, rows=3), dt=DT)
    assert len(out) == 1
