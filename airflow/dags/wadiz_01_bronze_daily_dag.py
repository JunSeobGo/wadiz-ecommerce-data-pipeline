from __future__ import annotations

import pendulum
from airflow.decorators import dag, task
from airflow.operators.python import get_current_context

from wadiz_airflow.bronze import run_bronze_table
from wadiz_airflow.callbacks import log_task_failure, log_task_success
from wadiz_airflow.dates import compact_dt_from_context

DEFAULT_ARGS = {
    'owner': 'wadiz-data',
    'retries': 1,
    'retry_delay': pendulum.duration(minutes=5),
    'on_failure_callback': log_task_failure,
    'on_success_callback': log_task_success,
}

BRONZE_TABLES = ['preorder', 'comments', 'supporter', 'fundings', 'wishes', 'user_info']


@dag(
    dag_id='wadiz_01_bronze_daily_dag',
    description='Bronze Raw JSON 수집 전용 DAG. 원천 API 응답을 변경하지 않고 S3에 보존합니다.',
    start_date=pendulum.datetime(2026, 5, 1, tz='Asia/Seoul'),
    schedule='0 2 * * *',
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=['wadiz', 'bronze', 'daily'],
)
def wadiz_01_bronze_daily_dag():
    @task(task_id='t00_resolve_processing_date')
    def resolve_processing_date() -> str:
        dt = compact_dt_from_context(get_current_context())
        print(f'[DEBUG] Bronze 처리 기준일: {dt}')
        return dt

    @task(task_id='t01_bronze_preorder')
    def bronze_preorder(dt: str):
        print(f'[DEBUG] preorder 수집 시작. dt={dt}')
        return run_bronze_table('preorder', dt)

    @task(task_id='t02_bronze_comments')
    def bronze_comments(dt: str):
        print(f'[DEBUG] comments 수집 시작. dt={dt}')
        return run_bronze_table('comments', dt)

    @task(task_id='t03_bronze_supporter')
    def bronze_supporter(dt: str):
        print(f'[DEBUG] supporter 수집 시작. dt={dt}')
        return run_bronze_table('supporter', dt)

    @task(task_id='t04_bronze_fundings')
    def bronze_fundings(dt: str):
        print(f'[DEBUG] fundings 수집 시작. dt={dt}')
        return run_bronze_table('fundings', dt)

    @task(task_id='t05_bronze_wishes')
    def bronze_wishes(dt: str):
        print(f'[DEBUG] wishes 수집 시작. dt={dt}')
        return run_bronze_table('wishes', dt)

    @task(task_id='t06_bronze_user_info')
    def bronze_user_info(dt: str):
        print(f'[DEBUG] user_info 수집 시작. dt={dt}')
        return run_bronze_table('user_info', dt)

    dt = resolve_processing_date()

    # campaign 목록이 있어야 comments/supporter를 안정적으로 수집할 수 있다.
    preorder = bronze_preorder(dt)

    # supporter 결과에서 user_id 후보가 파생되므로 fundings/wishes/user_info는 supporter 이후 실행한다.
    comments = bronze_comments(dt)
    supporter = bronze_supporter(dt)
    preorder >> [comments, supporter]
    supporter >> [bronze_fundings(dt), bronze_wishes(dt), bronze_user_info(dt)]


wadiz_01_bronze_daily_dag()
