from __future__ import annotations

import os
import time
from typing import Any

from wd_bronze.common.config import (
    csv_env,
    get_bronze_config,
    table_max_pages,
    table_max_records,
)
from wd_bronze.common.http import make_session
from wd_bronze.common.logging_utils import setup_logging
from wd_bronze.common.s3 import now_utc_iso, write_payload
from wd_bronze.common.source_ids import load_user_ids_from_supporter

logger = setup_logging("wd_bronze.crawlers.wishes")


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


def fetch_wishes_for_user(
    session,
    user_id: str,
    *,
    timeout: int,
    max_pages: int | None,
) -> list[dict[str, Any]]:
    """
    특정 user_id의 찜 목록 수집.

    기존 원본 구조 유지:
    - URL: <SOURCE_BASE_URL>/web/supporter/{user_id}/wishes
    - 응답 위치: data.projectList
    """

    base_url = os.getenv('SOURCE_BASE_URL', 'https://example.invalid').rstrip('/')
    url = f'{base_url}/web/supporter/{user_id}/wishes'

    rows: list[dict[str, Any]] = []
    page = 0
    prev_ids: set[Any] = set()

    logger.info(
        "wishes user fetch start. user_id=%s url=%s max_pages=%s",
        user_id,
        url,
        max_pages,
    )

    while True:
        if max_pages is not None and page >= max_pages:
            logger.info(
                "wishes max_pages 도달. user_id=%s page=%s max_pages=%s rows=%s",
                user_id,
                page,
                max_pages,
                len(rows),
            )
            break

        try:
            response = session.get(
                url,
                params={"size": 50, "page": page},
                timeout=timeout,
            )
        except Exception as e:
            logger.exception(
                "wishes API 요청 예외. user_id=%s page=%s error=%s",
                user_id,
                page,
                e,
            )
            break

        if response.status_code != 200:
            logger.warning(
                "wishes API 실패. user_id=%s page=%s status=%s body_head=%s",
                user_id,
                page,
                response.status_code,
                response.text[:500],
            )
            break

        try:
            payload = response.json()
        except Exception as e:
            logger.exception(
                "wishes JSON 파싱 실패. user_id=%s page=%s error=%s body_head=%s",
                user_id,
                page,
                e,
                response.text[:500],
            )
            break

        items = payload.get("data", {}).get("projectList", [])

        if not items:
            logger.info(
                "wishes page empty. user_id=%s page=%s rows=%s",
                user_id,
                page,
                len(rows),
            )
            break

        valid_items = [item for item in items if isinstance(item, dict)]

        current_ids = {
            item.get("projectId") or item.get("campaignId")
            for item in valid_items
        }

        if current_ids and current_ids == prev_ids:
            logger.info(
                "wishes 중복 페이지 감지. user_id=%s page=%s ids=%s",
                user_id,
                page,
                len(current_ids),
            )
            break

        prev_ids = current_ids
        rows.extend(valid_items)

        logger.info(
            "wishes page fetched. user_id=%s page=%s page_rows=%s rows_total=%s",
            user_id,
            page,
            len(valid_items),
            len(rows),
        )

        page += 1
        time.sleep(0.2)

    return rows


def run(dt: str) -> dict[str, Any]:
    cfg = get_bronze_config(table="wishes", dt=dt)

    max_pages = table_max_pages("wishes", cfg.max_pages)

    # 기존 max_records는 saved_files 기준으로 쓰고 있었음.
    # 여기서는 최대 처리 user 수로 사용.
    max_users = table_max_records("wishes", cfg.max_records)

    # 100명 단위로 S3 part 저장.
    # 테스트 시 WISHES_CHUNK_USERS=10 등으로 조정 가능.
    chunk_users = _int_env("WISHES_CHUNK_USERS", 100)

    logger.info(
        "BRONZE_PREP table=wishes dt=%s bucket=%s prefix=%s max_pages=%s max_users=%s chunk_users=%s",
        dt,
        cfg.s3_bucket,
        cfg.bronze_prefix,
        max_pages,
        max_users,
        chunk_users,
    )

    user_ids = csv_env("BRONZE_USER_IDS")

    logger.info(
        "wishes BRONZE_USER_IDS env 로딩 완료. users=%s",
        len(user_ids),
    )

    if not user_ids:
        logger.info(
            "wishes user_id를 supporter Bronze에서 로딩 시작. supporter_prefix=s3://%s/%s/supporter/dt=%s/",
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
            "wishes user_id를 supporter Bronze에서 로딩 완료. users=%s sample=%s",
            len(user_ids),
            user_ids[:5],
        )

    logger.info(
        "BRONZE_START table=wishes dt=%s users=%s max_pages=%s max_users=%s chunk_users=%s",
        dt,
        len(user_ids),
        max_pages,
        max_users,
        chunk_users,
    )

    if not user_ids:
        raise RuntimeError(
            f"wishes 수집용 user_id가 없습니다. supporter Bronze를 먼저 확인하세요. "
            f"s3://{cfg.s3_bucket}/{cfg.bronze_prefix.rstrip('/')}/supporter/dt={dt}/"
        )

    session = make_session()

    buffer: list[dict[str, Any]] = []
    outputs: list[str] = []

    processed_users = 0
    saved_users = 0
    error_users = 0
    total_rows = 0
    part_no = 0

    def flush_buffer(reason: str) -> None:
        nonlocal buffer, part_no, outputs

        if not buffer:
            logger.info(
                "BRONZE_FLUSH_SKIP table=wishes dt=%s part=%s reason=%s buffer_users=0",
                dt,
                part_no,
                reason,
            )
            return

        part_name = f"wishes_part_{part_no:05d}"

        part_users = len(buffer)
        part_rows = sum(
            len(item.get("data", []))
            for item in buffer
            if isinstance(item.get("data", []), list)
        )

        logger.info(
            "BRONZE_FLUSH_START table=wishes dt=%s part=%s users=%s rows=%s reason=%s",
            dt,
            part_no,
            part_users,
            part_rows,
            reason,
        )

        uri = write_payload(
            cfg.s3_bucket,
            cfg.bronze_prefix,
            "wishes",
            dt,
            buffer,
            name=part_name,
        )

        outputs.append(uri)

        logger.info(
            "BRONZE_PART_WRITTEN table=wishes dt=%s part=%s users=%s rows=%s output=%s reason=%s",
            dt,
            part_no,
            part_users,
            part_rows,
            uri,
            reason,
        )

        buffer.clear()
        part_no += 1

    for idx, user_id in enumerate(user_ids, start=1):
        if max_users is not None and processed_users >= max_users:
            logger.info(
                "wishes max_users 도달. processed_users=%s max_users=%s",
                processed_users,
                max_users,
            )
            break

        try:
            rows = fetch_wishes_for_user(
                session,
                user_id,
                timeout=cfg.request_timeout,
                max_pages=max_pages,
            )

            payload = {
                "collected_at": now_utc_iso(),
                "user_id": user_id,
                "data": rows,
            }

            buffer.append(payload)
            processed_users += 1
            saved_users += 1
            total_rows += len(rows)

            logger.info(
                "BRONZE_PROGRESS table=wishes dt=%s idx=%s/%s user_id=%s user_rows=%s buffer_users=%s total_users=%s total_rows=%s parts_written=%s",
                dt,
                idx,
                len(user_ids),
                user_id,
                len(rows),
                len(buffer),
                saved_users,
                total_rows,
                part_no,
            )

            if len(buffer) >= chunk_users:
                flush_buffer(reason="chunk_users_reached")

            time.sleep(cfg.page_sleep_sec)

        except Exception as e:
            error_users += 1

            logger.exception(
                "wishes user 처리 중 예외 발생. idx=%s/%s user_id=%s error=%s",
                idx,
                len(user_ids),
                user_id,
                e,
            )

            continue

    flush_buffer(reason="final_buffer")

    logger.info(
        "BRONZE_RESULT table=wishes dt=%s users=%s rows=%s parts=%s outputs=%s error_users=%s",
        dt,
        saved_users,
        total_rows,
        part_no,
        len(outputs),
        error_users,
    )

    if saved_users <= 0:
        raise RuntimeError(
            f"wishes Bronze 저장 user가 0명입니다. dt={dt}, input_users={len(user_ids)}"
        )

    if not outputs:
        raise RuntimeError(
            f"wishes Bronze S3 output이 없습니다. dt={dt}, users={saved_users}, rows={total_rows}"
        )

    return {
        "table": "wishes",
        "dt": dt,
        "users": saved_users,
        "rows": total_rows,
        "parts": part_no,
        "outputs": outputs,
        "error_users": error_users,
    }