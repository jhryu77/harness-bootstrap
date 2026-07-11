#!/usr/bin/env python3
"""
harness_doctor.py - 하네스 설치 무결성 셀프 진단 (A10).
settings/hook/에이전트 frontmatter/SSOT/manifest 정합성을 항목별로 검사해
[OK]/[WARN]/[FAIL] 리포트를 출력한다. 자동 수정은 하지 않는다 (제안만).

사용법:
  python3 .agent/scripts/harness_doctor.py

선택 자산 - 없어도 하네스는 동작한다. (Python 3.7+ 표준 라이브러리만 사용)
예외 발생 시 조용히 넘어가지 않고 해당 항목을 FAIL 로 보고한다 (진단 스크립트 예외 규율).
"""

import hashlib
import json
import pathlib
import py_compile
import re
import subprocess
import sys

RESULTS = []  # (level, message, fix_suggestion|None)

# Windows cp949 등 콘솔 인코딩에서 UnicodeEncodeError 로 죽지 않도록 (UTF-8 강제 + '?' 대체)
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def find_project_root() -> pathlib.Path:
    """배포 위치(.agent/scripts/)면 parents[2], 아니면 cwd 상향 탐색."""
    here = pathlib.Path(__file__).resolve()
    if here.parent.name == "scripts" and here.parent.parent.name == ".agent":
        return here.parents[2]
    cur = pathlib.Path.cwd().resolve()
    for cand in [cur] + list(cur.parents):
        if (cand / ".agent").is_dir() or (cand / ".claude").is_dir():
            return cand
    return cur


def report(level: str, message: str, fix: str = None):
    RESULTS.append((level, message, fix))
    print(f"[{level}] {message}")


def parse_frontmatter(path: pathlib.Path):
    """마크다운 frontmatter (--- ... ---) 를 라인 리스트로 반환. 없으면 None."""
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return None
    if not lines or lines[0].strip() != "---":
        return None
    body = []
    for line in lines[1:]:
        if line.strip() == "---":
            return body
        body.append(line)
    return None  # 닫는 --- 없음


def frontmatter_keys(fm_lines):
    keys = set()
    for line in fm_lines:
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:", line)
        if m:
            keys.add(m.group(1))
    return keys


# ---------------------------------------------------------------- 검사 항목

def check_1_settings(root):
    """1. .claude/settings.local.json 존재 + JSON 파싱"""
    path = root / ".claude" / "settings.local.json"
    if not path.is_file():
        report("FAIL", f"settings 없음: {path}",
               "templates/settings.local.json.template 을 .claude/settings.local.json 으로 배치")
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        report("OK", "settings.local.json 존재 + JSON 파싱 정상")
        return data
    except (json.JSONDecodeError, OSError) as e:
        report("FAIL", f"settings.local.json 파싱 실패: {e}",
               "JSON 문법 오류 수정 (마지막 항목 뒤 콤마 / 주석 사용 여부 확인)")
        return None


def check_2_hook_scripts(root, settings):
    """2. hooks.PostToolUse 의 command 에 명시된 .py 스크립트 실존 여부"""
    if settings is None:
        report("WARN", "hook 검사 생략 - settings 로드 실패")
        return
    hooks = (settings.get("hooks") or {}).get("PostToolUse") or []
    commands = []
    for entry in hooks:
        for h in entry.get("hooks") or []:
            cmd = h.get("command")
            if cmd:
                commands.append(cmd)
    if not commands:
        report("WARN", "hooks.PostToolUse 에 command 항목 없음 (CI Gate hook 미등록)")
        return
    ok = True
    for cmd in commands:
        for py in re.findall(r"[\w./\\-]+\.py", cmd):
            script = pathlib.Path(py)
            if not script.is_absolute():
                script = root / py
            if not script.is_file():
                ok = False
                report("FAIL", f"hook 이 가리키는 스크립트 없음: {py}",
                       f"{py} 를 배치하거나 settings.local.json 의 hook command 경로 수정")
    if ok:
        report("OK", f"hook command 스크립트 실존 확인 ({len(commands)}개 command)")


def check_3_ci_gate(root):
    """3. .agent/scripts/ci_gate_*.py 존재 + py_compile 통과"""
    gates = sorted((root / ".agent" / "scripts").glob("ci_gate_*.py"))
    if not gates:
        report("FAIL", ".agent/scripts/ci_gate_*.py 없음",
               "templates/ci_gate.py.template 을 ci_gate_<project>.py 로 배치")
        return
    for g in gates:
        try:
            py_compile.compile(str(g), doraise=True)
            report("OK", f"ci_gate 컴파일 통과: {g.name}")
        except py_compile.PyCompileError as e:
            report("FAIL", f"ci_gate 컴파일 실패: {g.name} - {e.msg}",
                   f"{g.name} 의 Python 문법 오류 수정")


def check_4_agent_frontmatter(root):
    """4. .claude/agents/*.md frontmatter 필수 키 (name/description/model/tools)"""
    agents = sorted((root / ".claude" / "agents").glob("*.md"))
    if not agents:
        report("WARN", ".claude/agents/*.md 없음 (서브에이전트 미배치)")
        return
    required = {"name", "description", "model", "tools"}
    for a in agents:
        fm = parse_frontmatter(a)
        if fm is None:
            report("FAIL", f"에이전트 frontmatter 없음/미닫힘: {a.name}",
                   f"{a.name} 상단에 --- name/description/model/tools --- 블록 추가")
            continue
        missing = required - frontmatter_keys(fm)
        if missing:
            report("FAIL", f"에이전트 필수 키 누락: {a.name} - {', '.join(sorted(missing))}",
                   f"{a.name} frontmatter 에 {', '.join(sorted(missing))} 추가")
        else:
            report("OK", f"에이전트 frontmatter 정상: {a.name}")


def check_5_eval_permission_mode(root):
    """5. eval_*.md 의 permissionMode: plan (이중 봉쇄)"""
    evals = sorted((root / ".claude" / "agents").glob("eval_*.md"))
    if not evals:
        report("WARN", ".claude/agents/eval_*.md 없음 (eval 에이전트 미배치)")
        return
    for e in evals:
        fm = parse_frontmatter(e) or []
        if any(re.match(r"^permissionMode\s*:\s*plan\s*$", line) for line in fm):
            report("OK", f"eval 이중 봉쇄 확인 (permissionMode: plan): {e.name}")
        else:
            report("FAIL", f"eval 이중 봉쇄 누락: {e.name} 에 permissionMode: plan 없음",
                   f"{e.name} frontmatter 에 'permissionMode: plan' 추가 (v1.2.0 마이그레이션, UPGRADE.md 참조)")


def check_6_command_description(root):
    """6. .claude/commands/*.md frontmatter description 존재"""
    commands = sorted((root / ".claude" / "commands").glob("*.md"))
    if not commands:
        report("WARN", ".claude/commands/*.md 없음 (슬래시 커맨드 미배치)")
        return
    for c in commands:
        fm = parse_frontmatter(c)
        if fm is not None and "description" in frontmatter_keys(fm):
            report("OK", f"커맨드 description 정상: {c.name}")
        else:
            report("FAIL", f"커맨드 frontmatter description 누락: {c.name}",
                   f"{c.name} 상단에 --- description: ... --- 블록 추가")


def check_7_ssot(root):
    """7. .agent/context/*_BRAIN.md + *_STATE.md 존재"""
    ctx = root / ".agent" / "context"
    brains = sorted(ctx.glob("*_BRAIN.md"))
    states = sorted(ctx.glob("*_STATE.md"))
    if brains and states:
        report("OK", f"SSOT 존재: BRAIN {len(brains)}개 / STATE {len(states)}개")
    else:
        missing = []
        if not brains:
            missing.append("*_BRAIN.md")
        if not states:
            missing.append("*_STATE.md")
        report("FAIL", f"SSOT 누락: .agent/context/ 에 {', '.join(missing)} 없음",
               "templates/BRAIN.md.template / STATE.md.template 로 생성")
    return brains


def check_8_tasks(root):
    """8. .agent/tasks/archive/ 존재"""
    path = root / ".agent" / "tasks" / "archive"
    if path.is_dir():
        report("OK", "tasks/archive/ 디렉터리 존재")
    else:
        report("FAIL", f"디렉터리 없음: {path}",
               "mkdir -p .agent/tasks/archive (task 아카이브 대상 폴더)")


def check_9_brain_drift(root, brains):
    """9. BRAIN 의 last_synced_commit 류 필드 vs git HEAD 대조 (없으면 skip)"""
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(root), capture_output=True, text=True, timeout=10,
        ).stdout.strip()
    except Exception:
        head = ""
    if not head:
        report("WARN", "git HEAD 확인 불가 - BRAIN 드리프트 검사 생략")
        return
    checked = False
    for b in brains or []:
        try:
            text = b.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        raw = re.search(r"last_synced_commit\s*[:=]\s*[`\"']?(\S+)", text)
        m = re.search(r"last_synced_commit\s*[:=]\s*[`\"']?([0-9a-fA-F]{7,40})", text)
        if not m:
            if raw:
                checked = True
                report("WARN", f"last_synced_commit 값이 hash 형식이 아님: {b.name} ({raw.group(1)[:20]}) - /sync_brain 필요")
            continue
        checked = True
        synced = m.group(1)
        if head.startswith(synced) or synced.startswith(head):
            report("OK", f"BRAIN 동기화 시점 = HEAD: {b.name} ({synced[:8]})")
        else:
            report("WARN", f"BRAIN 드리프트: {b.name} last_synced_commit={synced[:8]} vs HEAD={head[:8]} - /sync_brain 권장")
    if not checked:
        report("OK", "BRAIN 에 last_synced_commit 필드 없음 - 드리프트 검사 skip")


def check_10_manifest(root):
    """10. harness_manifest.json 존재 시 user_modified 카운트 재검"""
    manifest_path = root / ".agent" / "harness_manifest.json"
    if not manifest_path.is_file():
        report("OK", "harness_manifest.json 없음 - provenance 검사 skip (선택 자산)")
        return
    try:
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        report("WARN", f"harness_manifest.json 파싱 실패: {e}")
        return
    modified = []
    missing = []
    for key, meta in sorted((manifest.get("files") or {}).items()):
        path = root / key
        if not path.is_file():
            missing.append(key)
            continue
        h = hashlib.sha256(path.read_bytes()).hexdigest()
        if h != meta.get("deployed_hash"):
            modified.append(key)
    if modified:
        report("WARN", f"manifest 대비 user_modified {len(modified)}개: {', '.join(modified)} - 킷 업데이트 시 수동 병합 필요")
    else:
        report("OK", f"manifest 대비 변경 없음 (missing {len(missing)}개)")


# ---------------------------------------------------------------- main

CHECKS_DOC = "설치 무결성 진단 - settings/hook/ci_gate/에이전트/커맨드/SSOT/tasks/드리프트/manifest"


def main() -> int:
    root = find_project_root()
    print(f"== harness doctor: {root} ==")
    print(f"   ({CHECKS_DOC})\n")

    # 순차 실행 - settings(검사1 결과) / brains(검사7 결과) 는 후속 검사가 참조
    brains = []
    settings = None
    checks = [
        lambda: check_1_settings(root),
        lambda: check_2_hook_scripts(root, settings),
        lambda: check_3_ci_gate(root),
        lambda: check_4_agent_frontmatter(root),
        lambda: check_5_eval_permission_mode(root),
        lambda: check_6_command_description(root),
        lambda: check_7_ssot(root),
        lambda: check_8_tasks(root),
        lambda: check_9_brain_drift(root, brains),
        lambda: check_10_manifest(root),
    ]
    for i, fn in enumerate(checks):
        try:
            result = fn()
            if i == 0:
                settings = result
            if i == 6:
                brains = result or []
        except Exception as e:  # 진단 스크립트 - 예외를 오류 항목으로 보고
            report("FAIL", f"검사 {i + 1} 실행 중 예외: {type(e).__name__}: {e}",
                   "harness_doctor.py 자체 또는 대상 파일 인코딩/권한 확인")

    ok = sum(1 for lv, _, _ in RESULTS if lv == "OK")
    warn = sum(1 for lv, _, _ in RESULTS if lv == "WARN")
    fail = sum(1 for lv, _, _ in RESULTS if lv == "FAIL")
    print(f"\n== 요약: OK {ok} / WARN {warn} / FAIL {fail} ==")

    fails = [(msg, fix) for lv, msg, fix in RESULTS if lv == "FAIL"]
    if fails:
        print("\n-- FAIL 항목별 --fix 제안 (자동 수정하지 않음) --")
        for msg, fix in fails:
            print(f"  * {msg}")
            if fix:
                print(f"    --fix 제안: {fix}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
