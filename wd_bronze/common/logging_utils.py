from __future__ import annotations

import logging
import sys


def setup_logging(name: str) -> logging.Logger:
    """ECS/CloudWatch에서 바로 읽기 좋은 포맷으로 로그를 통일합니다."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        stream=sys.stdout,
        force=True,
    )
    return logging.getLogger(name)
