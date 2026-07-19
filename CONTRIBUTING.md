# 기여 및 협업 규칙 (Contributing Guide)

혼자 진행하는 프로젝트지만, 히스토리 추적과 유지보수를 위해 협업 흐름을 그대로 따라 관리합니다.

> 모든 문서와 코드 주석은 **한글 위주**로 작성합니다.
> 단, 브랜치명·커밋 타입 등 Git 식별자는 아래 규칙에 따라 **영문**으로 작성합니다.

---

## 1. 브랜치 전략

```
main        배포 가능한 안정 버전
 └── develop   개발 통합 브랜치
      ├── feature/xxx   기능 개발
      ├── fix/xxx       버그 수정
      ├── docs/xxx      문서 작업
      ├── refactor/xxx  리팩터링
      └── chore/xxx     설정/잡무
```

### 브랜치명 규칙 (필수)

- **무조건 영문 `snake_case`** 로 작성합니다. (한글·공백·대문자·하이픈 금지)
- 형식: `<타입>/<영문_snake_case_설명>`

| 좋은 예 | 나쁜 예 |
|---|---|
| `feature/silver_etl_refactor` | `feature/실버정제` |
| `fix/athena_ctas_error` | `fix/AthenaError` |
| `docs/readme_update` | `docs/README-update` |
| `refactor/airflow_dag_split` | `feature/dag 개선` |

### 브랜치 타입

| 타입 | 용도 |
|---|---|
| `feature/` | 새로운 기능 |
| `fix/` | 버그 수정 |
| `docs/` | 문서 작성/수정 |
| `refactor/` | 기능 변화 없는 코드 개선 |
| `chore/` | 빌드/설정/패키지 등 잡무 |

---

## 2. 커밋 컨벤션 (필수)

### 형식

```
<Type>: <한글 설명>
```

- **Type 은 영문 + 첫 글자 대문자**, 뒤에 `: ` (콜론+공백)
- **설명은 한글**로, 무엇을 왜 했는지 간결하게
- 제목은 50자 이내, 마침표 없이

### 예시

```
Feat: RAG 검색 API 추가
Fix: OpenSearch 인덱스 오류 수정
Docs: README 아키텍처 다이어그램 업데이트
Refactor: Airflow DAG 계층별 분리
Style: 코드 포맷 및 import 정렬
Test: 검색 API 테스트 코드 추가
Chore: requirements 정리
Perf: Athena CTAS 쿼리 파티셔닝 최적화
Ci: GitHub Actions 데모 빌드 설정
Build: Docker 이미지 빌드 스크립트 수정
```

### Type 목록

| Type | 의미 |
|---|---|
| `Feat` | 새로운 기능 |
| `Fix` | 버그 수정 |
| `Docs` | 문서 변경 |
| `Refactor` | 기능 변화 없는 코드 개선 |
| `Style` | 포맷/세미콜론 등 동작에 영향 없는 변경 |
| `Test` | 테스트 코드 추가/수정 |
| `Chore` | 설정·패키지·기타 잡무 |
| `Perf` | 성능 개선 |
| `Ci` | CI 설정 변경 |
| `Build` | 빌드 시스템·의존성 변경 |

### 본문(선택)

필요하면 제목 아래 한 줄 띄우고 한글로 상세 내용을 적습니다.

```
Feat: 캠페인 KPI 집계 로직 추가

- 누적 펀딩금액, 달성률, 참여자 수 계산 추가
- 전일 대비 증감 컬럼 생성
```

---

## 3. 작업 흐름

```
1. develop 최신화        git switch develop && git pull
2. 브랜치 생성            git switch -c feature/xxx
3. 작업 + 커밋            (커밋 컨벤션 준수)
4. 원격 푸시              git push -u origin feature/xxx
5. PR 생성               develop <- feature/xxx (템플릿 작성)
6. develop 머지          (스스로 리뷰 후 merge)
7. 기능 누적 시 main 머지  + 태그 생성 (v0.1, v1.0 ...)
```

- **main 에 직접 커밋/푸시하지 않습니다.**
- PR 은 혼자여도 반드시 만들고, 작업 내용과 테스트 결과를 기록합니다.

---

## 4. 이슈 / PR

- 기능 단위로 이슈를 먼저 만들고, 브랜치와 연결합니다.
- 이슈·PR 템플릿은 `.github/` 폴더에 있으며 자동으로 불러와집니다.
- PR 본문에 `close #이슈번호` 를 적으면 머지 시 이슈가 자동으로 닫힙니다.

---

## 5. 버전 태그

일정 기능이 `main` 에 모이면 태그를 붙입니다.

| 태그 | 기준 |
|---|---|
| `v0.1` | 기본 파이프라인 / 데이터 계층 구축 |
| `v0.2` | 대시보드 / 리포팅 추가 |
| `v1.0` | 배포 및 CI/CD 완성 |

```
git tag -a v0.1 -m "초기 파이프라인 구축"
git push origin v0.1
```
