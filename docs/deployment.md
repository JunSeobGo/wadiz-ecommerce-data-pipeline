# 배포 (CD)

GitHub Actions에서 **OIDC로 AWS 역할을 assume**해 ECR 이미지 빌드/푸시 + ECS task definition 갱신을 수행합니다. 장기 액세스키를 저장소에 두지 않습니다.

워크플로우: [.github/workflows/deploy.yml](../.github/workflows/deploy.yml) — 자동 실행하지 않고 **수동(workflow_dispatch)** 으로만 동작합니다.

## 흐름

```
GitHub Actions (deploy.yml, 수동 실행)
  │  OIDC 토큰 발급 (id-token: write)
  ▼
AWS IAM Role (신뢰정책: GitHub OIDC)  ← assume
  │
  ├─ ECR 로그인 → Dockerfile.silver / Dockerfile.dbt 빌드 → wd-crawler 레포에 push
  │     - silver-<sha> : bronze / silver / dashboard_export 공용
  │     - dbt-<sha>    : dbt-athena Gold
  └─ ECS RegisterTaskDefinition : 새 이미지로 task 정의 revision 등록
        (Airflow는 family 이름으로 RunTask → 최신 revision 자동 사용)
```

## 활성화에 필요한 것

1. **GitHub OIDC provider** 등록 (`token.actions.githubusercontent.com`)
2. **배포용 IAM Role** 생성
   - 신뢰정책: 위 OIDC provider + 이 저장소(`repo:OWNER/REPO:*`) 조건
   - 권한정책: [iam_policies/github_oidc_deploy_role_policy_template.json](../iam_policies/github_oidc_deploy_role_policy_template.json)
3. **GitHub Secret** `AWS_DEPLOY_ROLE_ARN` 에 역할 ARN 설정
4. ECR 레포(`wd-crawler`), ECS 클러스터/task 역할이 존재

## 실행

Actions 탭 → **deploy** → Run workflow. `image_tag`를 비우면 git sha 앞 12자리를 태그로 사용합니다.

## 참고

`register_task_definitions.py --image <URI>` 로 task 정의 JSON의 컨테이너 이미지를 CD가 주입한 URI로 교체해 등록합니다. 이미지 교체 로직은 단위 테스트로 검증합니다(`tests/test_register_task_definitions.py`).
