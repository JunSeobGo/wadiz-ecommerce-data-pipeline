from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / 'airflow' / 'include'))

from wadiz_airflow.athena import run_sql_file


def main() -> int:
    parser = argparse.ArgumentParser(description='Run one Athena SQL template.')
    parser.add_argument('--sql', required=True)
    parser.add_argument('--database', default=None)
    args = parser.parse_args()
    print(run_sql_file(args.sql, database=args.database))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
