variable "project_name" {
  type    = string
  default = "wadiz-demo"
}

variable "region" {
  type    = string
  default = "ap-northeast-2"
}

variable "data_lake_bucket_name" {
  type    = string
  default = "your-data-lake-bucket"
}

variable "athena_query_bucket_name" {
  type    = string
  default = "your-athena-query-result-bucket"
}

variable "airflow_instance_id" {
  type        = string
  description = "기존 Airflow EC2 instance id. 새 EC2를 만들지 않고 조회만 한다."
}

variable "ecs_cluster_name" {
  type        = string
  description = "기존 ECS cluster 이름"
}

variable "ecr_repository_names" {
  type        = list(string)
  default     = ["wd-crawler"]
  description = "기존 ECR repository 목록"
}

variable "enable_managed_log_group" {
  type        = bool
  default     = false
  description = "true로 바꾸면 Terraform이 /wadiz/pipeline-demo log group을 생성한다."
}

variable "enable_ecr_lifecycle_policy" {
  type        = bool
  default     = false
  description = "true로 바꾸면 기존 ECR repository에 image cleanup policy를 적용한다."
}
