from __future__ import annotations

import logging
import boto3

logger = logging.getLogger(__name__)


def list_s3_objects(bucket: str, prefix: str) -> list[str]:
    s3 = boto3.client('s3')
    paginator = s3.get_paginator('list_objects_v2')
    keys = []
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        keys.extend(obj['Key'] for obj in page.get('Contents', []))
    return keys


def read_s3_bytes(bucket: str, key: str) -> bytes:
    return boto3.client('s3').get_object(Bucket=bucket, Key=key)['Body'].read()


def delete_s3_prefix(bucket: str, prefix: str) -> int:
    s3 = boto3.client('s3')
    paginator = s3.get_paginator('list_objects_v2')
    deleted = 0
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        objects = [{'Key': obj['Key']} for obj in page.get('Contents', [])]
        for i in range(0, len(objects), 1000):
            batch = objects[i:i + 1000]
            if batch:
                s3.delete_objects(Bucket=bucket, Delete={'Objects': batch})
                deleted += len(batch)
    logger.info('Deleted S3 prefix. s3://%s/%s objects=%s', bucket, prefix, deleted)
    return deleted
