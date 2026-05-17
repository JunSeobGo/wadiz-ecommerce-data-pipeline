from __future__ import annotations

import logging
import time
from typing import Iterable, Mapping

import boto3

from wadiz_airflow.config import get_config

logger = logging.getLogger(__name__)


class EcsTaskFailed(RuntimeError):
    pass


def _normalize_command(command: str | Iterable[str]) -> list[str]:
    """문자열 명령은 bash -lc로 실행하고, 리스트 명령은 그대로 넘깁니다."""
    if isinstance(command, str):
        return ['bash', '-lc', command]
    return [str(x) for x in command]


def run_fargate_task_and_wait(
    *,
    task_definition: str,
    container_name: str,
    command: str | Iterable[str],
    environment: Mapping[str, str] | None = None,
    timeout_seconds: int = 14400,
    poll_seconds: int = 20,
) -> dict:
    """ECS Fargate task를 실행하고 종료까지 대기합니다.

    Airflow는 무거운 크롤링/ETL을 직접 수행하지 않고 이 함수로 ECS task만 호출합니다.
    실패 원인 추적을 위해 taskArn, stoppedReason, container exitCode를 로그에 남깁니다.
    """
    cfg = get_config()
    ecs = boto3.client('ecs', region_name=cfg.aws_region)
    command_list = _normalize_command(command)

    overrides = {
        'containerOverrides': [
            {
                'name': container_name,
                'command': command_list,
                'environment': [
                    {'name': key, 'value': str(value)}
                    for key, value in (environment or {}).items()
                ],
            }
        ]
    }

    logger.info(
        'ECS task 시작. cluster=%s task_definition=%s container=%s command=%s env_keys=%s',
        cfg.ecs_cluster,
        task_definition,
        container_name,
        command_list,
        sorted((environment or {}).keys()),
    )

    response = ecs.run_task(
        cluster=cfg.ecs_cluster,
        taskDefinition=task_definition,
        launchType='FARGATE',
        platformVersion=cfg.ecs_platform_version,
        networkConfiguration={
            'awsvpcConfiguration': {
                'subnets': cfg.ecs_subnets,
                'securityGroups': cfg.ecs_security_groups,
                'assignPublicIp': cfg.ecs_assign_public_ip,
            }
        },
        overrides=overrides,
    )

    failures = response.get('failures', [])
    if failures:
        raise EcsTaskFailed(f'ECS run_task failures={failures}')

    tasks = response.get('tasks', [])
    if not tasks:
        raise EcsTaskFailed('ECS run_task 결과에 task가 없습니다.')

    task_arn = tasks[0]['taskArn']
    logger.info('ECS task 생성 완료. task_arn=%s', task_arn)

    start = time.time()
    while True:
        desc = ecs.describe_tasks(cluster=cfg.ecs_cluster, tasks=[task_arn])
        if not desc.get('tasks'):
            raise EcsTaskFailed(f'ECS task 조회 실패. task_arn={task_arn}')

        task = desc['tasks'][0]
        last_status = task.get('lastStatus')
        logger.info('ECS task 상태 확인. task_arn=%s last_status=%s', task_arn, last_status)

        if last_status == 'STOPPED':
            stopped_reason = task.get('stoppedReason')
            stop_code = task.get('stopCode')
            containers = task.get('containers', [])
            logger.info('ECS task 종료. task_arn=%s stop_code=%s reason=%s', task_arn, stop_code, stopped_reason)

            failed = []
            for container in containers:
                logger.info(
                    'ECS container 종료. name=%s exit_code=%s reason=%s',
                    container.get('name'),
                    container.get('exitCode'),
                    container.get('reason'),
                )
                if container.get('exitCode') not in (0, None):
                    failed.append(container)

            if failed:
                raise EcsTaskFailed(
                    f'ECS task 실패. task_arn={task_arn} stop_code={stop_code} '
                    f'stopped_reason={stopped_reason} containers={failed}'
                )
            return task

        if time.time() - start > timeout_seconds:
            raise TimeoutError(f'ECS task timeout. seconds={timeout_seconds} task_arn={task_arn}')

        time.sleep(poll_seconds)
