# 보안 및 마스킹 정책

본 공개용 데모 패키지는 실제 API 도메인, AWS 계정 ID, 개인 로컬 경로, 서비스 계정 파일을 제거한 상태입니다.

## API 도메인 처리

크롤러 코드는 실제 원천 도메인을 코드에 하드코딩하지 않고 다음 환경변수를 사용합니다.

```text
SOURCE_BASE_URL
SOURCE_PREORDER_SEARCH_URL
```

공개 저장소의 기본값은 `https://example.invalid`입니다.

## 데이터 처리

- Streamlit demo dashboard는 fake CSV 데이터만 사용합니다.
- 사용자 식별자는 hash/alias 형태의 예시 값만 포함합니다.
- 실제 원천 JSON, supporter 개인 식별정보, 인증 파일은 포함하지 않습니다.

## Git ignore

`.env`, `.venv`, `secrets/`, `*.pem`, `*service_account*.json`, `*.parquet`는 `.gitignore`로 제외했습니다.
