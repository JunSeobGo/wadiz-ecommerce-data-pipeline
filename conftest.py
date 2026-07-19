"""pytest 공통 설정.

- 저장소 루트를 import 경로에 넣어 wd_bronze / wd_silver 등을 테스트에서 바로 import 할 수 있게 합니다.
- Airflow DAG import 테스트를 위해 airflow/include 와 airflow/dags 경로도 추가합니다.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# wd_* 패키지 및 airflow 공통 모듈(wadiz_airflow) import 경로 확보
_EXTRA_PATHS = [
    ROOT,
    ROOT / "airflow" / "include",
    ROOT / "airflow" / "dags",
]

for _path in _EXTRA_PATHS:
    _path_str = str(_path)
    if _path.exists() and _path_str not in sys.path:
        sys.path.insert(0, _path_str)
