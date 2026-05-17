from __future__ import annotations

import gzip
import json
import logging
from typing import Any

import pandas as pd

from wd_silver.date_utils import dashed_dt
from wd_silver.io.s3_utils import list_s3_objects, read_s3_bytes

logger = logging.getLogger(__name__)


WRAPPED_LIST_FIELDS = ('data', 'items', 'content', 'result', 'results', 'fundings', 'wishes')


def _parent_context(parsed: dict[str, Any], list_field: str | None = None) -> dict[str, Any]:
    """wrapper JSON의 부모 필드를 child row에 붙이기 위한 context를 만듭니다."""
    context: dict[str, Any] = {}
    for key, value in parsed.items():
        if key == list_field:
            continue
        if isinstance(value, (list, dict)):
            continue
        context[f'_parent_{key}'] = value
    return context


def _rows_from_parsed_json(parsed: Any) -> list[dict[str, Any]]:
    if isinstance(parsed, list):
        return [item if isinstance(item, dict) else {'raw_value': item} for item in parsed]

    if isinstance(parsed, dict):
        for field in WRAPPED_LIST_FIELDS:
            value = parsed.get(field)
            if isinstance(value, list):
                context = _parent_context(parsed, field)
                rows: list[dict[str, Any]] = []
                for item in value:
                    row = item.copy() if isinstance(item, dict) else {'raw_value': item}
                    for k, v in context.items():
                        row.setdefault(k, v)
                    rows.append(row)
                return rows
        # data가 dict인 user_info 같은 구조는 그대로 한 row로 보존합니다.
        return [parsed]

    return [{'raw_value': parsed}]


def _parse_json_payload(payload: bytes, key: str) -> list[dict[str, Any]]:
    if key.endswith('.gz'):
        payload = gzip.decompress(payload)

    text = payload.decode('utf-8', errors='replace').strip()
    if not text:
        return []

    try:
        parsed = json.loads(text)
        return _rows_from_parsed_json(parsed)
    except json.JSONDecodeError:
        pass

    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
            rows.extend(_rows_from_parsed_json(item))
        except json.JSONDecodeError as exc:
            logger.warning('Invalid JSON line. key=%s line_no=%s error=%s', key, line_no, exc)
    return rows


def _candidate_prefixes(bronze_prefix: str, table: str, dt: str) -> list[str]:
    base = bronze_prefix.rstrip('/')
    dashed = dashed_dt(dt)
    return [f'{base}/{table}/dt={dt}/', f'{base}/{table}/dt={dashed}/']


def read_bronze_table_from_s3(*, bucket: str, bronze_prefix: str, table: str, dt: str) -> pd.DataFrame:
    all_rows: list[dict[str, Any]] = []
    files: list[str] = []

    for prefix in _candidate_prefixes(bronze_prefix, table, dt):
        keys = [
            key for key in list_s3_objects(bucket, prefix)
            if key.endswith(('.json', '.jsonl', '.json.gz'))
        ]
        logger.info('Bronze prefix scanned. s3://%s/%s files=%s', bucket, prefix, len(keys))

        for key in keys:
            rows = _parse_json_payload(read_s3_bytes(bucket, key), key)
            for row in rows:
                if not isinstance(row, dict):
                    row = {'raw_value': row}
                row['_source_bucket'] = bucket
                row['_source_s3_key'] = key
                row['_bronze_source_key'] = key
            all_rows.extend(rows)
            files.append(key)

    df = pd.DataFrame(all_rows)
    logger.info('Bronze read completed. table=%s dt=%s files=%s rows=%s', table, dt, len(files), len(df))
    return df
