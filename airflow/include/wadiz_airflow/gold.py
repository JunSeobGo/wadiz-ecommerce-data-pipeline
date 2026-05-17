from __future__ import annotations

import logging
from pathlib import Path

from wadiz_airflow.athena import render_sql_template, run_athena_query
from wadiz_airflow.config import get_config
from wadiz_airflow.s3 import delete_gold_table_prefix

logger = logging.getLogger(__name__)


def recreate_gold_table_from_sql(table_name: str, sql_path: str | Path) -> str:
    """Gold2 CTAS를 멱등적으로 재생성합니다.

    Athena CTAS는 external_location 경로가 비어 있어야 하므로
    DROP TABLE 후 S3 prefix 삭제, 그 다음 CREATE TABLE 순서로 실행합니다.
    """
    cfg = get_config()
    logger.info('Gold table DROP. table=%s', table_name)
    run_athena_query(query=f'DROP TABLE IF EXISTS {cfg.gold_db}.{table_name}', database=cfg.gold_db)

    logger.info('Gold S3 prefix 삭제. table=%s', table_name)
    delete_gold_table_prefix(table_name)

    logger.info('Gold table CREATE. table=%s sql_path=%s', table_name, sql_path)
    sql = render_sql_template(sql_path)
    return run_athena_query(query=sql, database=cfg.gold_db)
