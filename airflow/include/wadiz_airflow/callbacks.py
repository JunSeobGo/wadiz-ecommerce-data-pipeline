from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def log_task_failure(context: dict) -> None:
    ti = context.get('task_instance')
    exc = context.get('exception')
    logger.error('Airflow task 실패. task=%s dag=%s error=%s', getattr(ti, 'task_id', None), getattr(ti, 'dag_id', None), exc)


def log_task_success(context: dict) -> None:
    ti = context.get('task_instance')
    logger.info('Airflow task 성공. task=%s dag=%s', getattr(ti, 'task_id', None), getattr(ti, 'dag_id', None))
