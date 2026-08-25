"""DAG 간 데이터 의존성을 나타내는 Airflow Dataset 정의.

시간(cron)만으로 이어져 있던 DAG들을 '데이터가 준비되었다'는 신호로 연결한다.
- Bronze 완료 → BRONZE_READY 발행 → Silver 실행
- Silver 완료 → SILVER_READY 발행 → Gold 실행
- Gold 완료   → GOLD_READY 발행   → Export 실행

각 신호에는 처리 기준일(dt)을 extra로 실어, 하위 DAG이 같은 dt로 처리하게 한다.
"""

from __future__ import annotations

from airflow.datasets import Dataset

BRONZE_READY = Dataset("wadiz://bronze/daily")
SILVER_READY = Dataset("wadiz://silver/daily")
GOLD_READY = Dataset("wadiz://gold/daily")

# 처리 기준일(dt) 전달용 Airflow Variable 키.
# Airflow 2.9는 Dataset 이벤트 extra를 지원하지 않아, Bronze가 이 Variable에 dt를 기록하고
# Silver가 읽어 같은 날짜를 처리한다(Dataset 트리거 시 logical_date 오정렬 방지).
PROCESSING_DT_VAR = "wadiz_processing_dt"
