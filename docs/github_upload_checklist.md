# GitHub 업로드 체크리스트

업로드 전에 아래 항목을 확인합니다.

## 반드시 제외

- `.env`
- `.venv/`, `venv/`
- `__pycache__/`, `*.pyc`
- AWS access key, secret key
- 개인 pem key
- Google service account json
- 실제 API 도메인과 상세 endpoint
- 실제 AWS account id, subnet id, security group id, role arn
- 실제 고객/서포터 개인정보가 포함된 원천 데이터

## 공개 가능

- 마스킹된 `.env.example`
- 예시 fake CSV 데이터
- Terraform skeleton
- Airflow DAG 구조
- Bronze/Silver/Gold 처리 코드
- Streamlit demo dashboard
- README와 설계 문서

## 업로드 전 실행

```bash
python scripts/scan_sensitive_strings.py
python -m compileall airflow wd_bronze wd_silver wd_dashboard_export scripts
```
