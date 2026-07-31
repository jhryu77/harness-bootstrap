#!/usr/bin/env python3
"""
stop_gate.py - Claude Code Stop hook. **선택(opt-in) 자산 - 기본 미등록. advisory 전용.**
등록법: settings.local.json 의 hooks.Stop 에 command "python3 .agent/scripts/stop_gate.py"
추가 (templates/settings.pretooluse.json.example 참조 - Stop 은 matcher 불필요).
스크립트는 templates/scripts/stop_gate.py 를 .agent/scripts/stop_gate.py 로 복사해 사용.

역할: 턴 종료(Stop) 시 git 변경 파일 전체를 .agent/scripts/ci_gate_*.py 로 일괄 검사해
per-file PostToolUse 가 못 잡는 광역 회귀(예: 공유 모듈 수정의 영향 파일)를 경고한다.

규율:
  [1] stop_hook_active 가 truthy 면 즉시 무출력 exit 0 - Stop 훅 재진입 루프 방지 (최우선 가드)
  [2] 커밋당 1회 - .agent/tasks/.stop_gate_head 에 기록된 HEAD SHA 와 같으면 생략
  [3] 변경 파일 30개 초과 시 앞 30개만 검사, 나머지는 "외 N개 미검사" 표기 (5초 예산)
  [4] advisory 전용 - 위반 시 stdout JSON {"systemMessage": ...} 경고만.
      **어떤 경우에도 차단(block) 출력을 내지 않는다.**
  [5] fail-open - git 부재/파싱 실패/모든 예외 시 무출력 exit 0
"""

import glob
import json
import os
import pathlib
import subprocess
import sys
import time

# Windows 콘솔(cp949) 에서 한국어 출력이 깨지지 않도록 UTF-8 강제 (3.7+).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# 프로젝트 루트 - __file__ 기준 동적 감지 (Mac/Windows 양쪽 동작).
# 위치: <root>/.agent/scripts/ → parents[2] 가 프로젝트 루트.
PROJECT_ROOT = str(pathlib.Path(__file__).resolve().parents[2])

_START = time.monotonic()
_BUDGET_SEC = 4.5  # 훅 전체 5초 예산 내 안전 마진
_MAX_FILES = 30    # 광역 검사 상한 - 초과분은 "외 N개 미검사" 표기
_MAX_LINES = 5     # systemMessage 에 표기할 위반 요약 최대 줄 수

HEAD_MARKER = os.path.join(PROJECT_ROOT, ".agent", "tasks", ".stop_gate_head")


def _remaining_budget() -> float:
    return _BUDGET_SEC - (time.monotonic() - _START)


def _run(cmd, timeout):
    """subprocess 실행 - 실패/타임아웃 시 None (fail-open)."""
    try:
        return subprocess.run(
            cmd, cwd=PROJECT_ROOT, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout)
    except Exception:
        return None


def _changed_files():
    """git status --porcelain 에서 변경(M/A/??) 파일 목록. git 실패 시 None."""
    res = _run(["git", "status", "--porcelain"],
               timeout=min(2.0, max(_remaining_budget(), 0.1)))
    if res is None or res.returncode != 0:
        return None
    files = []
    for line in res.stdout.splitlines():
        if len(line) < 4:
            continue
        status, path = line[:2], line[3:].strip()
        if not any(c in status for c in ("M", "A", "?")):
            continue  # 삭제(D)/rename-only 등은 검사 대상 아님
        if " -> " in path:  # rename/copy - 새 경로만
            path = path.split(" -> ", 1)[1].strip()
        path = path.strip('"')
        files.append(path)
    return files


def _check_files(files, gates):
    """각 파일을 ci_gate 로 서브프로세스 검사 - stderr 출력 파일을 (경로, 요약) 으로 수집."""
    violations = []
    for path in files:
        abs_path = os.path.join(PROJECT_ROOT, path)
        if not os.path.isfile(abs_path):
            continue
        for gate in gates:
            budget = _remaining_budget()
            if budget < 0.5:
                return violations  # 예산 소진 - 잔여 검사 포기 (fail-open)
            res = _run([sys.executable, gate, abs_path], timeout=min(1.5, budget))
            if res is None:
                continue
            err = (res.stderr or "").strip()
            if err:
                violations.append((path, err.splitlines()[0][:200]))
                break  # 파일당 위반 1건이면 충분
    return violations


def main() -> None:
    try:
        data = json.loads(sys.stdin.read())
    except Exception:
        return  # fail-open

    # [1] Stop 훅 재진입 루프 방지 - 최우선 가드
    if data.get("stop_hook_active"):
        return

    # [2] 커밋당 1회 - HEAD SHA 대조
    res = _run(["git", "rev-parse", "HEAD"], timeout=2.0)
    if res is None or res.returncode != 0:
        return  # git 부재/HEAD 없음 - fail-open
    head = res.stdout.strip()
    try:
        with open(HEAD_MARKER, encoding="utf-8") as f:
            if f.read().strip() == head:
                return  # 이 커밋에서 이미 advisory 수행
    except Exception:
        pass  # 마커 없음/읽기 실패 - 검사 진행

    # [3] 광역 검사
    files = _changed_files()
    if files is None:
        return  # fail-open (HEAD 기록 없이 종료 - 다음 Stop 에서 재시도)
    gates = sorted(glob.glob(os.path.join(PROJECT_ROOT, ".agent", "scripts", "ci_gate_*.py")))
    skipped = max(len(files) - _MAX_FILES, 0)
    violations = _check_files(files[:_MAX_FILES], gates) if gates else []

    # 검사 완료 - 현재 HEAD 기록 (커밋당 1회)
    try:
        os.makedirs(os.path.dirname(HEAD_MARKER), exist_ok=True)
        with open(HEAD_MARKER, "w", encoding="utf-8") as f:
            f.write(head + "\n")
    except Exception:
        pass

    # [4] advisory 출력 - 위반 없으면 무출력. 차단(block) 출력은 절대 내지 않는다.
    if violations:
        lines = [f"{p}: {s}" for p, s in violations[:_MAX_LINES]]
        msg = f"[stop_gate advisory] 위반 {len(violations)}건:\n" + "\n".join(lines)
        if len(violations) > _MAX_LINES:
            msg += f"\n(외 위반 {len(violations) - _MAX_LINES}건 생략)"
        if skipped:
            msg += f"\n외 {skipped}개 미검사"
        msg += " - 차단 아님, 커밋 전 정리 권장"
        print(json.dumps({"systemMessage": msg}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # fail-open
    sys.exit(0)
