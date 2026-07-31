#!/usr/bin/env python3
"""
harness_manifest.py - 하네스 킷 배포 파일 provenance 추적 (A7 후반부).
킷이 배포한 파일들의 SHA-256 을 기록해 두고, 이후 킷 업데이트 시
"킷 원본 그대로 / 사용자 수정 / 사용자 신규 / 삭제됨" 을 기계적으로 분류한다.

사용법:
  python3 .agent/scripts/harness_manifest.py generate [--kit-version 1.3.0] [--date 2026-07-04T00:00:00]
  python3 .agent/scripts/harness_manifest.py check
  python3 .agent/scripts/harness_manifest.py merge-gitignore --from <킷_gitignore_파일>

선택 자산 - 없어도 하네스는 동작한다. (Python 3.7+ 표준 라이브러리만 사용)
"""

import argparse
import datetime
import hashlib
import json
import os
import pathlib
import re
import sys

MANIFEST_REL = os.path.join(".agent", "harness_manifest.json")
GITIGNORE_HEADER = "# harness kit"

# Windows cp949 등 콘솔 인코딩에서 UnicodeEncodeError 로 죽지 않도록 (UTF-8 강제 + '?' 대체)
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# 킷 관리 대상 파일 (프로젝트 루트 기준 glob 패턴 - 존재하는 것만 기록)
TARGET_PATTERNS = [
    "CLAUDE.md",
    ".claude/settings.local.json",
    ".claude/commands/*.md",
    ".claude/agents/*.md",
    ".agent/HARNESS_GUIDE.md",
    ".agent/scripts/ci_gate_*.py",
    ".agent/scripts/harness_*.py",
    ".agent/scripts/archive_tasks.py",
    ".agent/scripts/pre_gate.py",
    ".agent/scripts/model_policy.py",
    ".agent/scripts/glm_mode.py",
    ".agent/scripts/stop_gate.py",
    ".agent/context/*_BRAIN.md",
    ".agent/context/*_STATE.md",
]

# check 시 "user_created" 로 분류할 네임스페이스 (manifest 에 없는 신규 파일 탐지 범위)
USER_CREATED_SCAN_PATTERNS = [
    ".claude/commands/*.md",
    ".claude/agents/*.md",
]

# kit-managed 표준 이름 (UPGRADE.md §3 네임스페이스 소유권 규약과 동일해야 함)
KIT_COMMAND_RE = re.compile(
    r"^\.claude/commands/(?:(?:read|plan_agent|dev|eval_agent|test)_[a-z0-9_]+"
    r"|sync_brain|commit_push)\.md$"
)
KIT_AGENT_RE = re.compile(r"^\.claude/agents/(?:plan|eval)_[a-z0-9_]+\.md$")
# 킷 구조를 따르지만 내용은 프로젝트 소유인 파일 - 킷 업데이트가 덮어쓰면 안 됨
USER_CONTENT_KEYS = ("CLAUDE.md", ".claude/settings.local.json")
USER_CONTENT_PREFIXES = (".agent/context/",)


def is_kit_managed(key: str) -> bool:
    """UPGRADE.md §3 규약 기준 - 킷 업데이트가 덮어쓰기 후보로 삼아도 되는 파일인가.
    표준 이름 밖의 커맨드/에이전트(user-owned)와 사용자 컨텐츠(CLAUDE.md/settings/context)는 False."""
    if key in USER_CONTENT_KEYS or key.startswith(USER_CONTENT_PREFIXES):
        return False
    if key.startswith(".claude/commands/"):
        return bool(KIT_COMMAND_RE.match(key))
    if key.startswith(".claude/agents/"):
        return bool(KIT_AGENT_RE.match(key))
    return True  # HARNESS_GUIDE.md / .agent/scripts/*


def find_project_root() -> pathlib.Path:
    """프로젝트 루트 자동 탐지.
    1) 배포 위치(.agent/scripts/)에서 실행되면 parents[2] 가 루트 (ci_gate.py 방식)
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


def sha256_of(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def rel_key(root: pathlib.Path, path: pathlib.Path) -> str:
    """manifest 키 - OS 무관하게 forward slash 상대 경로로 정규화."""
    return path.resolve().relative_to(root.resolve()).as_posix()


def collect_targets(root: pathlib.Path):
    """TARGET_PATTERNS 에 매칭되는 실존 파일 목록 (정렬, 중복 제거)."""
    found = {}
    for pattern in TARGET_PATTERNS:
        for p in sorted(root.glob(pattern)):
            if p.is_file():
                found[rel_key(root, p)] = p
    return found


# ---------------------------------------------------------------- generate

def cmd_generate(args) -> int:
    root = find_project_root()
    targets = collect_targets(root)
    files = {}
    for key, path in sorted(targets.items()):
        try:
            files[key] = {"deployed_hash": sha256_of(path), "kit_managed": is_kit_managed(key)}
        except OSError as e:
            print(f"[경고] 해시 실패, 건너뜀: {key} ({e})", file=sys.stderr)

    manifest = {
        "kit_version": args.kit_version,
        "generated_at": args.date or datetime.datetime.now().isoformat(timespec="seconds"),
        "files": files,
    }
    out = root / MANIFEST_REL
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"manifest 생성 완료: {out} ({len(files)}개 파일, kit_version={manifest['kit_version']})")
    return 0


# ---------------------------------------------------------------- check

def load_manifest(root: pathlib.Path):
    path = root / MANIFEST_REL
    if not path.is_file():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def classify(root: pathlib.Path, manifest: dict):
    """manifest 대비 현재 상태 분류. 반환: dict[카테고리] = [(상대경로, kit_managed), ...]
    kit_managed=False 항목은 킷 업데이트의 덮어쓰기 후보가 아니다 (UPGRADE.md §3)."""
    result = {"unchanged": [], "user_modified": [], "user_created": [], "missing": []}
    recorded = manifest.get("files", {})

    for key, meta in sorted(recorded.items()):
        km = meta.get("kit_managed", is_kit_managed(key))  # 구버전 manifest 호환
        path = root / key
        if not path.is_file():
            result["missing"].append((key, km))
            continue
        try:
            current = sha256_of(path)
        except OSError:
            result["missing"].append((key, km))
            continue
        if current == meta.get("deployed_hash"):
            result["unchanged"].append((key, km))
        else:
            result["user_modified"].append((key, km))

    # manifest 에 없는 .claude/commands|agents 파일 → 사용자 신규 자산
    for pattern in USER_CREATED_SCAN_PATTERNS:
        for p in sorted(root.glob(pattern)):
            if p.is_file():
                key = rel_key(root, p)
                if key not in recorded:
                    result["user_created"].append((key, False))

    return result


def cmd_check(_args) -> int:
    root = find_project_root()
    manifest = load_manifest(root)
    if manifest is None:
        print(f"manifest 없음: {root / MANIFEST_REL}")
        print("먼저 generate 를 실행하세요: python3 .agent/scripts/harness_manifest.py generate")
        return 1

    result = classify(root, manifest)

    print(f"== harness manifest check (kit_version={manifest.get('kit_version', 'unknown')}, "
          f"generated_at={manifest.get('generated_at', '?')}) ==")
    print(f"요약: unchanged {len(result['unchanged'])} / "
          f"user_modified {len(result['user_modified'])} / "
          f"user_created {len(result['user_created'])} / "
          f"missing {len(result['missing'])}")

    labels = [
        ("unchanged", "unchanged (해시 일치)"),
        ("user_modified", "user_modified (해시 불일치)"),
        ("user_created", "user_created (manifest 에 없음 - 킷 업데이트가 건드리지 않음)"),
        ("missing", "missing (manifest 에 있으나 파일 없음)"),
    ]
    for cat, label in labels:
        if result[cat]:
            print(f"\n[{label}]")
            for key, km in result[cat]:
                suffix = "" if km else "  [user-owned/컨텐츠 - 킷 업데이트 대상 아님]"
                print(f"  - {key}{suffix}")

    kit_modified = [key for key, km in result["user_modified"] if km]
    if kit_modified:
        print("\n주의: kit-managed 파일에 수정이 있습니다. 킷 업데이트 시 무조건 덮어쓰지 말 것 (UPGRADE.md §2 참조).")
        return 1
    return 0


# ---------------------------------------------------------------- merge-gitignore

def cmd_merge_gitignore(args) -> int:
    root = find_project_root()
    src = pathlib.Path(args.src)
    if not src.is_file():
        print(f"원본 파일 없음: {src}", file=sys.stderr)
        return 1

    with open(src, encoding="utf-8") as f:
        wanted = [line.rstrip("\n").rstrip("\r") for line in f]
    wanted = [line for line in wanted if line.strip()]  # 빈 줄 제외

    target = root / ".gitignore"
    existing_lines = []
    if target.is_file():
        with open(target, encoding="utf-8") as f:
            existing_lines = [line.rstrip("\n").rstrip("\r") for line in f]
    existing_set = {line.strip() for line in existing_lines if line.strip()}

    to_add = []
    seen = set()
    for line in wanted:
        key = line.strip()
        if key in existing_set or key in seen:
            continue
        seen.add(key)
        to_add.append(line)

    if not to_add:
        print(f".gitignore 병합: 추가할 항목 없음 (이미 {len(wanted)}개 전부 존재)")
        return 0

    with open(target, "a", encoding="utf-8", newline="\n") as f:
        if existing_lines and existing_lines[-1].strip():
            f.write("\n")
        if GITIGNORE_HEADER not in existing_set:
            f.write(f"{GITIGNORE_HEADER}\n")
        for line in to_add:
            f.write(f"{line}\n")

    print(f".gitignore 병합 완료: {len(to_add)}개 항목 추가 → {target}")
    for line in to_add:
        print(f"  + {line}")
    return 0


# ---------------------------------------------------------------- main

def main() -> int:
    parser = argparse.ArgumentParser(
        prog="harness_manifest.py",
        description="하네스 킷 배포 파일 provenance 추적 (선택 자산)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_gen = sub.add_parser("generate", help="킷 관리 대상 파일의 SHA-256 을 manifest 에 기록")
    p_gen.add_argument("--kit-version", default="unknown", help="킷 버전 (예: 1.3.0 - v 접두 없이)")
    p_gen.add_argument("--date", default=None, help="generated_at 값 (미지정 시 현재 시각 ISO)")
    p_gen.set_defaults(func=cmd_generate)

    p_chk = sub.add_parser("check", help="현재 파일 해시를 manifest 와 대조해 분류 리포트 출력")
    p_chk.set_defaults(func=cmd_check)

    p_mg = sub.add_parser("merge-gitignore", help="킷 .gitignore 항목의 누락분만 대상 프로젝트에 append")
    p_mg.add_argument("--from", dest="src", required=True, help="킷이 요구하는 .gitignore 항목 파일")
    p_mg.set_defaults(func=cmd_merge_gitignore)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
