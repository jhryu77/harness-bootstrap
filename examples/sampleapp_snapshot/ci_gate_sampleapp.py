#!/usr/bin/env python3
"""
ci_gate_sampleapp.py
Claude Code PostToolUse(Edit|Write) hook.
정상 시 무출력. 위반 시 stderr 로 Claude 컨텍스트에 주입.

검사 항목 (3개):
  [1] 파일 위치       - 임시 파일(tmp_*/verify_*/diag_*/check_*) 루트 직접 생성 금지 (tmp/ 폴더만 허용)
  [2] 시크릿 하드코딩 - JWT/AWS/Google API/GitHub PAT/PEM Private Key
  [3] Kotlin 괄호    - .kt/.kts 의 { } 매칭 경량 카운트 체크

진입점:
  - 인자 직접 호출:  python ci_gate_sampleapp.py <path>
  - PostToolUse hook: stdin JSON (file_path / path / toolInput.file_path 모두 지원)
"""

import sys
import os
import re
import json
import pathlib

# 프로젝트 루트 - __file__ 기준 동적 감지 (Mac/Windows 양쪽 동작).
# ci_gate_sampleapp.py 위치: <root>/.agent/scripts/ → parents[2] 가 프로젝트 루트.
PROJECT_ROOT = str(pathlib.Path(__file__).resolve().parents[2])

# === 검사 1: 임시 파일 prefix 패턴 ===
TMP_PATTERNS = ("tmp_", "verify_", "diag_", "check_")

# === 검사 2: 시크릿 정규식 ===
SECRET_PATTERNS = [
    (re.compile(r"eyJ[A-Za-z0-9._-]{40,}"), "JWT"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS Access Key"),
    (re.compile(r"AIza[0-9A-Za-z_-]{35}"), "Google API Key"),
    (re.compile(r"ghp_[A-Za-z0-9]{36}"), "GitHub PAT"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{82}"), "GitHub fine-grained PAT"),
    (re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"), "PEM Private Key"),
]


def _is_kotlin(path: str) -> bool:
    return path.endswith((".kt", ".kts"))


def _rel_to_root(path: str) -> str:
    """프로젝트 루트 기준 상대 경로. 루트 외부면 절대 경로 반환."""
    try:
        return os.path.relpath(os.path.abspath(path), os.path.abspath(PROJECT_ROOT))
    except ValueError:
        return path


def check_tmp_location(path: str):
    """검사 1: 임시 파일 prefix 가 루트 직접 배치되어 있는지."""
    base = os.path.basename(path)
    rel = _rel_to_root(path)
    # 루트 직접 배치 = 상대 경로에 디렉토리 구분자가 없음
    is_root_level = ("\\" not in rel) and ("/" not in rel)
    if any(base.startswith(p) for p in TMP_PATTERNS) and is_root_level:
        return f"임시 파일 prefix({base.split('_', 1)[0]}_*)는 tmp/ 폴더에 생성하세요. 루트 직접 배치 금지."
    return None


def check_secrets(path: str, content: str):
    """검사 2: 하드코딩 시크릿 감지. 검출 시 종류 명시."""
    for pat, label in SECRET_PATTERNS:
        if pat.search(content):
            return f"하드코딩 시크릿 감지({label}) - 환경변수/secrets.properties 사용. 절대 커밋 금지."
    return None


def check_kotlin_braces(path: str, content: str):
    """검사 3: Kotlin 중괄호 매칭 경량 카운트 (문자열·주석 정밀 파싱 안 함)."""
    if not _is_kotlin(path):
        return None
    opens = content.count("{")
    closes = content.count("}")
    if opens != closes:
        return f"Kotlin 괄호 불일치: '{{' {opens} 개 / '}}' {closes} 개"
    return None


def gate(path: str) -> None:
    if not path or not os.path.isfile(path):
        return

    rel = _rel_to_root(path)

    # 검사 1: 파일 내용 읽기 전 위치 체크
    loc_msg = check_tmp_location(path)
    if loc_msg:
        print(f"\n[CI Gate FAIL] 파일 위치: {rel}\n  {loc_msg}\n", file=sys.stderr)
        return

    # 파일 내용 로드
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception:
        return

    # 검사 2, 3
    hits = []
    for name, fn in (("secrets", check_secrets), ("kotlin_braces", check_kotlin_braces)):
        msg = fn(path, content)
        if msg:
            hits.append((name, msg))

    if hits:
        print(f"\n[CI Gate WARN] {rel}", file=sys.stderr)
        for name, msg in hits:
            print(f"  - {name}: {msg}", file=sys.stderr)
        print("", file=sys.stderr)


def _resolve_path_from_stdin() -> str:
    """PostToolUse hook 의 stdin JSON 에서 file_path 추출."""
    try:
        data = json.loads(sys.stdin.read())
    except Exception:
        return ""
    return (
        data.get("file_path")
        or data.get("path")
        or (data.get("toolInput") or {}).get("file_path")
        or (data.get("tool_input") or {}).get("file_path")
        or ""
    )


def main():
    # 직접 호출: python ci_gate_sampleapp.py <path>
    if len(sys.argv) > 1:
        gate(sys.argv[1])
        return
    # hook 진입: stdin JSON 파싱
    if not sys.stdin.isatty():
        fp = _resolve_path_from_stdin()
        if fp:
            gate(fp)


if __name__ == "__main__":
    main()
