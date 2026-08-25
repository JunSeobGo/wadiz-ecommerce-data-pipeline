from __future__ import annotations

import pendulum
from airflow.decorators import dag, task
from wadiz_airflow.callbacks import log_task_failure, log_task_success
from wadiz_airflow.config import get_config
from wadiz_airflow.datasets import GOLD_READY, SILVER_READY
from wadiz_airflow.ecs import run_fargate_task_and_wait

DEFAULT_ARGS = {
    'owner': 'wadiz-data',
    'retries': 1,
    'retry_delay': pendulum.duration(minutes=5),
    'on_failure_callback': log_task_failure,
    'on_success_callback': log_task_success,
}


@dag(
    dag_id='wadiz_03_gold_daily_dag',
    description='Gold 모델링 DAG. dbt-athena(ECS)로 Gold Mart 생성 + 데이터 테스트를 함께 수행합니다.',
    start_date=pendulum.datetime(2026, 5, 1, tz='Asia/Seoul'),
    schedule=[SILVER_READY],
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=['wadiz', 'gold', 'dbt'],
)
def wadiz_03_gold_daily_dag():
    @task(task_id='t10_dbt_build')
    def dbt_build():
        # Airflow는 실행 시점만 관리하고, 모델 의존성(ref)과 품질 검증(test)은 dbt가 담당한다.
        # dbt build = dbt run + dbt test (모델 생성 후 테스트 통과까지 한 번에).
        cfg = get_config()
        print('[DEBUG] dbt build (Gold 모델 + 테스트) ECS task 실행 시작')
        return run_fargate_task_and_wait(
            task_definition=cfg.ecs_task_family_dbt,
            container_name=cfg.ecs_container_dbt,
            command='dbt build --project-dir /app/dbt_wadiz --profiles-dir /app/dbt_wadiz',
            environment={
                'AWS_REGION': cfg.aws_region,
                'WADIZ_SILVER_DB': cfg.silver_db,
                'WADIZ_GOLD_DB': cfg.gold_db,
                'DBT_ATHENA_S3_STAGING_DIR': f's3://{cfg.athena_query_result_bucket}/{cfg.athena_query_result_prefix.strip("/")}/dbt/',
                'DBT_ATHENA_S3_DATA_DIR': f's3://{cfg.s3_bucket}/{cfg.gold_prefix.strip("/")}/dbt/',
                'DBT_ATHENA_WORKGROUP': cfg.athena_workgroup,
            },
            timeout_seconds=3600,
        )

    @task(task_id='t95_signal_gold_ready', outlets=[GOLD_READY])
    def signal_gold_ready():
        # Gold 생성 완료 신호(GOLD_READY 발행 → Export DAG 트리거).
        print('[DEBUG] Gold 완료 신호 발행')

    dbt_build() >> signal_gold_ready()


wadiz_03_gold_daily_dag()
