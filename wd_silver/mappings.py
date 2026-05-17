from __future__ import annotations

CATEGORY_NAME_MAP = {'TECH': '테크/가전', 'FASHION': '패션/잡화', 'BEAUTY': '뷰티', 'FOOD': '푸드', 'LIVING': '리빙'}
STATUS_MAP = {'OPEN': '진행중', 'COMING_SOON': '오픈예정', 'CLOSED': '종료', 'SUCCESS': '성공', 'FAILED': '실패'}
BIZ_MODEL_MAP = {'PREORDER': '예약구매', 'FUNDING': '펀딩', 'STORE': '스토어'}


def map_category_name(value: object) -> str | None:
    if value is None:
        return None
    raw = str(value).strip()
    return CATEGORY_NAME_MAP.get(raw, raw or None)


def map_status(value: object) -> str | None:
    if value is None:
        return None
    raw = str(value).strip()
    return STATUS_MAP.get(raw, raw or None)


def map_biz_model(value: object) -> str | None:
    if value is None:
        return None
    raw = str(value).strip()
    return BIZ_MODEL_MAP.get(raw, raw or None)
