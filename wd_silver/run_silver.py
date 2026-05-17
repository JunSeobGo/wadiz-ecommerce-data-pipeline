from __future__ import annotations

import argparse
import importlib
import json
import logging
import sys

from wd_silver.config import get_config
from wd_silver.date_utils import normalize_dt
from wd_silver.io.reader import read_bronze_table_from_s3
from wd_silver.io.writer import write_error_rows, write_parquet_partition
from wd_silver.quality.validators import log_quality_metrics, split_valid_and_error_rows
from wd_silver.schemas import get_schema

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
logger = logging.getLogger('wd_silver.run_silver')

TABLES = ['preorder', 'comments', 'supporter', 'fundings', 'wishes', 'user_info']


def load_transform(table: str):
    module = importlib.import_module(f'wd_silver.transforms.{table}')
    return getattr(module, 'transform')


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run Wadiz Silver ETL for one table and dt.')
    parser.add_argument('--table', required=True, choices=TABLES)
    parser.add_argument('--dt', required=True)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--allow-empty', action='store_true')
    parser.add_argument('--no-error-rows', action='store_true')
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    cfg = get_config()
    table = args.table
    dt = normalize_dt(args.dt)
    schema = get_schema(table)
    logger.info('Silver ETL started. table=%s dt=%s dry_run=%s', table, dt, args.dry_run)

    bronze_df = read_bronze_table_from_s3(bucket=cfg.s3_bucket, bronze_prefix=cfg.bronze_prefix, table=table, dt=dt)
    if bronze_df.empty and not (args.allow_empty or cfg.allow_empty):
        logger.error('Bronze input is empty. table=%s dt=%s', table, dt)
        return 2

    silver_df = load_transform(table)(bronze_df, dt=dt, hash_salt=cfg.hash_salt)
    metrics = log_quality_metrics(silver_df, schema)
    validation = split_valid_and_error_rows(silver_df, schema)

    if args.dry_run:
        logger.info('Dry run completed. table=%s dt=%s metrics=%s validation=%s', table, dt, json.dumps(metrics, ensure_ascii=False, default=str), json.dumps(validation.metrics, ensure_ascii=False, default=str))
        return 0

    output_uri = write_parquet_partition(df=validation.valid_df, bucket=cfg.s3_bucket, prefix=cfg.silver_prefix, table=table, dt=dt, delete_existing=True)
    error_uri = None
    if cfg.write_error_rows and not args.no_error_rows:
        error_uri = write_error_rows(error_df=validation.error_df, bucket=cfg.s3_bucket, error_prefix=cfg.silver_error_prefix, table=table, dt=dt)
    logger.info('Silver ETL completed. table=%s dt=%s output_uri=%s error_uri=%s validation=%s', table, dt, output_uri, error_uri, json.dumps(validation.metrics, ensure_ascii=False, default=str))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
