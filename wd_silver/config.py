from __future__ import annotations

import os
from dataclasses import dataclass


def env(name: str, default: str | None = None, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and (value is None or str(value).strip() == ''):
        raise ValueError(f'Missing required environment variable: {name}')
    return str(value or '')


def env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or str(raw).strip() == '':
        return default
    try:
        return float(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class SilverConfig:
    aws_region: str
    s3_bucket: str
    bronze_prefix: str
    silver_prefix: str
    silver_error_prefix: str
    hash_salt: str
    allow_empty: bool
    write_error_rows: bool
    # error 행 비율이 이 값을 넘으면 Silver를 실패시켜 오염 데이터가 Gold로 넘어가지 않게 한다.
    max_error_rate: float


def get_config() -> SilverConfig:
    return SilverConfig(
        aws_region=env('AWS_REGION', 'ap-northeast-2'),
        s3_bucket=env('S3_BUCKET', 'wd-data-lake'),
        bronze_prefix=env('BRONZE_PREFIX', 'bronze/wadiz'),
        silver_prefix=env('SILVER_PREFIX', 'silver2/wadiz'),
        silver_error_prefix=env('SILVER_ERROR_PREFIX', env('ERROR_PREFIX', 'silver_error/wadiz')),
        hash_salt=env('SILVER_HASH_SALT', ''),
        allow_empty=env('SILVER_ALLOW_EMPTY', 'false').lower() == 'true',
        write_error_rows=env('SILVER_WRITE_ERROR_ROWS', 'true').lower() == 'true',
        max_error_rate=env_float('SILVER_MAX_ERROR_RATE', 0.5),
    )
