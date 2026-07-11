#!/usr/bin/env python3
"""Claude Code 전역 statusLine - 모델/폴더/git 브랜치/세션 이름 + 컨텍스트(CW) / 5시간(5H) / 7일(7D) 사용량.

표시 예:
  Opus 4.8 (1M) v2.1.198 [high] | my_project | develop | my-session
  CW ▓▓▓▓░░░░░░  43% | 5H ▓▓▓▓▓▓░░░░  61% (1h47m) | 7D ▓▓░░░░░░░░  16% (2d0h) | $34.43

Claude Code 가 stdin 으로 넘겨주는 공식 세션 JSON 만 사용한다 (외부 의존성 없음).
- context_window.used_percentage        : 컨텍스트 사용률 (모든 사용자)
- rate_limits.five_hour.used_percentage : 5시간 rate limit (Claude.ai Pro/Max, 첫 API 응답 후)
- rate_limits.seven_day.used_percentage : 7일 rate limit  (동일)
- rate_limits.*.resets_at               : reset 시각 (epoch 초) → 남은 시간 카운트다운
- effort.level                          : /effort 상태 (low/medium/high/xhigh/max). 모델 미지원 시 부재. 강도색 [high] 로 표시
- session_name                          : --name 플래그 또는 /rename 으로 설정한 커스텀 세션 이름 (없으면 표시 안 함)
필드 부재 / null 은 우아하게 처리한다.

stdin 을 명시적으로 UTF-8 로 재설정한다 - Windows 환경에서 Python 의 stdin 기본 인코딩이
콘솔 코드페이지(cp949 등)를 따라가 한글 등 비 ASCII 필드(session_name 등)가 읽는 시점부터
깨지는 문제를 막는다.

설치 [필수 - 하네스 부트스트랩 시 반드시 반영] (플레이스홀더 치환 불필요 - 그대로 복사):
1. 이 파일을 ~/.claude/statusline.py 로 복사
2. ~/.claude/settings.json 에 등록 (command 는 인터프리터 감지형 - macOS(python3 전용)/Windows(python) 공용):
   "statusLine": { "type": "command", "command": "sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 <HOME>/.claude/statusline.py || exec python <HOME>/.claude/statusline.py'", "padding": 0, "refreshInterval": 60 }
셸: macOS=sh / Windows=git-bash(기본; PowerShell 폴백 환경은 git-bash 필요). 의존성: python 3.7+, git(선택).
   (bare `python <HOME>/.claude/statusline.py` 는 macOS 에서 python 부재로 상태바가 안 뜬다 - 감지형 필수.)

[권장] "refreshInterval"(초 단위, 최소 1)로 **세션 유휴 상태에서도 갱신**되게 한다: `"refreshInterval": 60`(60초=1분).
5H/7D reset 카운트다운·시계·백그라운드 서브에이전트의 git 변화 등 시간 기반 표시가 이벤트 없이도 최신화된다.
Claude Code 공식 문서(code.claude.com/docs statusline)상 이벤트 기반 갱신을 대체하지 않고 **추가로** 동작하며,
statusLine 은 로컬 스크립트 실행이라 API 토큰을 소비하지 않는다.
"""
import sys
import json
import os
import time

R = "\033[0m"
DIM = "\033[2m"
CYAN = "\033[36m"
BLUE = "\033[34m"
MAG = "\033[35m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
WHITE = "\033[97m"


def clean_text(s):
    """JSON 에서 온 문자열의 손상된 서로게이트 문자 제거 (session_name 등에서 발생 가능)."""
    if not s:
        return s
    try:
        return s.encode("utf-8", "replace").decode("utf-8", "replace")
    except Exception:
        return ""


def color_for(p):
    if p is None:
        return DIM
    if p < 60:
        return GREEN
    if p < 85:
        return YELLOW
    return RED


def effort_color(e):
    """reasoning effort(/effort) 강도 색 - 낮을수록 차분, 높을수록 뜨겁게."""
    return {"low": GREEN, "medium": CYAN, "high": YELLOW, "xhigh": MAG, "max": RED}.get(e, DIM)


def bar(p, width=10):
    """10칸 막대. 채움 ▓ / 빈칸 ░, 사용률에 따라 색."""
    if p is None:
        return DIM + "-" * width + R
    filled = max(0, min(width, round(p / 100 * width)))
    return color_for(p) + "▓" * filled + DIM + "░" * (width - filled) + R


def pct_str(p):
    if p is None:
        return DIM + "  -" + R
    return color_for(p) + f"{int(round(p)):3d}%" + R


def reset_in(ts):
    """resets_at(epoch 초)까지 남은 시간을 압축 표기. 예: 2h07m / 3d14h / 42m."""
    if not ts:
        return ""
    try:
        s = int(ts) - int(time.time())
    except Exception:
        return ""
    if s <= 0:
        return ""
    m = s // 60
    d, rem = divmod(m, 1440)
    h, m = divmod(rem, 60)
    if d:
        txt = f"{d}d{h}h"
    elif h:
        txt = f"{h}h{m:02d}m"
    else:
        txt = f"{max(m, 1)}m"
    return f" {DIM}({txt}){R}"


def git_branch(cwd):
    """현재 브랜치명. subprocess 없이 .git/HEAD 직접 파싱 (statusLine 타임아웃 회피).
    repo 아니면 빈 문자열. detached HEAD 는 short sha."""
    try:
        d = os.path.abspath(cwd)
        head = None
        for _ in range(8):  # 상위로 올라가며 .git 탐색
            g = os.path.join(d, ".git")
            if os.path.isdir(g):
                head = os.path.join(g, "HEAD")
                break
            if os.path.isfile(g):  # worktree/submodule: "gitdir: <path>"
                with open(g, encoding="utf-8") as f:
                    ln = f.read().strip()
                if ln.startswith("gitdir:"):
                    head = os.path.join(ln.split(":", 1)[1].strip(), "HEAD")
                break
            parent = os.path.dirname(d)
            if parent == d:
                break
            d = parent
        if not head or not os.path.isfile(head):
            return ""
        with open(head, encoding="utf-8") as f:
            ref = f.read().strip()
        if ref.startswith("ref: refs/heads/"):
            return ref[len("ref: refs/heads/"):]
        return ref[:7] if ref else ""
    except Exception:
        return ""


def main():
    try:
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", newline="\n")
    except Exception:
        pass

    model = (data.get("model") or {}).get("display_name", "?")
    version = data.get("version")
    effort = (data.get("effort") or {}).get("level")  # /effort: low/medium/high/xhigh/max (모델 미지원 시 부재)

    cw = data.get("context_window") or {}
    size = cw.get("context_window_size")
    size_lbl = "1M" if size == 1000000 else ("200K" if size == 200000 else (str(size) if size else ""))
    cw_pct = cw.get("used_percentage")

    rl = data.get("rate_limits") or {}
    five = (rl.get("five_hour") or {}).get("used_percentage")
    week = (rl.get("seven_day") or {}).get("used_percentage")
    five_rst = (rl.get("five_hour") or {}).get("resets_at")
    week_rst = (rl.get("seven_day") or {}).get("resets_at")

    cwd = (data.get("workspace") or {}).get("current_dir") or data.get("cwd") or "."
    folder = os.path.basename(cwd.rstrip("/\\")) or cwd
    cost = (data.get("cost") or {}).get("total_cost_usd")

    model_lbl = f"{CYAN}{model}{R}"
    if size_lbl:
        model_lbl += f" {DIM}({size_lbl}){R}"
    if version:
        model_lbl += f" {DIM}v{version}{R}"
    if effort:
        model_lbl += f" {DIM}[{R}{effort_color(effort)}{effort}{R}{DIM}]{R}"

    branch = git_branch(cwd)
    session_name = clean_text(data.get("session_name"))

    line1 = f"{model_lbl} {DIM}|{R} {BLUE}{folder}{R}"
    if branch:
        line1 += f" {DIM}|{R} {MAG}{branch}{R}"
    if session_name:
        line1 += f" {DIM}|{R} {WHITE}{session_name}{R}"

    parts = [f"{DIM}CW{R} {bar(cw_pct)} {pct_str(cw_pct)}"]
    if five is not None or week is not None:
        parts.append(f"{DIM}5H{R} {bar(five)} {pct_str(five)}{reset_in(five_rst)}")
        parts.append(f"{DIM}7D{R} {bar(week)} {pct_str(week)}{reset_in(week_rst)}")
    if cost:
        parts.append(f"{DIM}${cost:.2f}{R}")
    line2 = f" {DIM}|{R} ".join(parts)

    print(line1)
    print(line2)


if __name__ == "__main__":
    main()
