#!/usr/bin/env python3
"""
model_policy.py - 서브에이전트 model 정책(tier) 일괄 적용.
`.claude/agents/*.md` 를 파일명 규칙(plan_harness / eval_harness / plan_<project> /
eval_<project>)으로 분류한 뒤, 확정 매핑표(high/medium/low/inherit)에 따라 frontmatter 의
`model:` 값만 교체한다 (다른 줄은 건드리지 않음).
선택 자산 - 없어도 하네스는 동작한다 (모든 서브에이전트 기본값은 model: inherit).

사용법:
  python .agent/scripts/model_policy.py set <high|medium|low|inherit>
  python .agent/scripts/model_policy.py show
"""

import argparse
import pathlib
import re
import sys

# Windows cp949 등 콘솔 인코딩에서 UnicodeEncodeError 로 죽지 않도록 (UTF-8 강제 + '?' 대체)
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

TIERS = ("high", "medium", "low", "inherit")

# 확정 모델 정책 매핑표 (사용자 승인 완료 - 임의 변경 금지).
# 근거: plan_<project> 는 영향 평가/변경 순서 판단처럼 깊은 추론이 필요해 high/medium 모두
# opus 유지. eval_<project> 는 증거 기반 판정("의심되면 FAIL" 하드룰)이 핵심이라 opus/sonnet
# 로 한 단계만 낮춘다. plan_harness/eval_harness 는 메타 작업(빈도 낮음, 영향 범위 하네스
# 자체로 국한)이라 한 단계 더 낮게 잡는다. low 에서는 코드/하네스 구분 없이 sonnet/haiku 로
# 수렴시켜 정책 단계를 단순하게 유지한다.
MODEL_POLICY = {
    "plan_harness": {"high": "sonnet", "medium": "sonnet", "low": "haiku", "inherit": "inherit"},
    "eval_harness": {"high": "sonnet", "medium": "sonnet", "low": "haiku", "inherit": "inherit"},
    "plan_project": {"high": "opus", "medium": "opus", "low": "sonnet", "inherit": "inherit"},
    "eval_project": {"high": "opus", "medium": "sonnet", "low": "sonnet", "inherit": "inherit"},
}

CATEGORY_LABELS = {
    "plan_harness": "plan_harness",
    "eval_harness": "eval_harness",
    "plan_project": "plan_<project>",
    "eval_project": "eval_<project>",
}

# plan_<project>/eval_<project> 패턴 - release 워크플로의 plan_<release>.md (예: plan_ota_release.md)
# 도 이 정규식에 매칭되어 "plan_project" 행으로 처리된다. 별도 행은 없다.
RE_PLAN_PROJECT = re.compile(r"^plan_[a-z0-9_]+\.md$")
RE_EVAL_PROJECT = re.compile(r"^eval_[a-z0-9_]+\.md$")

MODEL_LINE_RE = re.compile(r"^(model:\s*)(\S+)(.*)$")


def classify_filename(name: str):
    """kit-managed 에이전트 파일명 분류 규칙 (이 순서로 매칭).
    1) plan_harness.md 정확히 일치
    2) eval_harness.md 정확히 일치
    3) plan_[a-z0-9_]+.md (1 제외) - plan_<project> (release 워크플로의 plan_<release>.md 포함)
    4) eval_[a-z0-9_]+.md (2 제외) - eval_<project>
    5) 그 외 - None (kit-managed 명명 규칙 밖)"""
    if name == "plan_harness.md":
        return "plan_harness"
    if name == "eval_harness.md":
        return "eval_harness"
    if RE_PLAN_PROJECT.match(name):
        return "plan_project"
    if RE_EVAL_PROJECT.match(name):
        return "eval_project"
    return None


def find_project_root() -> pathlib.Path:
    """프로젝트 루트 자동 탐지 (harness_manifest.py find_project_root() 와 동일 로직).
    1) 배포 위치(.agent/scripts/)에서 실행되면 parents[2] 가 루트
    2) 아니면 cwd 에서 위로 올라가며 .agent 또는 .claude 디렉터리를 가진 폴더 탐색
    3) 못 찾으면 cwd"""
    here = pathlib.Path(__file__).resolve()
    if here.parent.name == "scripts" and here.parent.parent.name == ".agent":
        return here.parents[2]
    cur = pathlib.Path.cwd().resolve()
    for cand in [cur] + list(cur.parents):
        if (cand / ".agent").is_dir() or (cand / ".claude").is_dir():
            return cand
    return cur


def collect_agent_files(root: pathlib.Path):
    """root/.claude/agents/*.md 를 정렬해 반환."""
    return sorted(root.glob(".claude/agents/*.md"))


def find_frontmatter_bounds(lines):
    """lines[0] 이 '---' 로 시작하지 않으면 None. 반환: (시작줄idx, 닫는줄idx)."""
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return (0, i)
    return None


def find_model_line(lines, start: int, end: int):
    """frontmatter 범위(start, end) 안에서 'model:' 줄을 찾는다.
    반환: (줄idx, match객체) 없으면 (None, None)."""
    for i in range(start + 1, end):
        m = MODEL_LINE_RE.match(lines[i])
        if m:
            return i, m
    return None, None


def read_lines(path: pathlib.Path):
    """줄 단위 리스트로 읽는다 (개행문자 미포함, 마지막 원소가 파일 끝 개행 여부를 대변)."""
    text = path.read_text(encoding="utf-8")
    return text.split("\n")


def write_lines(path: pathlib.Path, lines) -> None:
    """읽을 때와 동일한 방식(개행 없이 split)으로 만든 lines 를 원본 개행 스타일(LF) 그대로 씀."""
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write("\n".join(lines))


# ---------------------------------------------------------------- set

def cmd_set(args) -> int:
    tier = args.tier
    root = find_project_root()
    files = collect_agent_files(root)

    changed = []
    for path in files:
        name = path.name
        category = classify_filename(name)
        if category is None:
            print(f"[SKIP] {name} - kit-managed 명명 규칙 밖")
            continue

        lines = read_lines(path)
        bounds = find_frontmatter_bounds(lines)
        if bounds is None:
            print(f"[경고] {name} - frontmatter 없음, 건너뜀")
            continue
        start, end = bounds
        idx, m = find_model_line(lines, start, end)
        if idx is None:
            print(f"[경고] {name} - model: 줄 없음, 건너뜀")
            continue

        old_value = m.group(2)
        new_value = MODEL_POLICY[category][tier]
        lines[idx] = f"model: {new_value}{m.group(3)}"
        write_lines(path, lines)
        changed.append((name, old_value, new_value))

    print(f"변경 완료: {len(changed)}개 파일 (tier={tier})")
    for name, old_value, new_value in changed:
        print(f"  {name}: {old_value} -> {new_value}")
    print("STATE.md 의 model_policy 필드도 갱신하려면 /sync_brain 을 실행하세요 (자동 갱신 안 됨).")
    return 0


# ---------------------------------------------------------------- show

def cmd_show(_args) -> int:
    root = find_project_root()
    files = collect_agent_files(root)

    rows = []
    for path in files:
        name = path.name
        category = classify_filename(name)
        if category is None:
            continue

        lines = read_lines(path)
        bounds = find_frontmatter_bounds(lines)
        if bounds is None:
            value_disp = "(frontmatter 없음)"
        else:
            start, end = bounds
            idx, m = find_model_line(lines, start, end)
            if idx is None:
                value_disp = "(model: 줄 없음)"
            else:
                value = m.group(2)
                known_values = set(MODEL_POLICY[category].values())
                value_disp = value if value in known_values else f"{value} (사용자 지정값)"

        rows.append((CATEGORY_LABELS[category], name, value_disp))

    if not rows:
        print("표시할 kit-managed 에이전트 파일이 없습니다 (.claude/agents/*.md).")
        return 0

    w1 = max([len("분류")] + [len(r[0]) for r in rows])
    w2 = max([len("파일명")] + [len(r[1]) for r in rows])
    print(f"{'분류'.ljust(w1)}  {'파일명'.ljust(w2)}  현재 model 값")
    print(f"{'-' * w1}  {'-' * w2}  {'-' * 14}")
    for label, name, value_disp in rows:
        print(f"{label.ljust(w1)}  {name.ljust(w2)}  {value_disp}")
    return 0


# ---------------------------------------------------------------- main

def main() -> int:
    parser = argparse.ArgumentParser(
        prog="model_policy.py",
        description="서브에이전트 model 정책(tier) 일괄 적용 - .claude/agents/*.md 의 "
                     "model: 값을 확정 매핑표대로 교체 (선택 자산)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_set = sub.add_parser("set", help="지정한 tier 매핑값으로 .claude/agents/*.md 의 model: 을 일괄 교체")
    p_set.add_argument("tier", choices=list(TIERS), help="적용할 정책 tier")
    p_set.set_defaults(func=cmd_set)

    p_show = sub.add_parser("show", help="현재 .claude/agents/*.md 의 model: 값을 분류별 표로 출력")
    p_show.set_defaults(func=cmd_show)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
