# Terraform IaC 사용 방법

이 Terraform 예시는 기존 Airflow EC2가 살아있다는 가정에서 작성한 안전 시작 버전입니다.

처음에는 기존 S3, EC2, ECS, ECR을 조회만 합니다. 새 EC2를 만들지 않습니다.

## 실행 순서

```powershell
Copy-Item terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
```

처음 목표는 아래 결과입니다.

```text
Plan: 0 to add, 0 to change, 0 to destroy
```

`enable_managed_log_group` 또는 `enable_ecr_lifecycle_policy`를 true로 바꾸면 낮은 위험도 리소스부터 Terraform 관리 대상으로 확장할 수 있습니다.
