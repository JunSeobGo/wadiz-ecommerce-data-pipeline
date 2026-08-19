"""Airflow DAG import 검증 테스트.

DAG 파일에 문법 오류나 import 오류가 있으면 실제 배포 시점에야 발견되는 경우가 많습니다.
이 테스트는 DagBag 로딩만으로 그런 오류를 사전에 잡습니다.

주의:
- Airflow는 POSIX 환경(리눅스/Docker)에서 동작합니다.
- Windows 로컬 등 airflow 로딩이 불가능한 환경에서는 자동으로 skip 됩니다.
- 실제 검증은 CI(Linux + requirements-airflow.txt) 에서 수행됩니다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# airflow 로딩이 불가능한 환경(예: Windows)에서는 이 테스트 전체를 skip 합니다.
pytest.importorskip("airflow.models.dagbag", reason="airflow 로딩이 가능한 환경에서만 실행")

from airflow.models.dagbag import DagBag  # noqa: E402

DAG_FOLDER = Path(__file__).resolve().parent.parent / "airflow" / "dags"

# 존재해야 하는 DAG id 목록. 새 DAG를 추가하면 여기에도 반영합니다.
EXPECTED_DAG_IDS = {
    "wadiz_01_bronze_daily_dag",
    "wadiz_02_silver_daily_dag",
    "wadiz_03_gold_daily_dag",
    "wadiz_04_tableau_export_dag",
}


@pytest.fixture(scope="module")
def dagbag() -> DagBag:
    return DagBag(dag_folder=str(DAG_FOLDER), include_examples=False)


def test_no_import_errors(dagbag: DagBag) -> None:
    assert not dagbag.import_errors, f"DAG import 오류 발생: {dagbag.import_errors}"


def test_expected_dags_are_loaded(dagbag: DagBag) -> None:
    loaded = set(dagbag.dags.keys())
    missing = EXPECTED_DAG_IDS - loaded
    assert not missing, f"로드되지 않은 DAG: {missing} (실제 로드됨: {sorted(loaded)})"
