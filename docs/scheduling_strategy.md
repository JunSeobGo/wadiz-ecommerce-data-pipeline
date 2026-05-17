# 스케줄 설계

크라우드펀딩/프리오더 도메인은 실시간 초 단위 처리보다 전일 마감 기준의 안정적인 운영 리포팅이 더 중요합니다.
따라서 기본 스케줄은 새벽 배치 + 검증 버퍼를 기준으로 설계했습니다.

| 단계 | 실행 시간 | 목적 |
|---|---:|---|
| Bronze | 02:00 | 전일/당일 기준 원천 응답 수집 |
| Silver | 03:30 | JSON flatten, 타입 정리, 중복 제거, PII 해시 처리 |
| Gold | 05:00 | 운영 KPI CTAS 재생성 |
| Tableau Export | 06:30 | Gold public view를 Google Sheets로 내보내 Tableau 갱신 |
| Dashboard Check | 07:00 | 운영자 확인 가능 상태 |
| Report | 09:00 | 오전 보고 기준 데이터 제공 |

기존 통합 DAG는 실패 지점 파악이 어려웠기 때문에 Bronze, Silver, Gold, Export DAG로 분리했습니다.
