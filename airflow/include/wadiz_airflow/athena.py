from __future__ import annotations

import logging
import time
from pathlib import Path
from string import Template

import boto3

from wadiz_airflow.config import get_config

logger = logging.getLogger(__name__)


class AthenaQueryFailed(RuntimeError):
    pass


def render_sql_template(sql_path: str | Path, extra: dict | None = None) -> str:
    cfg = get_config()
    template = Template(Path(sql_path).read_text(encoding='utf-8'))
    values = {
        'bronze_db': cfg.bronze_db,
        'silver_db': cfg.silver_db,
        'gold_db': cfg.gold_db,
        's3_bucket': cfg.s3_bucket,
        'bronze_prefix': cfg.bronze_prefix,
        'silver_prefix': cfg.silver_prefix,
        'gold_prefix': cfg.gold_prefix,
    }
    if extra:
        values.update(extra)
    return template.safe_substitute(values)


def split_sql_statements(sql: str) -> list[str]:
    """세미콜론으로 SQL을 나눕니다. 문자열 내부 세미콜론은 보존합니다."""
    statements: list[str] = []
    current: list[str] = []
    in_single = False
    for ch in sql:
        if ch == "'":
            in_single = not in_single
        if ch == ';' and not in_single:
            statement = ''.join(current).strip()
            if statement:
                statements.append(statement)
            current = []
        else:
            current.append(ch)
    tail = ''.join(current).strip()
    if tail:
        statements.append(tail)
    return statements


def run_athena_query(
    *,
    query: str,
    database: str | None = None,
    timeout_seconds: int = 1800,
    poll_seconds: int = 5,
) -> str:
    cfg = get_config()
    athena = boto3.client('athena', region_name=cfg.aws_region)
    output_location = f"s3://{cfg.athena_query_result_bucket}/{cfg.athena_query_result_prefix.strip('/')}/"

    logger.info('Athena query 시작. database=%s workgroup=%s output=%s', database or cfg.gold_db, cfg.athena_workgroup, output_location)
    response = athena.start_query_execution(
        QueryString=query,
        QueryExecutionContext={'Database': database or cfg.gold_db},
        ResultConfiguration={'OutputLocation': output_location},
        WorkGroup=cfg.athena_workgroup,
    )
    query_execution_id = response['QueryExecutionId']
    start = time.time()

    while True:
        result = athena.get_query_execution(QueryExecutionId=query_execution_id)
        status = result['QueryExecution']['Status']['State']
        reason = result['QueryExecution']['Status'].get('StateChangeReason', '')
        logger.info('Athena query 상태. id=%s status=%s reason=%s', query_execution_id, status, reason)

        if status == 'SUCCEEDED':
            return query_execution_id
        if status in {'FAILED', 'CANCELLED'}:
            raise AthenaQueryFailed(f'Athena query 실패. id={query_execution_id} status={status} reason={reason}')
        if time.time() - start > timeout_seconds:
            raise TimeoutError(f'Athena query timeout. id={query_execution_id}')
        time.sleep(poll_seconds)


def run_sql_file(sql_path: str | Path, database: str | None = None, extra: dict | None = None) -> str:
    sql = render_sql_template(sql_path, extra=extra)
    return run_athena_query(query=sql, database=database)


def run_sql_file_statements(sql_path: str | Path, database: str | None = None, extra: dict | None = None) -> list[str]:
    sql = render_sql_template(sql_path, extra=extra)
    query_ids: list[str] = []
    for statement in split_sql_statements(sql):
        query_ids.append(run_athena_query(query=statement, database=database))
    return query_ids


def repair_table(database: str, table: str) -> str:
    return run_athena_query(query=f'MSCK REPAIR TABLE {database}.{table}', database=database)
