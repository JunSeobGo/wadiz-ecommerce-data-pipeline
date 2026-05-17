from __future__ import annotations

import logging

import boto3

from wadiz_airflow.config import get_config

logger = logging.getLogger(__name__)


def delete_s3_prefix(prefix: str) -> int:
    cfg = get_config()
    s3 = boto3.client('s3', region_name=cfg.aws_region)
    clean_prefix = prefix.strip('/') + '/'
    paginator = s3.get_paginator('list_objects_v2')
    deleted = 0

    for page in paginator.paginate(Bucket=cfg.s3_bucket, Prefix=clean_prefix):
        objects = [{'Key': obj['Key']} for obj in page.get('Contents', [])]
        for i in range(0, len(objects), 1000):
            batch = objects[i:i + 1000]
            if batch:
                s3.delete_objects(Bucket=cfg.s3_bucket, Delete={'Objects': batch})
                deleted += len(batch)

    logger.info('S3 prefix 삭제 완료. s3://%s/%s objects=%s', cfg.s3_bucket, clean_prefix, deleted)
    return deleted


def delete_gold_table_prefix(table_name: str) -> int:
    cfg = get_config()
    return delete_s3_prefix(f"{cfg.gold_prefix.rstrip('/')}/{table_name}")
