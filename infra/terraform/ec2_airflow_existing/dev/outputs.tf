output "data_lake_bucket" {
  value = data.aws_s3_bucket.data_lake.bucket
}

output "athena_query_bucket" {
  value = data.aws_s3_bucket.athena_query.bucket
}

output "airflow_instance_id" {
  value = data.aws_instance.airflow.id
}

output "airflow_instance_state" {
  value = data.aws_instance.airflow.instance_state
}

output "airflow_public_ip" {
  value = data.aws_instance.airflow.public_ip
}

output "ecs_cluster_arn" {
  value = data.aws_ecs_cluster.main.arn
}
