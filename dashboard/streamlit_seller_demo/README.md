# Wadiz Manager Dashboard

와디즈 운영자 관점에서 캠페인 성과, 일별 증감, 전환 흐름, 댓글 감성, 카테고리 벤치마크를 한 화면에서 확인하는 Streamlit 대시보드입니다.

## 실행 방법

### Windows

```bash
run_dashboard.bat
```

### Mac / Linux

```bash
./run_dashboard.sh
```

### 직접 실행

```bash
python -m pip install -r requirements.txt
streamlit run app.py --server.port 8503
```

## 주요 구성

```text
wadiz_manager_dashboard/
├─ app.py
├─ requirements.txt
├─ run_dashboard.bat
├─ run_dashboard.sh
├─ .streamlit/
│  └─ config.toml
└─ data/
   ├─ campaign_kpi.csv
   ├─ campaign_daily_kpi.csv
   ├─ campaign_conversion_kpi.csv
   ├─ comment_nlp_kpi.csv
   ├─ comment_word_kpi.csv
   ├─ campaign_category_benchmark.csv
   └─ 원천 CSV 파일들
```

## 반영 내용

- S3 연결 대신 Zip 내부 `data/*.csv`를 바로 읽도록 변경
- 상단 KPI 카드에 전일 대비 상승/하락 수치 표시
- 상승은 빨간 화살표, 하락은 파란 화살표로 표시
- 헤더 오른쪽에 `마감일 D-x`를 크게 표시
- 운영 체크포인트를 KPI 바로 아래 배치
- 체크포인트 문장에서 핵심 수치만 색상 강조
- 일별 펀딩 증감액, 일별 행동 지표, 전환율 추이 추가
- 댓글/NLP 영역을 `긍정 워드클라우드 / 댓글 감성 원차트 / 부정 워드클라우드` 구조로 변경

## 데이터 구조

- `campaign_kpi.csv`: 캠페인별 핵심 성과 지표
- `campaign_daily_kpi.csv`: 일별 누적값과 전일 대비 증감값
- `campaign_conversion_kpi.csv`: 조회, 관심등록, 지지서명, 참여 전환 지표
- `comment_nlp_kpi.csv`: 일별 댓글 감성 집계
- `comment_word_kpi.csv`: 긍정/부정 댓글 키워드 빈도
- `campaign_category_benchmark.csv`: 카테고리 평균 벤치마크
