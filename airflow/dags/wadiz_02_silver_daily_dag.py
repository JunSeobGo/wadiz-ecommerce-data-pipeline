from __future__ import annotations

import pendulum
from airflow.decorators import dag, task
from airflow.models import Variable
from airflow.operators.python import get_current_context
from wadiz_airflow.callbacks import log_task_failure, log_task_success
from wadiz_airflow.datasets import BRONZE_READY, PROCESSING_DT_VAR, SILVER_READY
from wadiz_airflow.dates import compact_dt_from_context
from wadiz_airflow.silver import repair_silver_table, run_silver_table

DEFAULT_ARGS = {
    'owner': 'wadiz-data',
    'retries': 1,
    'retry_delay': pendulum.duration(minutes=5),
    'on_failure_callback': log_task_failure,
    'on_success_callback': log_task_success,
}

SILVER_TABLES = ['preorder', 'comments', 'supporter', 'fundings', 'wishes', 'user_info']


@dag(
    dag_id='wadiz_02_silver_daily_dag',
    description='Silver Parquet 정제 전용 DAG. Bronze JSON을 표준 스키마와 타입으로 변환합니다.',
    start_date=pendulum.datetime(2026, 5, 1, tz='Asia/Seoul'),
    schedule=[BRONZE_READY],
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=['wadiz', 'silver', 'daily'],
)
def wadiz_02_silver_daily_dag():
    @task(task_id='t00_resolve_processing_date')
    def resolve_processing_date() -> str:
        # Bronze가 Variable에 기록한 dt를 우선 사용(Dataset 트리거 시 logical_date 오정렬 방지).
        # 수동/시간 실행 등으로 값이 없으면 logical_date로 fallback.
        dt = Variable.get(PROCESSING_DT_VAR, default_var=None) or compact_dt_from_context(get_current_context())
        print(f'[DEBUG] Silver 처리 기준일: {dt}')
        return dt

    @task
    def transform_table(table: str, dt: str):
        print(f'[DEBUG] Silver 변환 시작. table={table}, dt={dt}')
        return run_silver_table(table, dt)

    @task(task_id='t99_repair_silver_partitions')
    def repair_partitions(tables: list[str]):
        print(f'[DEBUG] Silver partition repair 시작. tables={tables}')
        return [repair_silver_table(table) for table in tables]

    @task(task_id='t100_signal_silver_ready', outlets=[SILVER_READY])
    def signal_silver_ready():
        # Silver 완료 신호(SILVER_READY 발행 → Gold DAG 트리거). Gold는 dt를 쓰지 않는다.
        print('[DEBUG] Silver 완료 신호 발행')

    dt = resolve_processing_date()
    transformed = [transform_table.override(task_id=f't10_silver_{table}')(table, dt) for table in SILVER_TABLES]
    transformed >> repair_partitions(SILVER_TABLES) >> signal_silver_ready()


wadiz_02_silver_daily_dag()
