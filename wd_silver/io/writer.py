from __future__ import annotations

import logging
from io import BytesIO

import boto3

from wd_silver.io.s3_utils import delete_s3_prefix

logger = logging.getLogger(__name__)


def write_parquet_partition(*, df, bucket: str, prefix: str, table: str, dt: str, file_name: str = 'part-00000.parquet', delete_existing: bool = True) -> str:
    partition_prefix = f"{prefix.rstrip('/')}/{table}/dt={dt}/"
    if delete_existing:
        delete_s3_prefix(bucket, partition_prefix)
    key = f'{partition_prefix}{file_name}'
    buf = BytesIO()
    df.to_parquet(buf, index=False, engine='pyarrow')
    buf.seek(0)
    boto3.client('s3').put_object(Bucket=bucket, Key=key, Body=buf.getvalue())
    logger.info('Parquet written. s3://%s/%s rows=%s columns=%s', bucket, key, len(df), len(df.columns))
    return f's3://{bucket}/{key}'


def write_error_rows(*, error_df, bucket: str, error_prefix: str, table: str, dt: str) -> str | None:
    if error_df.empty:
        logger.info('No error rows to write. table=%s dt=%s', table, dt)
        return None
    return write_parquet_partition(df=error_df, bucket=bucket, prefix=error_prefix, table=table, dt=dt, file_name='error-00000.parquet', delete_existing=True)
