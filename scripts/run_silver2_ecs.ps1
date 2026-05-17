param(
    [Parameter(Mandatory=$true)] [string]$Table,
    [Parameter(Mandatory=$true)] [string]$Dt,
    [switch]$DryRun
)

$Region = "ap-northeast-2"
$Cluster = "wd-crawler-cluster"
$TaskDefinition = "wd-silver-etl"
$ContainerName = "wd-silver-container"
$Subnets = "subnet-xxxxxxxx,subnet-yyyyyyyy"
$SecurityGroups = "sg-xxxxxxxx"

$DtClean = $Dt.Replace("-", "")
$Command = @("python", "-m", "wd_silver.run_silver", "--table", $Table, "--dt", $DtClean)
if ($DryRun) { $Command += "--dry-run" }

$OverrideObject = @{
    containerOverrides = @(
        @{
            name = $ContainerName
            command = $Command
            environment = @(
                @{ name = "AWS_REGION"; value = $Region },
                @{ name = "S3_BUCKET"; value = "wd-data-lake" },
                @{ name = "BRONZE_PREFIX"; value = "bronze/wadiz" },
                @{ name = "SILVER_PREFIX"; value = "silver2/wadiz" },
                @{ name = "SILVER_ERROR_PREFIX"; value = "silver_error/wadiz" },
                @{ name = "ERROR_PREFIX"; value = "silver_error/wadiz" },
                @{ name = "SILVER_DB"; value = "wadiz_silver2_db" }
            )
        }
    )
}

$OverrideFile = "overrides_${Table}_${DtClean}_silver2.json"
$OverrideObject | ConvertTo-Json -Depth 10 | Set-Content -Encoding ASCII $OverrideFile

Write-Host "Running ECS Silver2 task"
Write-Host "Table: $Table"
Write-Host "Dt: $DtClean"
Write-Host "DryRun: $DryRun"
Write-Host "OverrideFile: $OverrideFile"
Write-Host "SILVER_PREFIX: silver2/wadiz"

$TaskArn = aws ecs run-task `
  --cluster $Cluster `
  --launch-type FARGATE `
  --task-definition $TaskDefinition `
  --network-configuration "awsvpcConfiguration={subnets=[$Subnets],securityGroups=[$SecurityGroups],assignPublicIp=ENABLED}" `
  --overrides "file://$OverrideFile" `
  --region $Region `
  --query "tasks[0].taskArn" `
  --output text

Write-Host "Started ECS task:"
Write-Host $TaskArn
