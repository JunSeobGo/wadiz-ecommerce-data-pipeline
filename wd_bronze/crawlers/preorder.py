from __future__ import annotations

import os
import time
from typing import Any

from wd_bronze.common.config import get_bronze_config, table_max_pages, table_max_records
from wd_bronze.common.http import make_session
from wd_bronze.common.logging_utils import setup_logging
from wd_bronze.common.s3 import now_utc_iso, write_records

logger = setup_logging('wd_bronze.crawlers.preorder')

SEARCH_URL = os.getenv('SOURCE_PREORDER_SEARCH_URL', 'https://example.invalid/api/search/v2/preorder')
PAGE_LIMIT = 500


def fetch_page(session, start_num: int, timeout: int) -> list[dict[str, Any]]:
    payload = {
        'categoryCode': '',
        'endYn': '',
        'order': 'recent',
        'limit': PAGE_LIMIT,
        'isMakerClub': False,
        'startNum': start_num,
    }
    response = session.post(SEARCH_URL, json=payload, timeout=timeout)
    if response.status_code != 200:
        logger.warning('preorder API 실패. start=%s status=%s body=%s', start_num, response.status_code, response.text[:300])
        return []
    data = response.json()
    items = data.get('data', {}).get('list', [])
    if not isinstance(items, list):
        logger.warning('preorder 응답 구조가 예상과 다릅니다. start=%s keys=%s', start_num, list(data.keys()))
        return []
    return [item for item in items if isinstance(item, dict)]


def run(dt: str) -> dict[str, Any]:
    cfg = get_bronze_config(table='preorder', dt=dt)
    max_pages = table_max_pages('preorder', cfg.max_pages)
    max_records = table_max_records('preorder', cfg.max_records)
    session = make_session()

    logger.info('BRONZE_START table=preorder dt=%s max_pages=%s max_records=%s', dt, max_pages, max_records)
    all_rows: list[dict[str, Any]] = []
    page = 0
    start = 0
    collected_at = now_utc_iso()

    while True:
        if max_pages is not None and page >= max_pages:
            logger.info('preorder max_pages 도달. page=%s', page)
            break

        items = fetch_page(session, start, cfg.request_timeout)
        logger.info('preorder page fetched. page=%s start=%s rows=%s', page, start, len(items))
        if not items:
            break

        for item in items:
            item.setdefault('collectedAt', collected_at)
            all_rows.append(item)
            if max_records is not None and len(all_rows) >= max_records:
                logger.info('preorder max_records 도달. rows=%s', len(all_rows))
                break

        if max_records is not None and len(all_rows) >= max_records:
            break

        page += 1
        start += PAGE_LIMIT
        time.sleep(cfg.page_sleep_sec)

    uri = write_records(cfg.s3_bucket, cfg.bronze_prefix, 'preorder', dt, all_rows, name='preorder')
    logger.info('BRONZE_RESULT table=preorder dt=%s rows=%s output=%s', dt, len(all_rows), uri)
    if not all_rows:
        raise RuntimeError('preorder 수집 결과가 0건입니다. API 응답/네트워크/요청 조건을 확인하세요.')
    return {'table': 'preorder', 'dt': dt, 'rows': len(all_rows), 'output': uri}
