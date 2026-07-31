#!/usr/bin/env python3
"""
레퍼런스 프로젝트 도메인 용어 유출 검사.

이 킷은 실제 프로젝트의 하네스를 중립화해서 배포하는 물건이다. 파일명이나
슬래시 커맨드명은 find-replace 로 잡히지만, **산문 서술**(진화 곡선 내러티브,
case study 컨텍스트 등)에 남은 원본 제품 용어는 그물을 빠져나간다.
실제로 두 번 놓쳤다 - ccb5a7c 에서 한 번, 5f0efe6 에서 또 한 번.

이 스크립트가 세 번째를 막는다.

사용법:
    python scripts/check_domain_terms.py            # 저장소 전체 검사
    python scripts/check_domain_terms.py <경로> ... # 특정 파일만

종료 코드: 0 = 깨끗, 1 = 유출 발견

새 용어 추가는 FORBIDDEN 에 한 줄 넣으면 된다.
정당한 사용이라 통과시켜야 하면 그 줄 끝에 `domain-terms:allow` 주석을 단다.
"""

import os
import subprocess
import sys
from pathlib import Path

# 원본 프로젝트를 역추적 가능하게 만드는 용어.
# 일반 단어(분할 / Picker / 런처 단독 등)는 넣지 않는다 - 오탐이 나면
# 검사 자체가 무시당하고, 그게 검사가 없는 것보다 나쁘다.
FORBIDDEN = [
    # 조직 / 프로젝트 식별자
    "aibox",
    "lecostyle",
    # 제품 도메인
    "차량",
    "카런처",
    "Car런처",
    "헤드유닛",
    "인포테인먼트",
    # 제품 기능 (원본 고유)
    "좌우분할",
    "임베드",
    "분할 비율",
    "자기 자신 필터",
    "보드 환경",
    # 사업 정보
    "카컴페터",
    "컴페터",
    "경쟁사 분석",
    "실 서비스",
    # 원본 고유 기술 용어
    "VirtualDisplay",
    "tapExclude",
]

ALLOW_MARKER = "domain-terms:allow"

SCAN_SUFFIXES = {".md", ".py", ".json", ".yml", ".yaml", ".template", ".txt", ".sh"}

# 검사에서 제외할 경로 (repo 루트 기준 prefix)
SKIP_PREFIXES = (".git/", "plans/")

SELF = Path(__file__).resolve()


def repo_root() -> Path:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
            cwd=Path(__file__).resolve().parent,
        )
        return Path(out.stdout.strip())
    except Exception:
        return SELF.parent.parent


def tracked_files(root: Path):
    """git 추적 파일만 검사한다. git 이 없으면 디렉터리 순회로 폴백."""
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z"],
            capture_output=True, text=True, check=True, cwd=root,
        )
        rels = [p for p in out.stdout.split("\0") if p]
    except Exception:
        rels = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d != ".git"]
            for fn in filenames:
                rels.append(str(Path(dirpath, fn).relative_to(root)).replace(os.sep, "/"))

    for rel in rels:
        if rel.startswith(SKIP_PREFIXES):
            continue
        p = root / rel
        if p.suffix not in SCAN_SUFFIXES:
            continue
        if p.resolve() == SELF:
            continue
        yield rel, p


def scan(rel: str, path: Path):
    hits = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return hits

    for lineno, line in enumerate(text.splitlines(), 1):
        if ALLOW_MARKER in line:
            continue
        low = line.lower()
        for term in FORBIDDEN:
            if term.lower() in low:
                hits.append((rel, lineno, term, line.strip()))
    return hits


def main() -> int:
    root = repo_root()

    if len(sys.argv) > 1:
        targets = []
        for arg in sys.argv[1:]:
            p = Path(arg).resolve()
            if p.resolve() == SELF:
                continue
            try:
                rel = str(p.relative_to(root)).replace(os.sep, "/")
            except ValueError:
                rel = str(p)
            targets.append((rel, p))
    else:
        targets = list(tracked_files(root))

    all_hits = []
    for rel, path in targets:
        all_hits.extend(scan(rel, path))

    if not all_hits:
        print(f"도메인 용어 검사 통과 - {len(targets)}개 파일")
        return 0

    print("레퍼런스 프로젝트 도메인 용어가 발견됐다:\n", file=sys.stderr)
    for rel, lineno, term, line in all_hits:
        shown = line if len(line) <= 120 else line[:117] + "..."
        print(f"  {rel}:{lineno}  [{term}]", file=sys.stderr)
        print(f"      {shown}", file=sys.stderr)
    print(
        f"\n총 {len(all_hits)}건. 중립 용어로 바꾸거나, 정당한 사용이면 "
        f"그 줄에 `{ALLOW_MARKER}` 주석을 단다.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
