from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List


def _split_csv(value: str) -> List[str]:
    return [v.strip() for v in value.split(',') if v.strip()]


def env(name: str, default: str | None = None, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and (value is None or str(value).strip() == ''):
        raise ValueError(f'필수 환경변수가 없습니다: {name}')
    return str(value or '')


@dataclass(frozen=True)
class WadizConfig:
    aws_region: str
    s3_bucket: str
    bronze_prefix: str
    silver_prefix: str
    silver_error_prefix: str
    gold_prefix: str
    athena_query_result_bucket: str
    athena_query_result_prefix: str
    bronze_db: str
    silver_db: str
    gold_db: str
    athena_workgroup: str
    ecs_cluster: str
    ecs_subnets: List[str]
    ecs_security_groups: List[str]
    ecs_assign_public_ip: str
    ecs_platform_version: str
    ecs_task_family_bronze: str
    ecs_task_family_silver: str
    ecs_task_family_dashboard_export: str
    ecs_container_bronze: str
    ecs_container_silver: str
    ecs_container_dashboard_export: str


def get_config() -> WadizConfig:
    return WadizConfig(
        aws_region=env('AWS_REGION', 'ap-northeast-2'),
        s3_bucket=env('S3_BUCKET', 'wd-data-lake'),
        bronze_prefix=env('BRONZE_PREFIX', 'bronze/wadiz'),
        silver_prefix=env('SILVER_PREFIX', 'silver2/wadiz'),
        silver_error_prefix=env('SILVER_ERROR_PREFIX', env('ERROR_PREFIX', 'silver_error/wadiz')),
        gold_prefix=env('GOLD_PREFIX', 'gold2/wadiz'),
        athena_query_result_bucket=env('ATHENA_QUERY_RESULT_BUCKET', 'wd-athena-query3'),
        athena_query_result_prefix=env('ATHENA_QUERY_RESULT_PREFIX', 'athena-results/'),
        bronze_db=env('BRONZE_DB', 'wadiz_bronze_db'),
        silver_db=env('SILVER_DB', 'wadiz_silver2_db'),
        gold_db=env('GOLD_DB', 'wadiz_gold2_db'),
        athena_workgroup=env('ATHENA_WORKGROUP', 'primary'),
        ecs_cluster=env('ECS_CLUSTER', 'wd-crawler-cluster'),
        ecs_subnets=_split_csv(env('ECS_SUBNETS', required=True)),
        ecs_security_groups=_split_csv(env('ECS_SECURITY_GROUPS', required=True)),
        ecs_assign_public_ip=env('ECS_ASSIGN_PUBLIC_IP', 'ENABLED'),
        ecs_platform_version=env('ECS_PLATFORM_VERSION', '1.4.0'),
        ecs_task_family_bronze=env('ECS_TASK_FAMILY_BRONZE', 'wd-bronze-crawler'),
        ecs_task_family_silver=env('ECS_TASK_FAMILY_SILVER', 'wd-silver-etl'),
        ecs_task_family_dashboard_export=env('ECS_TASK_FAMILY_DASHBOARD_EXPORT', 'wd-dashboard-export'),
        ecs_container_bronze=env('ECS_CONTAINER_BRONZE', 'wd-bronze-container'),
        ecs_container_silver=env('ECS_CONTAINER_SILVER', 'wd-silver-container'),
        ecs_container_dashboard_export=env('ECS_CONTAINER_DASHBOARD_EXPORT', 'wd-dashboard-export-container'),
    )
