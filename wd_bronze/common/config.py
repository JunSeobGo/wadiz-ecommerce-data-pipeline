from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class BronzeConfig:
    """Bronze crawler 공통 설정.

    Airflow → ECS Fargate 실행 시 환경변수로 주입되는 값을 한곳에서 읽습니다.
    민감정보를 코드에 박아두지 않기 위해 S3 bucket/prefix/limit은 모두 env 기반으로 관리합니다.
    """

    aws_region: str
    s3_bucket: str
    bronze_prefix: str
    table: str | None
    dt: str | None
    request_timeout: int
    page_sleep_sec: float
    max_pages: int | None
    max_records: int | None
    source_base_url: str
    source_preorder_search_url: str


def _optional_int(name: str) -> int | None:
    raw = os.getenv(name, '').strip()
    if raw == '' or raw.lower() in {'none', 'null', '0'}:
        return None
    return int(raw)


def _optional_float(name: str, default: float) -> float:
    raw = os.getenv(name, '').strip()
    if raw == '':
        return default
    return float(raw)


def get_bronze_config(table: str | None = None, dt: str | None = None) -> BronzeConfig:
    return BronzeConfig(
        aws_region=os.getenv('AWS_REGION', 'ap-northeast-2'),
        s3_bucket=os.getenv('S3_BUCKET', 'wd-data-lake'),
        bronze_prefix=os.getenv('BRONZE_PREFIX', 'bronze/wadiz').strip('/'),
        table=table or os.getenv('TABLE'),
        dt=(dt or os.getenv('DT') or '').replace('-', '') or None,
        request_timeout=int(os.getenv('BRONZE_REQUEST_TIMEOUT', '20')),
        page_sleep_sec=_optional_float('BRONZE_PAGE_SLEEP_SEC', 0.25),
        max_pages=_optional_int('BRONZE_MAX_PAGES'),
        max_records=_optional_int('BRONZE_MAX_RECORDS'),
        source_base_url=os.getenv('SOURCE_BASE_URL', 'https://example.invalid').rstrip('/'),
        source_preorder_search_url=os.getenv('SOURCE_PREORDER_SEARCH_URL', 'https://example.invalid/api/search/v2/preorder'),
    )


def table_max_pages(table: str, fallback: int | None) -> int | None:
    raw = os.getenv(f'BRONZE_{table.upper()}_MAX_PAGES', '').strip()
    if raw == '' or raw.lower() in {'none', 'null', '0'}:
        return fallback
    return int(raw)


def table_max_records(table: str, fallback: int | None) -> int | None:
    raw = os.getenv(f'BRONZE_{table.upper()}_MAX_RECORDS', '').strip()
    if raw == '' or raw.lower() in {'none', 'null', '0'}:
        return fallback
    return int(raw)


def csv_env(name: str) -> list[str]:
    raw = os.getenv(name, '').strip()
    if not raw:
        return []
    return [item.strip() for item in raw.split(',') if item.strip()]
