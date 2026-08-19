"""error_rate 임계치 차단 로직 테스트."""

from __future__ import annotations

import pytest

from wd_silver.config import get_config
from wd_silver.quality.validators import error_rate, exceeds_error_threshold


@pytest.mark.parametrize(
    "metrics,expected",
    [
        ({"input_rows": 0, "error_rows": 0}, 0.0),   # 빈 입력 → 0
        ({"input_rows": 10, "error_rows": 0}, 0.0),  # 전부 정상
        ({"input_rows": 10, "error_rows": 5}, 0.5),  # 절반 오류
        ({"input_rows": 4, "error_rows": 1}, 0.25),
        ({}, 0.0),                                   # 키 없음 → 0
    ],
)
def test_error_rate_computation(metrics, expected):
    assert error_rate(metrics) == expected


def test_threshold_is_strictly_greater():
    # 정확히 임계치와 같으면 통과(초과 아님)
    assert exceeds_error_threshold({"input_rows": 10, "error_rows": 5}, 0.5) is False
    # 임계치를 넘으면 차단
    assert exceeds_error_threshold({"input_rows": 10, "error_rows": 6}, 0.5) is True


def test_threshold_disabled_when_negative():
    # 음수 임계치는 검사 비활성화
    assert exceeds_error_threshold({"input_rows": 10, "error_rows": 10}, -1) is False


def test_no_errors_never_exceeds():
    assert exceeds_error_threshold({"input_rows": 100, "error_rows": 0}, 0.0) is False


def test_config_default_max_error_rate(monkeypatch):
    # 기본 임계치는 0.5 (환경변수 미설정 시)
    monkeypatch.delenv("SILVER_MAX_ERROR_RATE", raising=False)
    assert get_config().max_error_rate == 0.5


def test_config_reads_max_error_rate_from_env(monkeypatch):
    monkeypatch.setenv("SILVER_MAX_ERROR_RATE", "0.2")
    assert get_config().max_error_rate == 0.2
