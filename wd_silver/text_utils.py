from __future__ import annotations

import html
import re

import pandas as pd

HTML_TAG_RE = re.compile(r'<[^>]+>')
WHITESPACE_RE = re.compile(r'\s+')
CONTROL_CHAR_RE = re.compile(r'[\x00-\x1f\x7f]')

POSITIVE_KEYWORDS = ['기대', '좋아요', '좋습니다', '만족', '예쁘', '편하', '기다렸', '응원', '구매완료', '추천', '감사', '최고']
NEGATIVE_KEYWORDS = ['배송', '언제', '취소', '환불', '불량', '늦', '실망', '문의', '문제', '안됨', '고장', '누락', '교환', '지연']
KEYWORD_GROUP_RULES = {
    'delivery': ['배송', '출고', '도착', '택배', '지연'],
    'refund_cancel': ['환불', '취소', '교환', '반품'],
    'quality_issue': ['불량', '고장', '문제', '하자', '누락'],
    'expectation': ['기대', '기다렸', '응원'],
    'purchase_intent': ['구매', '결제', '펀딩', '재구매'],
    'usage': ['사용', '설치', '방법', '문의'],
}


def clean_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ''
    text = html.unescape(str(value))
    text = HTML_TAG_RE.sub(' ', text)
    text = CONTROL_CHAR_RE.sub(' ', text)
    text = WHITESPACE_RE.sub(' ', text)
    return text.strip()


def sentiment_label_and_score(text: str) -> tuple[str, int]:
    positive_hits = sum(1 for keyword in POSITIVE_KEYWORDS if keyword in text)
    negative_hits = sum(1 for keyword in NEGATIVE_KEYWORDS if keyword in text)
    if positive_hits > negative_hits:
        return 'positive', 1
    if negative_hits > positive_hits:
        return 'negative', -1
    return 'neutral', 0


def keyword_groups(text: str) -> str:
    groups = [group for group, keywords in KEYWORD_GROUP_RULES.items() if any(keyword in text for keyword in keywords)]
    return ','.join(groups)
