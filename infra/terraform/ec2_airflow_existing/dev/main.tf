# 기존 인프라 조회 전용
# 이 파일은 운영 중인 EC2/S3/ECS를 새로 만들지 않고 Terraform에서 안전하게 참조하기 위한 시작점이다.

data "aws_s3_bucket" "data_lake" {
  bucket = var.data_lake_bucket_name
}

data "aws_s3_bucket" "athena_query" {
  bucket = var.athena_query_bucket_name
}

data "aws_instance" "airflow" {
  instance_id = var.airflow_instance_id
}

data "aws_ecs_cluster" "main" {
  cluster_name = var.ecs_cluster_name
}

data "aws_ecr_repository" "repos" {
  for_each = toset(var.ecr_repository_names)
  name     = each.value
}

resource "aws_cloudwatch_log_group" "pipeline_demo" {
  count             = var.enable_managed_log_group ? 1 : 0
  name              = "/wadiz/pipeline-demo"
  retention_in_days = 14

  tags = {
    Project   = var.project_name
    ManagedBy = "terraform"
  }
}

resource "aws_ecr_lifecycle_policy" "cleanup" {
  for_each = var.enable_ecr_lifecycle_policy ? data.aws_ecr_repository.repos : {}

  repository = each.value.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "최근 10개 이미지만 보관"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
