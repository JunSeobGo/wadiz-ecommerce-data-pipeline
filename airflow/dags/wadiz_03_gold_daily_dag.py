from __future__ import annotations

import os
from pathlib import Path

import pendulum
from airflow.decorators import dag, task
from wadiz_airflow.athena import run_sql_file_statements
from wadiz_airflow.callbacks import log_task_failure, log_task_success
from wadiz_airflow.gold import recreate_gold_table_from_sql

DEFAULT_ARGS = {
    'owner': 'wadiz-data',
    'retries': 1,
    'retry_delay': pendulum.duration(minutes=5),
    'on_failure_callback': log_task_failure,
    'on_success_callback': log_task_success,
}

GOLD_TABLES = [
    ('campaign_kpi', 'create_campaign_kpi_v2.sql'),
    ('campaign_daily_kpi', 'create_campaign_daily_kpi_v2.sql'),
    ('campaign_conversion_kpi', 'create_campaign_conversion_kpi_v2.sql'),
    ('comment_nlp_kpi', 'create_comment_nlp_kpi_v2.sql'),
    ('campaign_response_performance', 'create_campaign_response_performance_v2.sql'),
    ('campaign_category_benchmark', 'create_campaign_category_benchmark_v2.sql'),
]


@dag(
    dag_id='wadiz_03_gold_daily_dag',
    description='Gold KPI CTAS 재생성 전용 DAG. Streamlit/Tableau가 조회할 집계 테이블을 만듭니다.',
    start_date=pendulum.datetime(2026, 5, 1, tz='Asia/Seoul'),
    schedule='0 5 * * *',
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=['wadiz', 'gold', 'daily'],
)
def wadiz_03_gold_daily_dag():
    sql_dir = Path(os.getenv('WADIZ_GOLD_SQL_DIR', '/home/ec2-user/airflow/include/wd_gold/sql'))

    @task(task_id='t00_validate_gold_sql_files')
    def validate_gold_sql_files():
        missing = []
        for _, sql_file in GOLD_TABLES:
            path = sql_dir / sql_file
            if not path.exists():
                missing.append(str(path))
        public_view = sql_dir / 'create_public_views.sql'
        if not public_view.exists():
            missing.append(str(public_view))
        if missing:
            raise FileNotFoundError('Gold SQL 파일 누락:\n' + '\n'.join(missing))
        print(f'[DEBUG] Gold SQL 파일 검증 완료. sql_dir={sql_dir}')
        return str(sql_dir)

    @task
    def refresh_gold_table(table_name: str, sql_file: str):
        sql_path = sql_dir / sql_file
        print(f'[DEBUG] Gold CTAS 시작. table={table_name}, sql={sql_path}')
        return recreate_gold_table_from_sql(table_name, sql_path)

    @task(task_id='t90_create_public_views')
    def create_public_views():
        print('[DEBUG] Tableau/Google Sheets용 public view 생성 시작')
        return run_sql_file_statements(sql_dir / 'create_public_views.sql')

    validated = validate_gold_sql_files()
    gold_tasks = [
        refresh_gold_table.override(task_id=f't10_refresh_{table}')(table, sql_file)
        for table, sql_file in GOLD_TABLES
    ]
    validated >> gold_tasks >> create_public_views()


wadiz_03_gold_daily_dag()
