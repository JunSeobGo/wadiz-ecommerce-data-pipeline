from __future__ import annotations

import argparse
import importlib
import logging
import sys
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    force=True,
)

logger = logging.getLogger("wd_bronze.run_bronze")


TABLE_MODULES = {
    "preorder": "wd_bronze.crawlers.preorder",
    "comments": "wd_bronze.crawlers.comments",
    "supporter": "wd_bronze.crawlers.supporter",
    "fundings": "wd_bronze.crawlers.fundings",
    "wishes": "wd_bronze.crawlers.wishes",
    "user_info": "wd_bronze.crawlers.user_info",
}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Wadiz Bronze crawler by table.")
    parser.add_argument(
        "--table",
        required=True,
        choices=sorted(TABLE_MODULES),
        help="실행할 Bronze table 이름",
    )
    parser.add_argument(
        "--dt",
        required=True,
        help="파티션 날짜. 예: 20260509 또는 2026-05-09",
    )
    return parser.parse_args(argv)


def validate_result(expected_table: str, expected_dt: str, result: Any) -> None:
    if not isinstance(result, dict):
        raise RuntimeError(
            f"Bronze result가 dict가 아닙니다. "
            f"expected_table={expected_table}, expected_dt={expected_dt}, result={result}"
        )

    actual_table = result.get("table")
    actual_dt = str(result.get("dt", "")).replace("-", "")

    if actual_table != expected_table:
        raise RuntimeError(
            "Bronze table mismatch. "
            f"expected={expected_table}, actual={actual_table}, result={result}"
        )

    if actual_dt != expected_dt:
        raise RuntimeError(
            "Bronze dt mismatch. "
            f"expected={expected_dt}, actual={actual_dt}, result={result}"
        )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    table = args.table.strip()
    dt = args.dt.replace("-", "").strip()

    module_name = TABLE_MODULES[table]

    logger.info(
        "Bronze crawler started. table=%s dt=%s module=%s",
        table,
        dt,
        module_name,
    )

    module = importlib.import_module(module_name)

    if not hasattr(module, "run"):
        raise AttributeError(f"{module_name} 모듈에 run(dt) 함수가 없습니다.")

    logger.info(
        "Bronze crawler module loaded. table=%s dt=%s module=%s run=%s",
        table,
        dt,
        module_name,
        getattr(module, "run"),
    )

    result = module.run(dt)

    validate_result(table, dt, result)

    logger.info(
        "Bronze crawler finished. table=%s dt=%s result=%s",
        table,
        dt,
        result,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
