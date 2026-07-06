#!/usr/bin/env python3
"""archive_tasks.py - status 기준 task 폴더 아카이브 (선택 자산)

.agent/tasks/ 직하의 task_*/ (task_harness_* 포함) 폴더를 대상으로,
각 폴더의 plan.md YAML frontmatter 에 있는 `status:` 값을 읽어 판정한다:

- status: done   → archive 대상 (.agent/tasks/archive/ 로 이동)
- status: active → 유지
- frontmatter 또는 status 없음 → 폴더 mtime 이 임계(기본 120분) 초과면
  archive 대상으로 fallback 판정하고 "[FALLBACK mtime]" 표기

사용법:
    python .agent/scripts/archive_tasks.py            # dry-run (기본) - 대상 목록만 출력
    python .agent/scripts/archive_tasks.py --apply    # 실제 이동 실행
    python .agent/scripts/archive_tasks.py --minutes 60   # fallback mtime 임계 조정

- plan 워크플로 진입 시(plan_<project> / plan_harness) 자동 archive 단계에서
  `python .agent/scripts/archive_tasks.py --apply` 를 호출한다.
- 선택 자산 - 스크립트가 없으면 기존 find/PowerShell 룰(mtime 기준)을 사용한다.
- Python 3.7+ 표준 라이브러리만 사용 (PyYAML 등 외부 의존성 없음).
- fail-open: 예기치 못한 예외 시 조용히 통과한다 (exit 0).
"""

import argparse
import os
import re
import shutil
import sys
import time

STATUS_RE = re.compile(r"^status:\s*([A-Za-z0-9_-]+)", re.MULTILINE)

# Windows cp949 콘솔 등에서 인코딩 불가 문자로 죽지 않도록 (Python 3.7+)
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(errors="replace")
        except Exception:
            pass


def find_tasks_dir():
    """cwd 기준 우선, 없으면 스크립트 위치(.agent/scripts/) 기준으로 탐지."""
    cand = os.path.join(os.getcwd(), ".agent", "tasks")
    if os.path.isdir(cand):
        return cand
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cand = os.path.normpath(os.path.join(script_dir, "..", "tasks"))
    if os.path.isdir(cand):
        return cand
    return None


def read_frontmatter_status(plan_path):
    """plan.md 첫 --- 블록에서 status 값을 간이 파싱. 없으면 None."""
    try:
        with open(plan_path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        return None
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    # 첫 --- 이후 닫는 --- 까지가 frontmatter
    end = None
    for i in range(1, min(len(lines), 50)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return None
    block = "\n".join(lines[1:end])
    m = STATUS_RE.search(block)
    if not m:
        return None
    return m.group(1).lower()


def judge(task_dir, minutes):
    """(archive 여부, 판정 근거 문자열) 반환."""
    plan_path = os.path.join(task_dir, "plan.md")
    status = read_frontmatter_status(plan_path) if os.path.isfile(plan_path) else None
    if status == "done":
        return True, "status: done"
    if status == "active":
        return False, "status: active"
    if status is not None:
        # 알 수 없는 status 값 - 안전하게 유지
        return False, "status: %s (알 수 없는 값 - 유지)" % status
    # frontmatter/status 없음 → mtime fallback
    try:
        age_min = (time.time() - os.path.getmtime(task_dir)) / 60.0
    except OSError:
        return False, "[FALLBACK mtime] mtime 확인 불가 - 유지"
    if age_min > minutes:
        return True, "[FALLBACK mtime] %d분 경과 (임계 %d분)" % (int(age_min), minutes)
    return False, "[FALLBACK mtime] %d분 경과 - 임계(%d분) 미만, 유지" % (int(age_min), minutes)


def unique_dest(archive_dir, name):
    """동명 폴더가 있으면 -1, -2 ... suffix 를 붙인 경로 반환."""
    dest = os.path.join(archive_dir, name)
    n = 0
    while os.path.exists(dest):
        n += 1
        dest = os.path.join(archive_dir, "%s-%d" % (name, n))
    return dest


def main():
    parser = argparse.ArgumentParser(
        description="status 기준 task 폴더 아카이브 (기본 dry-run)")
    parser.add_argument("--apply", action="store_true",
                        help="실제 이동 실행 (기본은 dry-run)")
    parser.add_argument("--minutes", type=int, default=120,
                        help="frontmatter 없을 때 mtime fallback 임계 (분, 기본 120)")
    args = parser.parse_args()

    tasks_dir = find_tasks_dir()
    if tasks_dir is None:
        print(".agent/tasks 디렉토리를 찾지 못함 - 아무것도 하지 않음")
        return 0

    archive_dir = os.path.join(tasks_dir, "archive")
    targets = []   # (경로, 근거)
    keeps = []     # (경로, 근거)
    for entry in sorted(os.listdir(tasks_dir)):
        path = os.path.join(tasks_dir, entry)
        if not os.path.isdir(path):
            continue
        if not entry.startswith("task_"):
            continue
        do_archive, reason = judge(path, args.minutes)
        if do_archive:
            targets.append((path, reason))
        else:
            keeps.append((path, reason))

    mode = "APPLY" if args.apply else "DRY-RUN"
    print("[archive_tasks] 모드: %s / 대상 %d개 / 유지 %d개" % (mode, len(targets), len(keeps)))
    for path, reason in keeps:
        print("  유지     %s  (%s)" % (os.path.basename(path), reason))
    for path, reason in targets:
        print("  archive  %s  (%s)" % (os.path.basename(path), reason))

    if not args.apply:
        if targets:
            print("dry-run - 실제 이동하려면 --apply 를 붙여 실행")
        return 0

    if targets and not os.path.isdir(archive_dir):
        os.makedirs(archive_dir)
    for path, reason in targets:
        dest = unique_dest(archive_dir, os.path.basename(path))
        shutil.move(path, dest)
        print("  이동 완료: %s -> %s" % (os.path.basename(path), os.path.relpath(dest, tasks_dir)))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # fail-open - 예외 시 조용히 통과
        print("[archive_tasks] 예외 발생 - 통과: %s" % e, file=sys.stderr)
        sys.exit(0)
