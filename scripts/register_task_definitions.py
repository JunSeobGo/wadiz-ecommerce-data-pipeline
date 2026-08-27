from __future__ import annotations

import argparse
import json
from pathlib import Path


def apply_image_override(payload: dict, image: str | None) -> dict:
    """CD에서 새로 빌드/푸시한 이미지 URI로 컨테이너 image를 교체한다.

    image가 없으면 JSON에 적힌 값을 그대로 사용한다.
    """
    if not image:
        return payload
    for container in payload.get('containerDefinitions', []):
        container['image'] = image
    return payload


def register_one(path: Path, region: str, image: str | None = None) -> str:
    import boto3  # boto3 없이도 apply_image_override를 테스트할 수 있도록 지연 import

    payload = json.loads(path.read_text(encoding='utf-8'))
    payload = apply_image_override(payload, image)
    response = boto3.client('ecs', region_name=region).register_task_definition(**payload)
    td = response['taskDefinition']
    result = f"{td['family']}:{td['revision']}"
    print(f"registered: {result} from {path} image={image or '(json 그대로)'}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description='Register Wadiz ECS task definition JSON files.')
    parser.add_argument('--task', help='특정 task definition JSON만 등록합니다.')
    parser.add_argument('--dir', default='ecs_task_definitions', help='전체 등록 대상 디렉터리')
    parser.add_argument('--region', default='ap-northeast-2')
    parser.add_argument('--image', default=None, help='컨테이너 image를 이 URI로 교체(CD에서 주입)')
    args = parser.parse_args()

    if args.task:
        paths = [Path(args.task)]
    else:
        paths = sorted(Path(args.dir).glob('*.json'))

    if not paths:
        raise FileNotFoundError('등록할 task definition JSON이 없습니다.')

    for path in paths:
        register_one(path, args.region, args.image)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
