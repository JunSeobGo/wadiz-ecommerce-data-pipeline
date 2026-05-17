from __future__ import annotations

import pendulum


def compact_dt_from_context(context: dict) -> str:
    """Airflow logical date를 YYYYMMDD로 변환합니다."""
    logical_date = context.get('logical_date') or context.get('data_interval_start') or pendulum.now('Asia/Seoul')
    if isinstance(logical_date, str):
        logical_date = pendulum.parse(logical_date)
    return logical_date.in_timezone('Asia/Seoul').format('YYYYMMDD')
