from __future__ import annotations

from wadiz_airflow.athena import repair_table
from wadiz_airflow.config import get_config
from wadiz_airflow.ecs import run_fargate_task_and_wait


SILVER_TABLES = ['preorder', 'comments', 'supporter', 'fundings', 'wishes', 'user_info']


def run_silver_table(table: str, dt: str, dry_run: bool = False) -> dict:
    """Bronze JSON을 Silver2 Parquet으로 변환합니다.

    detail은 현재 대시보드에서 사용하지 않으므로 자동화 대상에서 제외합니다.
    """
    if table not in SILVER_TABLES:
        raise ValueError(f'지원하지 않는 Silver 테이블입니다: {table}')

    cfg = get_config()
    command = ['python', '-m', 'wd_silver.run_silver', '--table', table, '--dt', dt]
    if dry_run:
        command.append('--dry-run')

    env = {
        'AWS_REGION': cfg.aws_region,
        'S3_BUCKET': cfg.s3_bucket,
        'BRONZE_PREFIX': cfg.bronze_prefix,
        'SILVER_PREFIX': cfg.silver_prefix,
        'SILVER_ERROR_PREFIX': cfg.silver_error_prefix,
        'ERROR_PREFIX': cfg.silver_error_prefix,
        'SILVER_DB': cfg.silver_db,
    }
    return run_fargate_task_and_wait(
        task_definition=cfg.ecs_task_family_silver,
        container_name=cfg.ecs_container_silver,
        command=command,
        environment=env,
        timeout_seconds=7200,
    )


def repair_silver_table(table: str) -> str:
    cfg = get_config()
    return repair_table(cfg.silver_db, table)
