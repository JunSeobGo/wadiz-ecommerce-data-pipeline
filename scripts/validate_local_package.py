from __future__ import annotations

import json
import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROLE = 'arn:aws:iam::000000000000:role/ECS-role-wd-crawler'


def main() -> int:
    py_files = list(ROOT.rglob('*.py'))
    for path in py_files:
        py_compile.compile(str(path), doraise=True)
    json_files = list(ROOT.rglob('*.json'))
    for path in json_files:
        json.loads(path.read_text(encoding='utf-8'))
    for path in (ROOT / 'ecs_task_definitions').glob('*.json'):
        payload = json.loads(path.read_text(encoding='utf-8'))
        assert payload['taskRoleArn'] == ROLE, path
        assert payload['executionRoleArn'] == ROLE, path
    print(f'validated py_files={len(py_files)} json_files={len(json_files)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
