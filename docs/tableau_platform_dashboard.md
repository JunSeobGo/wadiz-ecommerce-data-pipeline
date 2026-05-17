# Tableau 플랫폼 대시보드 설계

판매자용 상세 대시보드는 Streamlit demo dashboard에서 제공합니다.
플랫폼 전체 성과 대시보드는 Gold public view를 Google Sheets로 내보낸 뒤 Tableau에서 연결하는 구조로 설계했습니다.

## 흐름

```text
Athena Gold public view
↓
wd_dashboard_export.export_gold2_to_google_sheets
↓
Google Sheets
↓
Tableau 플랫폼 운영 대시보드
```

## Tableau에서 보는 지표

- 전체 캠페인 수
- 카테고리별 평균 펀딩금액
- 카테고리별 달성률
- 참여자 수 분포
- 댓글 긍정/부정 비율
- 카테고리 벤치마크

Google service account 파일은 `secrets/`에 두고 Git에는 올리지 않습니다.
