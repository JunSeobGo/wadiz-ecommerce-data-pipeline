param(
    [Parameter(Mandatory=$true)] [ValidateSet("preorder","comments","supporter","fundings","wishes","user_info")] [string]$Table,
    [Parameter(Mandatory=$true)] [string]$Dt
)

$Region = "ap-northeast-2"
$Cluster = "wd-crawler-cluster"
$TaskDefinition = "wd-bronze-crawler"
$ContainerName = "wd-bronze-container"
$Subnets = "subnet-0abb7263b7ec6580f,subnet-07179740222a12ea2"
$SecurityGroups = "sg-0c057b9568be47eb7"
$DtClean = $Dt.Replace("-", "")
$DtDash = "$($DtClean.Substring(0,4))-$($DtClean.Substring(4,2))-$($DtClean.Substring(6,2))"

$DefaultCommands = @{
    preorder = "python preorder_crawler.py --dt $DtClean"
    comments = "python product_comments.py --dt $DtClean"
    supporter = "python supporter_crawler.py --dt $DtClean"
    fundings = "python fundings_crawler.py --dt $DtDash"
    wishes = "python wishes_crawler.py --dt $DtDash"
    user_info = "python user_info_crawler.py --dt $DtDash"
}

$CommandString = $DefaultCommands[$Table]
$Command = @("bash", "-lc", $CommandString)

$OverrideObject = @{
    containerOverrides = @(
        @{
            name = $ContainerName
            command = $Command
            environment = @(
                @{ name = "AWS_REGION"; value = $Region },
                @{ name = "S3_BUCKET"; value = "wd-data-lake" },
                @{ name = "BRONZE_PREFIX"; value = "bronze/wadiz" },
                @{ name = "TABLE"; value = $Table },
                @{ name = "DT"; value = $DtClean }
            )
        }
    )
}

$OverrideFile = "overrides_bronze_${Table}_${DtClean}.json"
$OverrideObject | ConvertTo-Json -Depth 10 | Set-Content -Encoding ASCII $OverrideFile

Write-Host "Running ECS Bronze task"
Write-Host "Table: $Table"
Write-Host "Dt: $DtClean"
Write-Host "Command: $CommandString"

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
