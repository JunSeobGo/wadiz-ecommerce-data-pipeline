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
from wd_bronze.common.s3 import write_records
from wd_bronze.common.source_ids import load_campaign_ids_from_preorder

logger = setup_logging("wd_bronze.crawlers.supporter")


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


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)

    if raw is None or str(raw).strip() == "":
        return default

    try:
        value = float(raw)
    except ValueError:
        logger.warning(
            "환경변수 float 변환 실패. default 사용. name=%s raw=%s default=%s",
            name,
            raw,
            default,
        )
        return default

    if value < 0:
        logger.warning(
            "환경변수 값이 0 미만입니다. default 사용. name=%s raw=%s default=%s",
            name,
            raw,
            default,
        )
        return default

    return value


def fetch_supporters_for_campaign(
    session,
    campaign_id: int,
    *,
    timeout: int,
    max_pages: int | None,
    max_records: int | None,
) -> tuple[list[dict[str, Any]], bool, str]:
    """
    campaign_id 기준 지지서명/참여자 데이터 수집.

    기존에 성공했던 API:
    <SOURCE_BASE_URL>/web/campaign/{campaign_id}/participants?pageSize=80&startNum=0

    반환:
    - rows: 수집 row
    - ok: API 자체가 정상적으로 호출됐는지 여부
    - reason: 종료 사유
    """

    base_url = os.getenv('SOURCE_BASE_URL', 'https://example.invalid').rstrip('/')
    url = f'{base_url}/web/campaign/{campaign_id}/participants'

    page_size = _int_env("SUPPORTER_PAGE_SIZE", 80)
    request_sleep_sec = _float_env("SUPPORTER_PAGE_SLEEP_SEC", 0.2)

    rows: list[dict[str, Any]] = []
    start_num = 0
    page_no = 0

    headers = {
        "accept": "application/json, text/plain, */*",
        "referer": f"{base_url}/web/campaign/detail/{campaign_id}",
    }

    logger.info(
        "supporter campaign fetch start. campaign_id=%s url=%s page_size=%s start_num=%s max_pages=%s max_records=%s",
        campaign_id,
        url,
        page_size,
        start_num,
        max_pages,
        max_records,
    )

    while True:
        if max_pages is not None and page_no >= max_pages:
            logger.info(
                "supporter max_pages 도달. campaign_id=%s page_no=%s max_pages=%s rows=%s",
                campaign_id,
                page_no,
                max_pages,
                len(rows),
            )
            return rows, True, "max_pages_reached"

        params = {
            "pageSize": page_size,
            "startNum": start_num,
        }

        try:
            response = session.get(
                url,
                headers=headers,
                params=params,
                timeout=timeout,
            )
        except Exception as e:
            logger.exception(
                "supporter API 요청 예외. campaign_id=%s page_no=%s start_num=%s error=%s",
                campaign_id,
                page_no,
                start_num,
                e,
            )
            return rows, False, "request_exception"

        if response.status_code != 200:
            logger.warning(
                "supporter API 실패. campaign_id=%s page_no=%s start_num=%s status=%s body_head=%s",
                campaign_id,
                page_no,
                start_num,
                response.status_code,
                response.text[:500],
            )
            return rows, False, f"status_{response.status_code}"

        try:
            payload = response.json()
        except Exception as e:
            logger.exception(
                "supporter JSON 파싱 실패. campaign_id=%s page_no=%s start_num=%s error=%s body_head=%s",
                campaign_id,
                page_no,
                start_num,
                e,
                response.text[:500],
            )
            return rows, False, "json_parse_error"

        data = payload.get("data", [])

        if not isinstance(data, list):
            logger.warning(
                "supporter data 타입 이상. campaign_id=%s page_no=%s start_num=%s data_type=%s payload_keys=%s",
                campaign_id,
                page_no,
                start_num,
                type(data).__name__,
                list(payload.keys()) if isinstance(payload, dict) else type(payload).__name__,
            )
            return rows, False, "invalid_data_type"

        if not data:
            logger.info(
                "supporter page empty. campaign_id=%s page_no=%s start_num=%s rows=%s",
                campaign_id,
                page_no,
                start_num,
                len(rows),
            )
            return rows, True, "empty_page"

        valid_count = 0

        for item in data:
            if not isinstance(item, dict):
                continue

            rows.append(
                {
                    "campaign_id": campaign_id,
                    "raw_text": item,
                    "status": "success",
                }
            )
            valid_count += 1

            if max_records is not None and len(rows) >= max_records:
                logger.info(
                    "supporter campaign max_records 도달. campaign_id=%s rows=%s max_records=%s",
                    campaign_id,
                    len(rows),
                    max_records,
                )
                return rows[:max_records], True, "campaign_max_records_reached"

        logger.info(
            "supporter page fetched. campaign_id=%s page_no=%s start_num=%s page_rows=%s valid_rows=%s rows_total=%s",
            campaign_id,
            page_no,
            start_num,
            len(data),
            valid_count,
            len(rows),
        )

        # 기존 성공 코드 방식: start += page_size
        start_num += page_size
        page_no += 1

        time.sleep(request_sleep_sec)


def run(dt: str) -> dict[str, Any]:
    cfg = get_bronze_config(table="supporter", dt=dt)

    max_pages = table_max_pages("supporter", cfg.max_pages)

    # max_records는 전체 supporter row 기준으로 사용
    max_records = table_max_records("supporter", cfg.max_records)

    # 운영 기본값은 50,000 rows.
    # 테스트할 때만 ECS env로 SUPPORTER_CHUNK_ROWS=20 넣기.
    chunk_rows = _int_env("SUPPORTER_CHUNK_ROWS", 20)

    # 잘못된 API URL/응답 구조일 때 9,500개를 끝까지 돌지 않도록 방어
    max_consecutive_api_failures = _int_env("SUPPORTER_MAX_CONSECUTIVE_API_FAILURES", 30)
    max_consecutive_zero_rows = _int_env("SUPPORTER_MAX_CONSECUTIVE_ZERO_ROWS", 300)

    campaign_ids = [int(x) for x in csv_env("BRONZE_CAMPAIGN_IDS")]

    if not campaign_ids:
        campaign_ids = load_campaign_ids_from_preorder(
            cfg.s3_bucket,
            cfg.bronze_prefix,
            dt,
        )

    logger.info(
        "BRONZE_START table=supporter dt=%s campaign_ids=%s max_pages=%s max_records=%s chunk_rows=%s bucket=%s prefix=%s",
        dt,
        len(campaign_ids),
        max_pages,
        max_records,
        chunk_rows,
        cfg.s3_bucket,
        cfg.bronze_prefix,
    )

    if not campaign_ids:
        raise RuntimeError("supporter 수집용 campaign_id가 없습니다. 먼저 preorder Bronze를 생성하세요.")

    session = make_session()

    buffer: list[dict[str, Any]] = []
    outputs: list[str] = []

    total_rows = 0
    campaigns_done = 0
    campaigns_error = 0
    zero_row_campaigns = 0
    consecutive_api_failures = 0
    consecutive_zero_rows = 0
    part_no = 0

    def flush_buffer(reason: str) -> None:
        nonlocal buffer, part_no, outputs

        if not buffer:
            logger.info(
                "BRONZE_FLUSH_SKIP table=supporter dt=%s part=%s reason=%s buffer_rows=0",
                dt,
                part_no,
                reason,
            )
            return

        part_name = f"supporter_part_{part_no:05d}"

        logger.info(
            "BRONZE_FLUSH_START table=supporter dt=%s part=%s rows=%s reason=%s",
            dt,
            part_no,
            len(buffer),
            reason,
        )

        uri = write_records(
            cfg.s3_bucket,
            cfg.bronze_prefix,
            "supporter",
            dt,
            buffer,
            name=part_name,
        )

        outputs.append(uri)

        logger.info(
            "BRONZE_PART_WRITTEN table=supporter dt=%s part=%s rows=%s output=%s reason=%s",
            dt,
            part_no,
            len(buffer),
            uri,
            reason,
        )

        buffer.clear()
        part_no += 1

    for idx, cid in enumerate(campaign_ids, start=1):
        try:
            remaining_records: int | None = None

            if max_records is not None:
                remaining_records = max_records - total_rows
                if remaining_records <= 0:
                    logger.info(
                        "supporter 전체 max_records 도달. total_rows=%s max_records=%s",
                        total_rows,
                        max_records,
                    )
                    break

            rows, ok, reason = fetch_supporters_for_campaign(
                session,
                cid,
                timeout=cfg.request_timeout,
                max_pages=max_pages,
                max_records=remaining_records,
            )

            if not ok:
                campaigns_error += 1
                consecutive_api_failures += 1
            else:
                consecutive_api_failures = 0

            if len(rows) == 0:
                zero_row_campaigns += 1
                consecutive_zero_rows += 1
            else:
                consecutive_zero_rows = 0

            if max_records is not None:
                available = max_records - total_rows
                rows = rows[:available]

            buffer.extend(rows)
            total_rows += len(rows)
            campaigns_done += 1

            logger.info(
                "BRONZE_PROGRESS table=supporter dt=%s idx=%s/%s campaign_id=%s campaign_rows=%s buffer_rows=%s total_rows=%s parts_written=%s ok=%s reason=%s consecutive_api_failures=%s consecutive_zero_rows=%s",
                dt,
                idx,
                len(campaign_ids),
                cid,
                len(rows),
                len(buffer),
                total_rows,
                part_no,
                ok,
                reason,
                consecutive_api_failures,
                consecutive_zero_rows,
            )

            # API가 잘못된 경우 빠르게 실패
            if consecutive_api_failures >= max_consecutive_api_failures and total_rows == 0:
                raise RuntimeError(
                    "supporter API 연속 실패로 중단합니다. "
                    f"consecutive_api_failures={consecutive_api_failures}, "
                    f"last_campaign_id={cid}, "
                    f"last_reason={reason}, "
                    "URL 또는 응답 구조를 확인하세요. "
                    "정상 URL 예: <SOURCE_BASE_URL>/web/campaign/{campaign_id}/participants?pageSize=80&startNum=0"
                )

            # API는 200인데 계속 0건이면 campaign_id 소스나 응답 구조를 의심
            if consecutive_zero_rows >= max_consecutive_zero_rows and total_rows == 0:
                raise RuntimeError(
                    "supporter가 연속 0건으로 중단합니다. "
                    f"consecutive_zero_rows={consecutive_zero_rows}, "
                    f"last_campaign_id={cid}, "
                    f"last_reason={reason}"
                )

            while len(buffer) >= chunk_rows:
                write_chunk = buffer[:chunk_rows]
                remain_chunk = buffer[chunk_rows:]

                buffer = write_chunk
                flush_buffer(reason="chunk_rows_reached")

                buffer = remain_chunk

            if max_records is not None and total_rows >= max_records:
                logger.info(
                    "supporter 전체 max_records 도달 후 종료. total_rows=%s max_records=%s",
                    total_rows,
                    max_records,
                )
                break

            time.sleep(cfg.page_sleep_sec)

        except Exception as e:
            logger.exception(
                "supporter campaign 처리 중 예외 발생. idx=%s/%s campaign_id=%s error=%s",
                idx,
                len(campaign_ids),
                cid,
                e,
            )
            raise

    flush_buffer(reason="final_buffer")

    logger.info(
        "BRONZE_RESULT table=supporter dt=%s rows=%s parts=%s outputs=%s campaigns_done=%s campaigns_error=%s zero_row_campaigns=%s",
        dt,
        total_rows,
        part_no,
        len(outputs),
        campaigns_done,
        campaigns_error,
        zero_row_campaigns,
    )

    if total_rows <= 0:
        raise RuntimeError(
            f"supporter Bronze 수집 결과가 0건입니다. "
            f"dt={dt}, campaigns={len(campaign_ids)}, parts={part_no}, outputs={len(outputs)}, "
            f"campaigns_done={campaigns_done}, campaigns_error={campaigns_error}, zero_row_campaigns={zero_row_campaigns}"
        )

    if not outputs:
        raise RuntimeError(
            f"supporter Bronze S3 output이 없습니다. dt={dt}, rows={total_rows}, parts={part_no}"
        )

    return {
        "table": "supporter",
        "dt": dt,
        "rows": total_rows,
        "parts": part_no,
        "outputs": outputs,
        "campaigns_done": campaigns_done,
        "campaigns_error": campaigns_error,
        "zero_row_campaigns": zero_row_campaigns,
    }