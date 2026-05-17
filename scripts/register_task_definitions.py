from __future__ import annotations

import argparse
import json
from pathlib import Path

import boto3


def register_one(path: Path, region: str) -> str:
    payload = json.loads(path.read_text(encoding='utf-8'))
    response = boto3.client('ecs', region_name=region).register_task_definition(**payload)
    td = response['taskDefinition']
    result = f"{td['family']}:{td['revision']}"
    print(f"registered: {result} from {path}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description='Register Wadiz ECS task definition JSON files.')
    parser.add_argument('--task', help='특정 task definition JSON만 등록합니다.')
    parser.add_argument('--dir', default='ecs_task_definitions', help='전체 등록 대상 디렉터리')
    parser.add_argument('--region', default='ap-northeast-2')
    args = parser.parse_args()

    if args.task:
        paths = [Path(args.task)]
    else:
        paths = sorted(Path(args.dir).glob('*.json'))

    if not paths:
        raise FileNotFoundError('등록할 task definition JSON이 없습니다.')

    for path in paths:
        register_one(path, args.region)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
