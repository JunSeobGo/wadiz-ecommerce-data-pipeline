from __future__ import annotations

import json
import os
from typing import Any

import boto3

from wd_bronze.common.logging_utils import setup_logging

logger = setup_logging("wd_bronze.common.source_ids")


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)

    if raw is None or str(raw).strip() == "":
        return default

    try:
        value = int(raw)
    except ValueError:
        logger.warning(
            "환경변수 int 변환 실패. default 사용. name=%s raw=%s default=%s",
            name,
            raw,
            default,
        )
        return default

    if value <= 0:
        logger.warning(
            "환경변수 값이 0 이하입니다. default 사용. name=%s raw=%s default=%s",
            name,
            raw,
            default,
        )
        return default

    return value


def _read_json_from_s3(s3, bucket: str, key: str) -> Any:
    obj = s3.get_object(Bucket=bucket, Key=key)
    body = obj["Body"].read()
    return json.loads(body)


def _iter_json_keys(
    bucket: str,
    prefix: str,
    *,
    max_files: int | None = None,
):
    s3 = boto3.client("s3")
    paginator = s3.get_paginator("list_objects_v2")

    files_seen = 0

    logger.info(
        "S3 JSON 파일 스캔 시작. bucket=%s prefix=%s max_files=%s",
        bucket,
        prefix,
        max_files,
    )

    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        contents = page.get("Contents", [])

        if not contents:
            logger.info(
                "S3 JSON 파일 없음. bucket=%s prefix=%s",
                bucket,
                prefix,
            )

        for obj in contents:
            key = obj.get("Key", "")

            if not key.endswith(".json"):
                continue

            files_seen += 1
            yield key

            if max_files is not None and files_seen >= max_files:
                logger.info(
                    "S3 JSON 파일 max_files 도달. bucket=%s prefix=%s files_seen=%s max_files=%s",
                    bucket,
                    prefix,
                    files_seen,
                    max_files,
                )
                return

    logger.info(
        "S3 JSON 파일 스캔 완료. bucket=%s prefix=%s files_seen=%s",
        bucket,
        prefix,
        files_seen,
    )


def _normalize_records(payload: Any) -> list[dict[str, Any]]:
    """
    JSON payload를 row list로 정규화.

    지원 구조:
    1. [row, row, ...]
    2. {"records": [...]}
    3. {"data": [...]}
    4. {"rows": [...]}
    5. {"items": [...]}
    6. 단일 dict row
    """

    if payload is None:
        return []

    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]

    if isinstance(payload, dict):
        for key in ("records", "data", "rows", "items", "content", "projectList"):
            value = payload.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]

        return [payload]

    return []


def _extract_campaign_id(row: dict[str, Any]) -> int | None:
    candidates: list[Any] = []

    for key in (
        "campaignId",
        "campaign_id",
        "projectId",
        "project_id",
        "id",
    ):
        candidates.append(row.get(key))

    raw = row.get("raw") or row.get("raw_text") or row.get("data")

    if isinstance(raw, dict):
        for key in (
            "campaignId",
            "campaign_id",
            "projectId",
            "project_id",
            "id",
        ):
            candidates.append(raw.get(key))

    for value in candidates:
        if value is None:
            continue

        try:
            return int(value)
        except (TypeError, ValueError):
            continue

    return None


def load_campaign_ids_from_preorder(
    bucket: str,
    bronze_prefix: str,
    dt: str,
) -> list[int]:
    """
    preorder Bronze에서 campaign_id 목록을 로드한다.

    읽는 위치:
    s3://{bucket}/{bronze_prefix}/preorder/dt={dt}/

    hour=HH 하위 경로가 있어도 Prefix 하위 전체를 읽는다.
    """

    dt = str(dt).replace("-", "")
    prefix = f"{bronze_prefix.rstrip('/')}/preorder/dt={dt}/"

    max_files = _int_env("SOURCE_IDS_PREORDER_MAX_FILES", 1000)

    s3 = boto3.client("s3")
    campaign_ids: set[int] = set()

    files_read = 0
    files_error = 0
    rows_read = 0
    rows_without_campaign_id = 0

    logger.info(
        "preorder campaign_id 로딩 시작. bucket=%s prefix=%s max_files=%s",
        bucket,
        prefix,
        max_files,
    )

    for key in _iter_json_keys(bucket, prefix, max_files=max_files):
        try:
            payload = _read_json_from_s3(s3, bucket, key)
            records = _normalize_records(payload)

            files_read += 1
            rows_read += len(records)

            found_in_file = 0

            for row in records:
                campaign_id = _extract_campaign_id(row)

                if campaign_id is not None:
                    campaign_ids.add(campaign_id)
                    found_in_file += 1
                else:
                    rows_without_campaign_id += 1

            logger.info(
                "preorder campaign_id 파일 처리 완료. key=%s records=%s found_in_file=%s total_campaign_ids=%s",
                key,
                len(records),
                found_in_file,
                len(campaign_ids),
            )

        except Exception as e:
            files_error += 1
            logger.exception(
                "preorder campaign_id 파일 처리 실패. key=%s error=%s",
                key,
                e,
            )
            continue

    logger.info(
        "preorder campaign_id 로딩 완료. bucket=%s prefix=%s campaign_ids=%s files_read=%s files_error=%s rows_read=%s rows_without_campaign_id=%s",
        bucket,
        prefix,
        len(campaign_ids),
        files_read,
        files_error,
        rows_read,
        rows_without_campaign_id,
    )

    return sorted(campaign_ids)


def _extract_user_id_from_supporter_row(row: dict[str, Any]) -> str | None:
    """
    supporter row에서 fundings/wishes/user_info 호출용 user_id 추출.

    현재 supporter Bronze 구조:
    {
      "campaign_id": 356585,
      "raw_text": {
        "encUserId": "5409679515",
        ...
      },
      "status": "success"
    }
    """

    candidates: list[Any] = []

    raw_text = row.get("raw_text")
    raw = row.get("raw")
    data = row.get("data")

    if isinstance(raw_text, dict):
        for key in (
            "encUserId",
            "userId",
            "user_id",
            "enc_user_id",
            "supporterId",
            "supporter_id",
            "memberId",
            "member_id",
        ):
            candidates.append(raw_text.get(key))

    if isinstance(raw, dict):
        for key in (
            "encUserId",
            "userId",
            "user_id",
            "enc_user_id",
            "supporterId",
            "supporter_id",
            "memberId",
            "member_id",
        ):
            candidates.append(raw.get(key))

    if isinstance(data, dict):
        for key in (
            "encUserId",
            "userId",
            "user_id",
            "enc_user_id",
            "supporterId",
            "supporter_id",
            "memberId",
            "member_id",
        ):
            candidates.append(data.get(key))

    for key in (
        "encUserId",
        "user_id",
        "userId",
        "enc_user_id",
        "supporterId",
        "supporter_id",
        "memberId",
        "member_id",
    ):
        candidates.append(row.get(key))

    for value in candidates:
        if value is None:
            continue

        value = str(value).strip()

        if not value:
            continue

        if value.lower() in ("none", "null", "nan"):
            continue

        return value

    return None


def load_user_ids_from_supporter(
    bucket: str,
    bronze_prefix: str,
    dt: str,
) -> list[str]:
    """
    supporter Bronze chunk 파일에서 encUserId 목록을 로드한다.

    읽는 위치:
    s3://{bucket}/{bronze_prefix}/supporter/dt={dt}/

    partial 실행 지원:
    - supporter 전체 수집이 끝나지 않아도 이미 저장된 part 파일만 읽는다.
    - hour=HH 하위 경로도 읽는다.
    - SOURCE_IDS_MAX_FILES로 읽을 파일 수 제한.
    - SOURCE_IDS_MAX_USER_IDS로 user_id 수 제한.
    """

    dt = str(dt).replace("-", "")
    prefix = f"{bronze_prefix.rstrip('/')}/supporter/dt={dt}/"

    max_files = _int_env("SOURCE_IDS_MAX_FILES", 50)
    max_user_ids = _int_env("SOURCE_IDS_MAX_USER_IDS", 500)

    s3 = boto3.client("s3")
    user_ids: set[str] = set()

    files_read = 0
    files_error = 0
    rows_read = 0
    rows_without_user_id = 0

    logger.info(
        "supporter user_id 로딩 시작. bucket=%s prefix=%s max_files=%s max_user_ids=%s",
        bucket,
        prefix,
        max_files,
        max_user_ids,
    )

    for key in _iter_json_keys(bucket, prefix, max_files=max_files):
        try:
            payload = _read_json_from_s3(s3, bucket, key)
            records = _normalize_records(payload)

            files_read += 1
            rows_read += len(records)

            found_in_file = 0

            for row in records:
                user_id = _extract_user_id_from_supporter_row(row)

                if user_id:
                    user_ids.add(user_id)
                    found_in_file += 1
                else:
                    rows_without_user_id += 1

                if len(user_ids) >= max_user_ids:
                    logger.info(
                        "supporter user_id max_user_ids 도달. users=%s files_read=%s rows_read=%s last_key=%s",
                        len(user_ids),
                        files_read,
                        rows_read,
                        key,
                    )
                    return sorted(user_ids)

            logger.info(
                "supporter user_id 파일 처리 완료. key=%s records=%s found_in_file=%s total_users=%s",
                key,
                len(records),
                found_in_file,
                len(user_ids),
            )

        except Exception as e:
            files_error += 1
            logger.exception(
                "supporter user_id 파일 처리 실패. key=%s error=%s",
                key,
                e,
            )
            continue

    logger.info(
        "supporter user_id 로딩 완료. bucket=%s prefix=%s users=%s files_read=%s files_error=%s rows_read=%s rows_without_user_id=%s",
        bucket,
        prefix,
        len(user_ids),
        files_read,
        files_error,
        rows_read,
        rows_without_user_id,
    )

    return sorted(user_ids)