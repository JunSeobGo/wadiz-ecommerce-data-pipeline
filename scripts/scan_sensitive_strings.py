"""공개 저장소에 민감정보가 섞여 들어갔는지 검사하는 스크립트.

이 프로젝트는 GitHub 공개용 데모라서, 실제 AWS 계정/네트워크 식별자나 인증키가
커밋되면 안 됩니다. 이 스크립트는 Git이 추적하는 텍스트 파일만 훑어서
'진짜 민감값'으로 보이는 패턴을 찾고, 발견되면 0이 아닌 종료코드를 반환합니다.

설계 원칙:
- placeholder(000000000000, subnet-xxxx, sg-xxxx, example.invalid 등)는 통과시킨다.
- 오탐으로 CI를 막지 않도록, 형태가 분명한 패턴만 검사한다.
- 실제 실행 시에만 쓰는 파일(.env 등)은 .gitignore로 이미 제외되어 검사 대상이 아니다.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# 검사 대상에서 제외할 경로 (자기 자신, 예시 파일 등)
EXCLUDED_FILES = {
    "scripts/scan_sensitive_strings.py",  # 패턴 문자열이 들어있는 자기 자신
}

# 텍스트가 아닌 확장자는 건너뛴다.
SKIP_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf",
    ".parquet", ".avro", ".orc", ".gz", ".zip", ".tar",
    ".xlsx", ".xls",
}

# placeholder로 허용되는 값들 (발견돼도 문제없음)
ALLOWED = {
    "000000000000",
    "subnet-xxxxxxxx",
    "subnet-yyyyyyyy",
    "sg-xxxxxxxx",
    "example.invalid",
}

# (이름, 정규식) 목록. 매칭되면 잠재적 민감값으로 본다.
PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # AWS 액세스 키 ID
    ("aws_access_key_id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    # 프라이빗 키 블록
    ("private_key_block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    # ARN 안의 실제 AWS 계정 ID (전부 0인 placeholder는 제외)
    ("aws_account_id_in_arn", re.compile(r"arn:aws:[^:]*:[^:]*:(?!000000000000)\d{12}:")),
    # ECR 이미지 URI 안의 실제 계정 ID
    ("aws_account_id_in_ecr", re.compile(r"(?!000000000000)\d{12}\.dkr\.ecr\.")),
    # 실제 서브넷/보안그룹 ID (placeholder는 x/y 라서 hex에 안 걸림)
    ("real_subnet_id", re.compile(r"\bsubnet-[0-9a-f]{8,17}\b")),
    ("real_security_group_id", re.compile(r"\bsg-[0-9a-f]{8,17}\b")),
]


def tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line.strip() for line in out.stdout.splitlines() if line.strip()]


def scan_file(rel_path: str) -> list[tuple[int, str, str]]:
    findings: list[tuple[int, str, str]] = []
    abs_path = ROOT / rel_path
    try:
        text = abs_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, FileNotFoundError):
        return findings

    for lineno, line in enumerate(text.splitlines(), start=1):
        for name, pattern in PATTERNS:
            for match in pattern.finditer(line):
                if match.group(0) in ALLOWED:
                    continue
                findings.append((lineno, name, match.group(0)))
    return findings


def main() -> int:
    all_findings: list[tuple[str, int, str, str]] = []
    for rel_path in tracked_files():
        if rel_path in EXCLUDED_FILES:
            continue
        if Path(rel_path).suffix.lower() in SKIP_SUFFIXES:
            continue
        for lineno, name, value in scan_file(rel_path):
            all_findings.append((rel_path, lineno, name, value))

    if all_findings:
        print("민감정보로 의심되는 값이 발견되었습니다:")
        for rel_path, lineno, name, value in all_findings:
            print(f"  - {rel_path}:{lineno} [{name}] {value}")
        print(f"\n총 {len(all_findings)}건. 커밋 전에 마스킹하거나 placeholder로 교체하세요.")
        return 1

    print("민감정보 스캔 통과: 의심 패턴 없음")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
