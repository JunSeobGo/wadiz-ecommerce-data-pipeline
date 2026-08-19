"""파생 컬럼 로직의 경계값/분기 테스트 (fundings, wishes 중심)."""

from __future__ import annotations

import pandas as pd
import pytest
from helpers import DT, RAW_USER_ID, make_bronze

from wd_silver.transforms import fundings, wishes


@pytest.mark.parametrize(
    "amount,expected_tier",
    [
        (0, "unknown"),
        (29_999, "under_30k"),
        (30_000, "30k_100k"),
        (100_000, "100k_300k"),
        (300_000, "over_300k"),
    ],
)
def test_fundings_amount_tier_boundaries(amount, expected_tier):
    out = fundings.transform(make_bronze("fundings", amount=amount), dt=DT)
    assert out["amount_tier"].iloc[0] == expected_tier


@pytest.mark.parametrize(
    "product_type,expected_action",
    [
        ("REWARD", "funding"),
        ("PREORDER", "funding"),
        ("FUNDING", "funding"),
        ("STORE", "store"),
    ],
)
def test_fundings_action_type_normalization(product_type, expected_action):
    out = fundings.transform(make_bronze("fundings", productType=product_type), dt=DT)
    assert out["action_type"].iloc[0] == expected_action


def test_fundings_camel_and_snake_case_equivalent():
    base = {"userId": RAW_USER_ID, "amount": 50_000, "createdAt": "2026-05-19T09:00:00"}
    snake = fundings.transform(pd.DataFrame([{**base, "campaign_id": 1001}]), dt=DT)
    camel = fundings.transform(pd.DataFrame([{**base, "campaignId": 1001}]), dt=DT)
    assert snake["campaign_id"].iloc[0] == camel["campaign_id"].iloc[0] == 1001


@pytest.mark.parametrize("end_yn,expected_active", [(0, True), (1, False)])
def test_wishes_is_active_from_end_yn(end_yn, expected_active):
    out = wishes.transform(make_bronze("wishes", endYn=end_yn), dt=DT)
    assert bool(out["is_active_at_snapshot"].iloc[0]) == expected_active


@pytest.mark.parametrize("remaining_day,expected_active", [(-1, False), (5, True)])
def test_wishes_is_active_fallback_to_remaining_day(remaining_day, expected_active):
    # endYn이 없으면 remaining_day >= 0 으로 판단
    base = {
        "userId": RAW_USER_ID,
        "campaign_id": 1001,
        "snapshotAt": "2026-05-19T00:00:00",
        "remainingDay": remaining_day,
    }
    out = wishes.transform(pd.DataFrame([base]), dt=DT)
    assert bool(out["is_active_at_snapshot"].iloc[0]) == expected_active
