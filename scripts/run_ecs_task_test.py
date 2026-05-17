from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / 'airflow' / 'include'))

from wadiz_airflow.ecs import run_fargate_task_and_wait


def main() -> int:
    parser = argparse.ArgumentParser(description='Run ECS Fargate task test.')
    parser.add_argument('--task-family', required=True)
    parser.add_argument('--container-name', required=True)
    parser.add_argument('--command', required=True)
    parser.add_argument('--timeout-seconds', type=int, default=3600)
    args = parser.parse_args()
    run_fargate_task_and_wait(task_definition=args.task_family, container_name=args.container_name, command=args.command, timeout_seconds=args.timeout_seconds)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
