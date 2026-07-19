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

logger = setup_logging('wd_bronze.crawlers.comments')


def fetch_comments_for_campaign(
    session,
    campaign_id: int,
    *,
    timeout: int,
    max_pages: int | None,
    max_records: int | None,
) -> list[dict[str, Any]]:
    """
    특정 campaign_id의 댓글/답글 데이터를 수집한다.

    주의:
    - 이 함수는 campaign 1개에 대한 rows만 반환한다.
    - 전체 comments를 한 번에 메모리에 누적하지 않도록, run()에서 chunk 단위로 S3 저장한다.
    - 댓글과 답글은 depth로 구분한다.
      depth=0: 원댓글
      depth=1: 답글
    """
    base_url = os.getenv('SOURCE_BASE_URL', 'https://example.invalid').rstrip('/')
    url = f'{base_url}/web/reward/api/comments/campaigns/{campaign_id}'
    headers = {
        'referer': f'{base_url}/web/campaign/detail/qa/{campaign_id}/comment'
    }

    rows: list[dict[str, Any]] = []
    page = 0

    while True:
        if max_pages is not None and page >= max_pages:
            logger.info(
                'comments max_pages 도달. campaign_id=%s max_pages=%s',
                campaign_id,
                max_pages,
            )
            break

        if max_records is not None and len(rows) >= max_records:
            logger.info(
                'comments campaign max_records 도달. campaign_id=%s max_records=%s',
                campaign_id,
                max_records,
            )
            break

        params = {
            'page': page,
            'size': 10,
            'commentGroupType': 'CAMPAIGN',
        }

        try:
            response = session.get(
                url,
                headers=headers,
                params=params,
                timeout=timeout,
            )
        except Exception:
            logger.exception(
                'comments API 요청 중 예외 발생. campaign_id=%s page=%s',
                campaign_id,
                page,
            )
            break

        if response.status_code != 200:
            logger.warning(
                'comments API 실패. campaign_id=%s page=%s status=%s body_prefix=%s',
                campaign_id,
                page,
                response.status_code,
                response.text[:300],
            )
            break

        try:
            payload = response.json()
        except Exception:
            logger.exception(
                'comments API JSON 파싱 실패. campaign_id=%s page=%s body_prefix=%s',
                campaign_id,
                page,
                response.text[:300],
            )
            break

        content = payload.get('data', {}).get('content', [])
        if not content:
            break

        for comment in content:
            rows.append(
                {
                    'campaign_id': campaign_id,
                    'raw': comment,
                    'depth': 0,
                    'status': 'success',
                }
            )

            for reply in comment.get('commentReplys', []) or []:
                rows.append(
                    {
                        'campaign_id': campaign_id,
                        'raw': reply,
                        'depth': 1,
                        'status': 'success',
                    }
                )

            if max_records is not None and len(rows) >= max_records:
                break

        logger.info(
            'comments page fetched. campaign_id=%s page=%s rows_total=%s',
            campaign_id,
            page,
            len(rows),
        )

        page += 1
        time.sleep(0.15)

    return rows


def _get_chunk_rows() -> int:
    """
    comments Bronze 저장 chunk 크기를 반환한다.

    기본값은 50,000 rows이다.
    환경변수 COMMENTS_CHUNK_ROWS로 조정할 수 있다.

    예:
    COMMENTS_CHUNK_ROWS=30000
    """
    raw_value = os.getenv('COMMENTS_CHUNK_ROWS', '50000')

    try:
        chunk_rows = int(raw_value)
    except ValueError:
        logger.warning(
            'COMMENTS_CHUNK_ROWS 값이 숫자가 아닙니다. 기본값 50000을 사용합니다. value=%s',
            raw_value,
        )
        chunk_rows = 50000

    if chunk_rows <= 0:
        logger.warning(
            'COMMENTS_CHUNK_ROWS 값이 0 이하입니다. 기본값 50000을 사용합니다. value=%s',
            raw_value,
        )
        chunk_rows = 50000

    return chunk_rows


def run(dt: str) -> dict[str, Any]:
    """
    comments Bronze 수집 메인 함수.

    기존 방식:
    - 전체 comments rows를 all_rows에 계속 누적
    - 마지막에 S3에 한 번만 저장

    변경 방식:
    - COMMENTS_CHUNK_ROWS 단위로 S3에 part 파일 저장
    - 저장 후 buffer를 비워 메모리 사용량을 제한
    - 중간에 실패해도 이미 저장된 part 파일은 S3에 남음
    """
    cfg = get_bronze_config(table='comments', dt=dt)
    max_pages = table_max_pages('comments', cfg.max_pages)
    max_records = table_max_records('comments', cfg.max_records)
    chunk_rows = _get_chunk_rows()

    campaign_ids = [int(x) for x in csv_env('BRONZE_CAMPAIGN_IDS')]
    if not campaign_ids:
        campaign_ids = load_campaign_ids_from_preorder(
            cfg.s3_bucket,
            cfg.bronze_prefix,
            dt,
        )

    logger.info(
        'BRONZE_START table=comments dt=%s campaign_ids=%s max_pages=%s max_records=%s chunk_rows=%s',
        dt,
        len(campaign_ids),
        max_pages,
        max_records,
        chunk_rows,
    )

    if not campaign_ids:
        raise RuntimeError('comments 수집용 campaign_id가 없습니다. 먼저 preorder Bronze를 생성하세요.')

    session = make_session()

    # 전체 rows를 한 번에 들고 있지 않고, chunk 단위로 S3에 저장한다.
    buffer: list[dict[str, Any]] = []

    total_rows = 0
    part_no = 0
    output_uris: list[str] = []

    def flush_part(force: bool = False) -> None:
        """
        buffer에 쌓인 comments rows를 S3에 part 파일로 저장한다.

        force=False:
        - buffer가 chunk_rows 이상일 때만 저장

        force=True:
        - 마지막에 남은 rows가 chunk_rows보다 작아도 저장
        """
        nonlocal buffer, part_no, output_uris

        if not buffer:
            return

        if not force and len(buffer) < chunk_rows:
            return

        while buffer and (force or len(buffer) >= chunk_rows):
            if force:
                part_rows = buffer
                buffer = []
            else:
                part_rows = buffer[:chunk_rows]
                buffer = buffer[chunk_rows:]

            if not part_rows:
                break

            part_name = f'comments_part_{part_no:05d}'
            uri = write_records(
                cfg.s3_bucket,
                cfg.bronze_prefix,
                'comments',
                dt,
                part_rows,
                name=part_name,
            )
            output_uris.append(uri)

            logger.info(
                'BRONZE_PART_WRITTEN table=comments dt=%s part=%s rows=%s output=%s',
                dt,
                part_no,
                len(part_rows),
                uri,
            )

            part_no += 1

            if force:
                break

    for idx, cid in enumerate(campaign_ids, start=1):
        # max_records가 있으면 전체 수집량 기준으로 남은 개수만큼만 더 수집한다.
        remaining_records: int | None = None
        if max_records is not None:
            remaining_records = max_records - total_rows
            if remaining_records <= 0:
                logger.info(
                    'comments 전체 max_records 도달. max_records=%s total_rows=%s',
                    max_records,
                    total_rows,
                )
                break

        rows = fetch_comments_for_campaign(
            session,
            cid,
            timeout=cfg.request_timeout,
            max_pages=max_pages,
            max_records=remaining_records,
        )

        buffer.extend(rows)
        total_rows += len(rows)

        logger.info(
            'comments campaign done. idx=%s/%s campaign_id=%s rows=%s total=%s buffer=%s parts=%s',
            idx,
            len(campaign_ids),
            cid,
            len(rows),
            total_rows,
            len(buffer),
            part_no,
        )

        # buffer가 일정 크기 이상이면 즉시 S3에 저장하고 메모리를 비운다.
        flush_part(force=False)

        if max_records is not None and total_rows >= max_records:
            logger.info(
                'comments 전체 max_records 도달 후 수집 종료. max_records=%s total_rows=%s',
                max_records,
                total_rows,
            )
            break

        time.sleep(cfg.page_sleep_sec)

    # 마지막 남은 rows 저장
    flush_part(force=True)

    logger.info(
        'BRONZE_RESULT table=comments dt=%s rows=%s parts=%s outputs=%s',
        dt,
        total_rows,
        part_no,
        len(output_uris),
    )

    return {
        'table': 'comments',
        'dt': dt,
        'rows': total_rows,
        'parts': part_no,
        'outputs': output_uris,
    }
