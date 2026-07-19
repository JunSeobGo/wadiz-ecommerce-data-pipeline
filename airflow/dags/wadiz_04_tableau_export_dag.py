from __future__ import annotations

import pendulum
from airflow.decorators import dag, task
from wadiz_airflow.callbacks import log_task_failure, log_task_success
from wadiz_airflow.config import get_config
from wadiz_airflow.ecs import run_fargate_task_and_wait

DEFAULT_ARGS = {
    'owner': 'wadiz-data',
    'retries': 1,
    'retry_delay': pendulum.duration(minutes=5),
    'on_failure_callback': log_task_failure,
    'on_success_callback': log_task_success,
}


@dag(
    dag_id='wadiz_04_tableau_export_dag',
    description='Gold public view를 Google Sheets로 내보내 Tableau 플랫폼 대시보드에서 사용합니다.',
    start_date=pendulum.datetime(2026, 5, 1, tz='Asia/Seoul'),
    schedule='30 6 * * *',
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=['wadiz', 'tableau', 'google-sheets'],
)
def wadiz_04_tableau_export_dag():
    @task(task_id='t10_export_gold_to_google_sheets')
    def export_gold_to_google_sheets():
        cfg = get_config()
        print('[DEBUG] Google Sheets export ECS task 실행 시작')
        return run_fargate_task_and_wait(
            task_definition=cfg.ecs_task_family_dashboard_export,
            container_name=cfg.ecs_container_dashboard_export,
            command='python -m wd_dashboard_export.export_gold2_to_google_sheets',
            environment={
                'AWS_REGION': cfg.aws_region,
                'ATHENA_DATABASE': cfg.gold_db,
                'ATHENA_OUTPUT_LOCATION': f's3://{cfg.athena_query_result_bucket}/{cfg.athena_query_result_prefix.strip("/")}/',
                'GOOGLE_APPLICATION_CREDENTIALS': '/app/secrets/google_service_account.json',
            },
            timeout_seconds=3600,
        )

    export_gold_to_google_sheets()


wadiz_04_tableau_export_dag()
