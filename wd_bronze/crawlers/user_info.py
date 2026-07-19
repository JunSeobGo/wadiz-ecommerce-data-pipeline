from __future__ import annotations

import os
import time
from typing import Any

from wd_bronze.common.config import (
    csv_env,
    get_bronze_config,
    table_max_records,
)
from wd_bronze.common.http import make_session
from wd_bronze.common.logging_utils import setup_logging
from wd_bronze.common.s3 import now_utc_iso, write_payload
from wd_bronze.common.source_ids import load_user_ids_from_supporter

logger = setup_logging("wd_bronze.crawlers.user_info")


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


def fetch_user_info(
    session,
    user_id: str,
    *,
    timeout: int,
) -> dict[str, Any] | None:
    base_url = os.getenv('SOURCE_BASE_URL', 'https://example.invalid').rstrip('/')
    url = f'{base_url}/web/supporter/{user_id}/info'

    logger.info(
        "user_info fetch start. user_id=%s url=%s",
        user_id,
        url,
    )

    try:
        response = session.get(url, timeout=timeout)
    except Exception as e:
        logger.exception(
            "user_info API 요청 예외. user_id=%s error=%s",
            user_id,
            e,
        )
        return None

    if response.status_code != 200:
        logger.warning(
            "user_info API 실패. user_id=%s status=%s body_head=%s",
            user_id,
            response.status_code,
            response.text[:500],
        )
        return None

    try:
        payload = response.json()
    except Exception as e:
        logger.exception(
            "user_info JSON 파싱 실패. user_id=%s error=%s body_head=%s",
            user_id,
            e,
            response.text[:500],
        )
        return None

    data = payload.get("data", {})

    if not isinstance(data, dict):
        logger.warning(
            "user_info data 타입 이상. user_id=%s data_type=%s",
            user_id,
            type(data).__name__,
        )
        return None

    return data


def run(dt: str) -> dict[str, Any]:
    cfg = get_bronze_config(table="user_info", dt=dt)

    # 기존 max_records는 saved_files 기준으로 쓰고 있었음.
    # 여기서는 최대 저장 user 수로 사용.
    max_users = table_max_records("user_info", cfg.max_records)

    chunk_users = _int_env("USER_INFO_CHUNK_USERS", 100)

    logger.info(
        "BRONZE_PREP table=user_info dt=%s bucket=%s prefix=%s max_users=%s chunk_users=%s",
        dt,
        cfg.s3_bucket,
        cfg.bronze_prefix,
        max_users,
        chunk_users,
    )

    user_ids = csv_env("BRONZE_USER_IDS")

    logger.info(
        "user_info BRONZE_USER_IDS env 로딩 완료. users=%s",
        len(user_ids),
    )

    if not user_ids:
        logger.info(
            "user_info user_id를 supporter Bronze에서 로딩 시작. supporter_prefix=s3://%s/%s/supporter/dt=%s/",
            cfg.s3_bucket,
            cfg.bronze_prefix.rstrip("/"),
            dt,
        )

        user_ids = load_user_ids_from_supporter(
            cfg.s3_bucket,
            cfg.bronze_prefix,
            dt,
        )

        logger.info(
            "user_info user_id를 supporter Bronze에서 로딩 완료. users=%s sample=%s",
            len(user_ids),
            user_ids[:5],
        )

    logger.info(
        "BRONZE_START table=user_info dt=%s users=%s max_users=%s chunk_users=%s",
        dt,
        len(user_ids),
        max_users,
        chunk_users,
    )

    if not user_ids:
        raise RuntimeError(
            f"user_info 수집용 user_id가 없습니다. supporter Bronze를 먼저 확인하세요. "
            f"s3://{cfg.s3_bucket}/{cfg.bronze_prefix.rstrip('/')}/supporter/dt={dt}/"
        )

    session = make_session()

    buffer: list[dict[str, Any]] = []
    outputs: list[str] = []

    processed_users = 0
    saved_users = 0
    empty_users = 0
    error_users = 0
    part_no = 0

    def flush_buffer(reason: str) -> None:
        nonlocal buffer, part_no, outputs

        if not buffer:
            logger.info(
                "BRONZE_FLUSH_SKIP table=user_info dt=%s part=%s reason=%s buffer_users=0",
                dt,
                part_no,
                reason,
            )
            return

        part_name = f"user_info_part_{part_no:05d}"

        part_users = len(buffer)

        logger.info(
            "BRONZE_FLUSH_START table=user_info dt=%s part=%s users=%s reason=%s",
            dt,
            part_no,
            part_users,
            reason,
        )

        uri = write_payload(
            cfg.s3_bucket,
            cfg.bronze_prefix,
            "user_info",
            dt,
            buffer,
            name=part_name,
        )

        outputs.append(uri)

        logger.info(
            "BRONZE_PART_WRITTEN table=user_info dt=%s part=%s users=%s output=%s reason=%s",
            dt,
            part_no,
            part_users,
            uri,
            reason,
        )

        buffer.clear()
        part_no += 1

    for idx, user_id in enumerate(user_ids, start=1):
        if max_users is not None and saved_users >= max_users:
            logger.info(
                "user_info max_users 도달. saved_users=%s max_users=%s",
                saved_users,
                max_users,
            )
            break

        try:
            processed_users += 1

            data = fetch_user_info(
                session,
                user_id,
                timeout=cfg.request_timeout,
            )

            if data is None:
                empty_users += 1

                logger.info(
                    "user_info empty. idx=%s/%s user_id=%s processed_users=%s saved_users=%s empty_users=%s error_users=%s",
                    idx,
                    len(user_ids),
                    user_id,
                    processed_users,
                    saved_users,
                    empty_users,
                    error_users,
                )

                time.sleep(cfg.page_sleep_sec)
                continue

            payload = {
                "collected_at": now_utc_iso(),
                "user_id": user_id,
                "data": data,
            }

            buffer.append(payload)
            saved_users += 1

            logger.info(
                "BRONZE_PROGRESS table=user_info dt=%s idx=%s/%s user_id=%s buffer_users=%s processed_users=%s saved_users=%s empty_users=%s error_users=%s parts_written=%s",
                dt,
                idx,
                len(user_ids),
                user_id,
                len(buffer),
                processed_users,
                saved_users,
                empty_users,
                error_users,
                part_no,
            )

            if len(buffer) >= chunk_users:
                flush_buffer(reason="chunk_users_reached")

            time.sleep(cfg.page_sleep_sec)

        except Exception as e:
            error_users += 1

            logger.exception(
                "user_info user 처리 중 예외 발생. idx=%s/%s user_id=%s error=%s",
                idx,
                len(user_ids),
                user_id,
                e,
            )

            continue

    flush_buffer(reason="final_buffer")

    logger.info(
        "BRONZE_RESULT table=user_info dt=%s input_users=%s processed_users=%s saved_users=%s empty_users=%s error_users=%s parts=%s outputs=%s",
        dt,
        len(user_ids),
        processed_users,
        saved_users,
        empty_users,
        error_users,
        part_no,
        len(outputs),
    )

    if saved_users <= 0:
        raise RuntimeError(
            f"user_info Bronze 저장 user가 0명입니다. "
            f"dt={dt}, input_users={len(user_ids)}, processed_users={processed_users}, "
            f"empty_users={empty_users}, error_users={error_users}"
        )

    if not outputs:
        raise RuntimeError(
            f"user_info Bronze S3 output이 없습니다. dt={dt}, saved_users={saved_users}"
        )

    return {
        "table": "user_info",
        "dt": dt,
        "input_users": len(user_ids),
        "processed_users": processed_users,
        "users": saved_users,
        "empty_users": empty_users,
        "error_users": error_users,
        "parts": part_no,
        "outputs": outputs,
    }
