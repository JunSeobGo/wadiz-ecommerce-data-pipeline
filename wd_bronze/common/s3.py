from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Iterable

import boto3


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def current_hour_utc() -> str:
    return datetime.now(timezone.utc).strftime('%H')


def current_ts_utc() -> str:
    return datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')


def table_prefix(bronze_prefix: str, table: str, dt: str, *, with_hour: bool = True) -> str:
    base = f"{bronze_prefix.strip('/')}/{table}/dt={dt}"
    if with_hour:
        return f"{base}/hour={current_hour_utc()}"
    return base


def put_json(bucket: str, key: str, payload: Any) -> str:
    boto3.client('s3').put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(payload, ensure_ascii=False, default=str).encode('utf-8'),
        ContentType='application/json; charset=utf-8',
    )
    return f's3://{bucket}/{key}'


def write_records(bucket: str, bronze_prefix: str, table: str, dt: str, records: list[dict[str, Any]], name: str = 'part') -> str | None:
    """Bronze row list를 dt/hour partition 아래에 저장합니다.

    Silver reader가 list JSON을 펼칠 수 있으므로, 테이블별 row list를 그대로 보존합니다.
    """
    if not records:
        return None
    key = f"{table_prefix(bronze_prefix, table, dt)}/{name}_{current_ts_utc()}.json"
    return put_json(bucket, key, records)


def write_payload(bucket: str, bronze_prefix: str, table: str, dt: str, payload: dict[str, Any], name: str) -> str:
    """fundings/wishes/user_info처럼 wrapper dict를 저장하는 경우 사용합니다."""
    key = f"{table_prefix(bronze_prefix, table, dt)}/{name}_{current_ts_utc()}.json"
    return put_json(bucket, key, payload)


def list_json_keys(bucket: str, prefix: str) -> list[str]:
    s3 = boto3.client('s3')
    paginator = s3.get_paginator('list_objects_v2')
    keys: list[str] = []
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get('Contents', []):
            key = obj['Key']
            if key.endswith(('.json', '.jsonl', '.json.gz')):
                keys.append(key)
    return keys


def read_json(bucket: str, key: str) -> Any:
    body = boto3.client('s3').get_object(Bucket=bucket, Key=key)['Body'].read().decode('utf-8')
    return json.loads(body)


def iter_json_objects(bucket: str, keys: Iterable[str]) -> Iterable[Any]:
    for key in keys:
        try:
            yield read_json(bucket, key)
        except Exception:
            continue
