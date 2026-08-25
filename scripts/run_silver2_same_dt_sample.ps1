param(
    [Parameter(Mandatory=$true)] [string]$Table,
    [Parameter(Mandatory=$true)] [string]$Dt,
    [Parameter(Mandatory=$false)] [int]$MaxFiles = 5,
    [switch]$RunActual
)

# 주의: 테스트 샘플도 Silver output은 무조건 silver2/wadiz에 씁니다.
# 그래서 샘플 테스트 후 실제 전체 실행으로 같은 dt partition을 다시 덮어써야 합니다.

$Bucket = "wd-data-lake"
$Region = "ap-northeast-2"
$SourceBronzeBase = "bronze/wadiz"
$SampleBronzeBase = "bronze_sample/wadiz"
$SilverPrefix = "silver2/wadiz"
$ErrorPrefix = "silver_error/wadiz"
$Cluster = "wd-crawler-cluster"
$TaskDefinition = "wd-silver-etl"
$ContainerName = "wd-silver-container"
# 데모용 placeholder 값 (연결된 운영 계정 없음)
$Subnets = "subnet-xxxxxxxx,subnet-yyyyyyyy"
$SecurityGroups = "sg-xxxxxxxx"

$DtClean = $Dt.Replace("-", "")
$DtDashed = "$($DtClean.Substring(0,4))-$($DtClean.Substring(4,2))-$($DtClean.Substring(6,2))"

Write-Host "Preparing same-dt sample"
Write-Host "Table: $Table"
Write-Host "Dt: $DtClean"
Write-Host "MaxFiles: $MaxFiles"
Write-Host "Sample Bronze: s3://$Bucket/$SampleBronzeBase/$Table/dt=$DtClean/"
Write-Host "Silver Output: s3://$Bucket/$SilverPrefix/$Table/dt=$DtClean/"

$Keys = @()
foreach ($Prefix in @("$SourceBronzeBase/$Table/dt=$DtClean/", "$SourceBronzeBase/$Table/dt=$DtDashed/")) {
    Write-Host "Scanning s3://$Bucket/$Prefix"
    $RawKeys = aws s3api list-objects-v2 --bucket $Bucket --prefix $Prefix --max-keys $MaxFiles --query "Contents[].Key" --output text --region $Region
    if ($RawKeys -and $RawKeys -ne "None") {
        foreach ($Key in ($RawKeys -split "\s+")) {
            if ($Key -and $Key.EndsWith(".json")) { $Keys += $Key }
        }
    }
    if ($Keys.Count -ge $MaxFiles) { break }
}

$Keys = $Keys | Select-Object -First $MaxFiles
if ($Keys.Count -eq 0) { Write-Host "No source files found."; exit 1 }

$SampleBronzePrefix = "$SampleBronzeBase/$Table/dt=$DtClean/"
aws s3 rm "s3://$Bucket/$SampleBronzePrefix" --recursive --region $Region
aws s3 rm "s3://$Bucket/$SilverPrefix/$Table/dt=$DtClean/" --recursive --region $Region
aws s3 rm "s3://$Bucket/$ErrorPrefix/$Table/dt=$DtClean/" --recursive --region $Region

$Index = 0
foreach ($Key in $Keys) {
    $Index += 1
    $FileName = Split-Path $Key -Leaf
    $DestKey = "$SampleBronzePrefix" + "sample_$('{0:D3}' -f $Index)_$FileName"
    aws s3 cp "s3://$Bucket/$Key" "s3://$Bucket/$DestKey" --region $Region
}

$Command = @("python", "-m", "wd_silver.run_silver", "--table", $Table, "--dt", $DtClean)
if (-not $RunActual) { $Command += "--dry-run" }

$OverrideObject = @{
    containerOverrides = @(
        @{
            name = $ContainerName
            command = $Command
            environment = @(
                @{ name = "AWS_REGION"; value = $Region },
                @{ name = "S3_BUCKET"; value = $Bucket },
                @{ name = "BRONZE_PREFIX"; value = $SampleBronzeBase },
                @{ name = "SILVER_PREFIX"; value = $SilverPrefix },
                @{ name = "SILVER_ERROR_PREFIX"; value = $ErrorPrefix },
                @{ name = "ERROR_PREFIX"; value = $ErrorPrefix },
                @{ name = "SILVER_DB"; value = "wadiz_silver2_db" }
            )
        }
    )
}

$OverrideFile = "overrides_${Table}_${DtClean}_same_dt_sample.json"
$OverrideObject | ConvertTo-Json -Depth 10 | Set-Content -Encoding ASCII $OverrideFile

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
