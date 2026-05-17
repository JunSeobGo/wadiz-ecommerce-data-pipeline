from __future__ import annotations

from wadiz_airflow.config import get_config
from wadiz_airflow.ecs import run_fargate_task_and_wait

TABLES = ['preorder', 'comments', 'supporter', 'fundings', 'wishes', 'user_info']


def bronze_command_for(table: str, dt: str) -> str:
    """모든 Bronze 수집은 wd_bronze.run_bronze 모듈을 통해 실행합니다.

    개별 파일명(product_comments.py 등)을 Airflow에 직접 노출하지 않으면
    Docker 이미지 내부 파일 위치가 바뀌어도 DAG 수정 없이 wd_bronze 패키지 안에서만 관리할 수 있습니다.
    """
    if table not in TABLES:
        raise ValueError(f'지원하지 않는 Bronze 테이블입니다: {table}')
    return f'python -m wd_bronze.run_bronze --table {table} --dt {dt}'


def run_bronze_table(table: str, dt: str) -> dict:
    cfg = get_config()
    command = bronze_command_for(table, dt)
    env = {
        'AWS_REGION': cfg.aws_region,
        'S3_BUCKET': cfg.s3_bucket,
        'BRONZE_PREFIX': cfg.bronze_prefix,
        'TABLE': table,
        'DT': dt,
    }
    return run_fargate_task_and_wait(
        task_definition=cfg.ecs_task_family_bronze,
        container_name=cfg.ecs_container_bronze,
        command=command,
        environment=env,
        timeout_seconds=7200,
    )
