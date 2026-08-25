"""Silver transform 테스트용 공통 헬퍼.

- 각 테이블별 '최소 유효 bronze row'를 만들어주는 팩토리.
- transform은 외부 의존(S3 등) 없이 DataFrame만 받으므로 입력만 만들면 된다.
"""

from __future__ import annotations

import pandas as pd

from wd_silver.transforms import (
    comments,
    fundings,
    preorder,
    supporter,
    user_info,
    wishes,
)

# PII 검증용: 이 원본 user id가 출력에 남으면 안 된다(해시만 남아야 함).
RAW_USER_ID = "rawuser123"

# 테스트 기준 파티션 날짜
DT = "20260519"

TRANSFORMS = {
    "preorder": preorder.transform,
    "comments": comments.transform,
    "supporter": supporter.transform,
    "fundings": fundings.transform,
    "wishes": wishes.transform,
    "user_info": user_info.transform,
}

ALL_TABLES = list(TRANSFORMS)

# user id를 해싱하는 테이블 → 출력에서 원본이 사라졌는지 검증할 컬럼명
HASH_COLUMN = {
    "comments": "author_id_hash",
    "supporter": "user_id_hash",
    "fundings": "user_id_hash",
    "wishes": "user_id_hash",
    "user_info": "user_id_hash",
}

# 테이블별 대표 bronze 필드(camelCase 원천 형태를 섞어 실제 입력에 가깝게 구성)
_DEFAULTS = {
    "preorder": {
        "campaign_id": 1001,
        "title": "테스트 캠페인",
        "snapshot_ts": "2026-05-19T05:00:00",
        "achievementRate": 120.5,
        "targetAmount": 1_000_000,
        "totalBackedAmount": 1_200_000,
        "status": "OPEN",
        "productType": "PREORDER",
        "remainingDay": 3,
    },
    "comments": {
        "comment_id": "c1",
        "campaign_id": 1001,
        "commentType": "CAMPAIGN",
        "depth": 0,
        "userId": RAW_USER_ID,
        "createdAt": "2026-05-19T10:00:00",
        "body": "배송 언제인가요?",
    },
    "supporter": {
        "userId": RAW_USER_ID,
        "campaign_id": 1001,
        "supportType": "FUNDING",
        "amount": 50_000,
        "createdAt": "2026-05-19T09:00:00",
    },
    "fundings": {
        "userId": RAW_USER_ID,
        "campaign_id": 1001,
        "amount": 50_000,
        "title": "테스트 캠페인",
        "productType": "REWARD",
        "createdAt": "2026-05-19T09:00:00",
        "remainingDay": 3,
        "achievementRate": 120.0,
    },
    "wishes": {
        "userId": RAW_USER_ID,
        "campaign_id": 1001,
        "title": "테스트 캠페인",
        "makerName": "메이커",
        "snapshotAt": "2026-05-19T00:00:00",
        "achievementRate": 110.0,
        "remainingDay": 2,
        "amount": 30_000,
        "productType": "REWARD",
        "endYn": 0,
    },
    "user_info": {
        "userId": RAW_USER_ID,
        "signatureCnt": 5,
        "totalFundingCount": 4,
        "followerCnt": 10,
        "followingCnt": 3,
        "interestKeyword": ["a", "b", "c"],
        "collectedAt": "2026-05-19T00:00:00",
    },
}


def make_bronze(table: str, rows: int = 1, **overrides) -> pd.DataFrame:
    """해당 테이블의 최소 유효 bronze DataFrame을 만든다.

    rows>1이면 동일 행을 복제(중복 제거 테스트용).
    overrides로 특정 필드만 바꿔 경계값 테스트를 한다.
    """
    base = dict(_DEFAULTS[table])
    base.update(overrides)
    return pd.DataFrame([dict(base) for _ in range(rows)])
