#!/usr/bin/env python3
"""
pre_gate.py - Claude Code PreToolUse(Bash) hook. **선택(opt-in) 자산 - 기본 미등록.**
등록법: settings.local.json 의 hooks.PreToolUse 에 matcher "Bash" + command
"python3 .agent/scripts/pre_gate.py" 추가 (templates/settings.pretooluse.json.example 참조).

검사 항목:
  [1] 파괴적 명령 차단 (DENY) - rm -rf 루트급 / git push --force → main·master /
      DROP TABLE·DATABASE·SCHEMA / docker system·volume prune / mkfs / dd of=/dev/ /
      Windows rd·rmdir /s 드라이브 루트 / Remove-Item -Recurse -Force 드라이브 루트·~
  [2] 확인 요구 (ASK) - git reset --hard / git clean -f* / git checkout -- . / truncate
  [3] 커밋 게이트 - git commit 시 staged 파일 전체를 .agent/scripts/ci_gate_*.py 로 재검사,
      stderr 출력이 있으면 deny (--no-verify 로 우회 불가 - 훅 레벨 게이트)

프로젝트별 추가 패턴: .agent/config/bash_guard.json
  {"deny": ["<regex>", ...], "ask": ["<regex>", ...]}
  기본 패턴 제거는 불가 - 추가만 허용 (배포 킷 안전 기본값).

규율: fail-open (파싱 실패/예외/도구 부재 시 무출력 exit 0). 전체 5초 예산 -
무거운 검사 금지, 커밋 게이트는 시간 예산 초과 시 잔여 검사를 건너뛴다.

판정 출력 (stdout JSON, exit 0):
  {"hookSpecificOutput": {"hookEventName": "PreToolUse",
    "permissionDecision": "deny"|"ask", "permissionDecisionReason": "<사유>"}}
allow 면 아무것도 출력하지 않고 exit 0.
"""

import glob
import json
import os
import pathlib
import re
import subprocess
import sys
import time

# Windows 콘솔(cp949) 에서 한국어 판정 출력이 깨지지 않도록 UTF-8 강제 (3.7+).
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# 프로젝트 루트 - __file__ 기준 동적 감지 (Mac/Windows 양쪽 동작).
# 위치: <root>/.agent/scripts/ → parents[2] 가 프로젝트 루트.
PROJECT_ROOT = str(pathlib.Path(__file__).resolve().parents[2])

_START = time.monotonic()
_BUDGET_SEC = 4.5  # 훅 전체 5초 예산 내 안전 마진


# === DENY 기본 패턴 (제거 불가) ===
DEFAULT_DENY_PATTERNS = [
    # rm -rf 가 / · ~ · . 루트급 대상일 때 (rm -rf /home/x 등 하위 경로는 미매칭)
    (re.compile(
        r"\brm\s+(?:-{1,2}[\w-]+\s+)*-[A-Za-z]*(?:rf|fr)[A-Za-z]*\s+(?:-{1,2}[\w-]+\s+)*"
        r"[\"']?(?:/|~/?|\.{1,2}/?)\*?[\"']?\s*(?:$|[;&|]|\s)"),
     "rm -rf 루트급 대상(/ · ~ · .) - 파괴적 삭제 차단"),
    # git push --force / -f 가 main|master 대상 (플래그·브랜치 순서 무관)
    (re.compile(
        r"\bgit\s+push\b(?=.*(?:--force(?:-with-lease)?\b|\s-f\b))(?=.*\b(?:main|master)\b)"),
     "git push --force → main/master - 보호 브랜치 강제 푸시 차단"),
    (re.compile(r"(?i)\bDROP\s+(?:TABLE|DATABASE|SCHEMA)\b"),
     "SQL DROP TABLE/DATABASE/SCHEMA - 파괴적 DDL 차단"),
    (re.compile(r"\bdocker\s+(?:system|volume)\s+prune\b"),
     "docker system/volume prune - 데이터 소실 위험 차단"),
    (re.compile(r"\bmkfs(?:\.\w+)?\b"),
     "mkfs - 파일시스템 포맷 차단"),
    (re.compile(r"\bdd\b[^\n]*\bof=/dev/"),
     "dd of=/dev/* - 디바이스 직접 쓰기 차단"),
    # Windows: rd|rmdir /s 가 드라이브 루트(C:\ 등) 대상
    (re.compile(
        r"(?i)\b(?:rd|rmdir)\s+(?:/[sq]\s+)+[\"']?[A-Za-z]:[\\/]?[\"']?\s*(?:$|[;&|])"),
     "rd/rmdir /s 드라이브 루트 - 파괴적 삭제 차단"),
    # PowerShell: Remove-Item -Recurse -Force 가 드라이브 루트·~ 대상
    (re.compile(
        r"(?i)\bRemove-Item\b(?=[^\n]*-Recurse)(?=[^\n]*-Force)"
        r"(?=[^\n]*(?:\s|['\"])(?:[A-Za-z]:[\\/]?|~)['\"]?\s*(?:$|[;&|\s]))"),
     "Remove-Item -Recurse -Force 드라이브 루트/~ - 파괴적 삭제 차단"),
]

# === ASK 기본 패턴 (제거 불가) ===
DEFAULT_ASK_PATTERNS = [
    (re.compile(r"\bgit\s+reset\s+--hard\b"), "git reset --hard - 작업 내용 소실 가능"),
    (re.compile(r"\bgit\s+clean\s+-[A-Za-z]*f"), "git clean -f - 미추적 파일 삭제"),
    (re.compile(r"\bgit\s+checkout\s+--\s+\."), "git checkout -- . - 로컬 변경 폐기"),
    (re.compile(r"\btruncate\b"), "truncate - 파일 내용 소거"),
]

GIT_COMMIT_RE = re.compile(r"^\s*git\s+commit\b")


def _load_extra_patterns():
    """프로젝트별 추가 패턴 (.agent/config/bash_guard.json).
    기본 패턴 제거는 불가 - 추가만 허용."""
    extra_path = os.path.join(PROJECT_ROOT, ".agent", "config", "bash_guard.json")
    deny, ask = [], []
    try:
        with open(extra_path, encoding="utf-8") as f:
            cfg = json.load(f)
        for p in cfg.get("deny", []):
            try:
                deny.append((re.compile(p), f"프로젝트 추가 deny 패턴: {p}"))
            except Exception:
                pass
        for p in cfg.get("ask", []):
            try:
                ask.append((re.compile(p), f"프로젝트 추가 ask 패턴: {p}"))
            except Exception:
                pass
    except Exception:
        pass
    return deny, ask


def _emit(decision: str, reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }, ensure_ascii=False))


def _remaining_budget() -> float:
    return _BUDGET_SEC - (time.monotonic() - _START)


def _run(cmd, timeout):
    """subprocess 실행 - 실패/타임아웃 시 None (fail-open)."""
    try:
        return subprocess.run(
            cmd, cwd=PROJECT_ROOT, capture_output=True, text=True,
            encoding="utf-8", errors="ignore", timeout=timeout)
    except Exception:
        return None


def check_commit_gate(command: str):
    """[3] git commit 시 staged 파일을 ci_gate_*.py 로 재검사.
    stderr 출력이 하나라도 있으면 deny 사유 반환, 이상 없으면 None.
    --no-verify 가 있어도 우회 불가 (훅 레벨). 도구 부재/예산 초과 시 통과."""
    if not GIT_COMMIT_RE.match(command):
        return None
    gates = sorted(glob.glob(os.path.join(PROJECT_ROOT, ".agent", "scripts", "ci_gate_*.py")))
    if not gates:
        return None
    if _remaining_budget() < 1.0:
        return None
    diff = _run(["git", "diff", "--cached", "--name-only"], timeout=min(2.0, _remaining_budget()))
    if diff is None or diff.returncode != 0:
        return None
    staged = [ln.strip() for ln in diff.stdout.splitlines() if ln.strip()]
    for path in staged:
        abs_path = os.path.join(PROJECT_ROOT, path)
        if not os.path.isfile(abs_path):
            continue  # 삭제된 staged 파일 등
        for gate in gates:
            budget = _remaining_budget()
            if budget < 0.5:
                return None  # 예산 소진 - 잔여 검사 포기 (fail-open)
            res = _run([sys.executable, gate, abs_path], timeout=min(2.0, budget))
            if res is None:
                continue
            err = (res.stderr or "").strip()
            if err:
                summary = "\n".join(err.splitlines()[:6])[:500]
                return (f"커밋 게이트 실패 - CI Gate 위반이 staged 파일에 남아 있음 "
                        f"({path}):\n{summary}\n위반을 해소한 뒤 다시 커밋할 것 "
                        f"(--no-verify 로도 이 게이트는 우회되지 않음).")
    return None


def main() -> None:
    try:
        data = json.loads(sys.stdin.read())
    except Exception:
        return  # fail-open
    command = (
        (data.get("tool_input") or {}).get("command")
        or (data.get("toolInput") or {}).get("command")  # 구버전 호환
        or ""
    )
    if not command:
        return

    extra_deny, extra_ask = _load_extra_patterns()

    # [1] DENY
    for pat, reason in DEFAULT_DENY_PATTERNS + extra_deny:
        if pat.search(command):
            _emit("deny", f"차단됨: {reason}")
            return

    # [3] 커밋 게이트 (deny)
    gate_reason = check_commit_gate(command)
    if gate_reason:
        _emit("deny", gate_reason)
        return

    # [2] ASK
    for pat, reason in DEFAULT_ASK_PATTERNS + extra_ask:
        if pat.search(command):
            _emit("ask", f"확인 필요: {reason}")
            return

    # allow - 무출력 exit 0


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # fail-open
    sys.exit(0)
