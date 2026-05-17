from __future__ import annotations

import os

import requests


def _source_base_url() -> str:
    """공개 저장소에는 실제 원천 도메인을 남기지 않는다.

    실제 실행 시에는 개인 .env 또는 ECS 환경변수에서 SOURCE_BASE_URL을 주입한다.
    DEMO_MODE 기본값에서는 example.invalid를 사용하므로 외부 사이트로 요청이 나가지 않는다.
    """
    return os.getenv('SOURCE_BASE_URL', 'https://example.invalid').rstrip('/')


def default_headers() -> dict[str, str]:
    base_url = _source_base_url()
    return {
        'accept': '*/*',
        'accept-language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'content-type': 'application/json',
        'origin': base_url,
        'referer': f'{base_url}/',
        'user-agent': os.getenv(
            'SOURCE_USER_AGENT',
            'Mozilla/5.0 (compatible; portfolio-demo-bot/1.0)',
        ),
        'wadiz-country': 'KR',
        'wadiz-language': 'ko',
    }


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(default_headers())
    return session
