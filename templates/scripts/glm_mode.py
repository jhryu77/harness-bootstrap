#!/usr/bin/env python3
"""
glm_mode.py - GLM(z.ai 등 Anthropic 호환 엔드포인트) 라우팅 실험 유틸리티. **실험적, opt-in.**

이것은 Claude Code 의 내장 다중 에이전트 오케스트레이션이 아니다. 이 스크립트가 하는 일은
"GLM 으로 라우팅된 별도 Claude Code 프로세스를 tmux 새 창에 띄워주는 수동 유틸리티" 뿐이다.
그 창에서 무엇을 시킬지는 자동으로 결정되지 않는다 - 사람이 직접 판단해서 프롬프트로 지시한다.
자동 위임/자동 오케스트레이션 기능은 없다.

기본 비활성. 사용하려면:
  - tmux 필요 (Windows 는 WSL 안에서 실행)
  - 별도의 유료 GLM 호환 API 계정/키 필요 (예: z.ai)
  - `glm_mode.py spawn` 자체를 tmux 세션 안에서 실행해야 함

사용법:
  python .agent/scripts/glm_mode.py setup <api-key> [--base-url URL] [--model MODEL_ID]
  python .agent/scripts/glm_mode.py status
  python .agent/scripts/glm_mode.py spawn [--name PANE_NAME]
  python .agent/scripts/glm_mode.py teardown

선택 자산 - 없어도 하네스는 동작한다. (Python 3.7+ 표준 라이브러리만 사용)

fail-open 규율 관련 주의: 이 스크립트는 hook 스크립트(ci_gate/pre_gate/stop_gate)가 아니다.
그것들은 예외 발생 시 조용히 넘어가는(fail-open) 규율을 따르지만, 이 스크립트의 4개 서브커맨드는
전부 사용자가 터미널에서 직접 호출하는 명령이므로 실패를 숨기지 않는다 - 사전 체크 실패 시
명확한 한국어 에러 메시지와 함께 exit 1 로 종료한다.
"""

import argparse
import json
import pathlib
import shlex
import shutil
import subprocess
import sys

# Windows 콘솔(cp949) 에서 한국어 출력이 깨지지 않도록 UTF-8 강제 (3.7+).
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

DEFAULT_BASE_URL = "https://api.z.ai/api/anthropic"
DEFAULT_MODEL = "glm-4.6 (사용 중인 GLM 플랜의 실제 모델 ID로 교체하세요)"


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


def config_path(root: pathlib.Path) -> pathlib.Path:
    return root / ".agent" / "config" / "glm.json"


def mask_key(key: str) -> str:
    if not key:
        return ""
    prefix = key[:4]
    return prefix + "*" * max(0, len(key) - 4)


def cmd_setup(args) -> int:
    root = find_project_root()
    path = config_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)

    config = {
        "api_key": args.api_key,
        "base_url": args.base_url or DEFAULT_BASE_URL,
        "model": args.model or DEFAULT_MODEL,
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
        f.write("\n")

    try:
        import os

        os.chmod(path, 0o600)
    except Exception:
        pass  # Windows 등 chmod 미지원 환경 - 조용히 skip

    print(f"설정 저장 완료: {path} (키는 표시하지 않음)")
    return 0


def cmd_status(args) -> int:
    root = find_project_root()
    path = config_path(root)

    if not path.is_file():
        print("GLM 설정 없음 - glm_mode.py setup <api-key> 먼저 실행")
    else:
        try:
            with open(path, encoding="utf-8") as f:
                config = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"GLM 설정 파일 파싱 실패: {path} ({e})")
            config = {}

        base_url = config.get("base_url", "(없음)")
        model = config.get("model", "(없음)")
        api_key = config.get("api_key", "")

        print(f"설정 파일: {path}")
        print(f"base_url: {base_url}")
        print(f"model: {model}")
        print(f"api_key: {mask_key(api_key)}")

    tmux_path = shutil.which("tmux")
    print(f"tmux 사용 가능: {'예 (' + tmux_path + ')' if tmux_path else '아니오'}")

    import os

    in_tmux = bool(os.environ.get("TMUX"))
    print(f"현재 tmux 세션 안에서 실행 중: {'예' if in_tmux else '아니오'}")

    return 0


def cmd_spawn(args) -> int:
    import os

    root = find_project_root()
    path = config_path(root)

    # (1) glm.json 존재 확인
    if not path.is_file():
        print("오류: GLM 설정이 없습니다 - glm_mode.py setup <api-key> 를 먼저 실행하세요.")
        return 1

    try:
        with open(path, encoding="utf-8") as f:
            config = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"오류: GLM 설정 파일 파싱 실패: {path} ({e})")
        return 1

    # (2) tmux 존재 확인
    if not shutil.which("tmux"):
        print("오류: tmux 가 필요합니다 (Windows 는 WSL 안에서 실행하세요).")
        return 1

    # (3) 현재 tmux 세션 안에서 실행 중인지 확인
    if not os.environ.get("TMUX"):
        print(
            "오류: 이 명령은 tmux 세션 안에서 실행해야 합니다. "
            "먼저 tmux 세션을 시작한 뒤(tmux new -s work) 그 안에서 이 명령을 실행하세요."
        )
        return 1

    # (4) claude CLI 존재 확인 - 없으면 경고만 하고 계속 진행
    if not shutil.which("claude"):
        print("경고: Claude Code CLI(claude)가 PATH 에서 발견되지 않았습니다. 계속 진행합니다.")

    base_url = config.get("base_url", DEFAULT_BASE_URL)
    api_key = config.get("api_key", "")
    model = config.get("model", DEFAULT_MODEL)

    shell_command = (
        f"ANTHROPIC_BASE_URL={shlex.quote(base_url)} "
        f"ANTHROPIC_AUTH_TOKEN={shlex.quote(api_key)} "
        f"ANTHROPIC_MODEL={shlex.quote(model)} "
        f"claude"
    )

    pane_name = args.name
    try:
        subprocess.run(["tmux", "new-window", "-n", pane_name, shell_command], check=True)
    except subprocess.CalledProcessError as e:
        print(f"오류: tmux new-window 실행 실패: {e}")
        return 1

    print(
        f"새 tmux 창 '{pane_name}' 에서 GLM 라우팅 Claude Code 를 시작했습니다. "
        f"Ctrl-b <번호> 또는 창 목록에서 전환해 확인하세요. "
        f"이 창에 어떤 작업을 맡길지는 직접 판단해서 프롬프트로 전달하세요 - 자동 위임 기능은 없습니다."
    )
    return 0


def cmd_teardown(args) -> int:
    root = find_project_root()
    path = config_path(root)

    if path.is_file():
        path.unlink()
        print("GLM 설정 제거 완료")
    else:
        print("GLM 설정 없음")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "GLM(z.ai 등 Anthropic 호환 엔드포인트) 라우팅 실험 유틸리티. "
            "실험적, opt-in - tmux 새 창에 별도 Claude Code 프로세스를 띄워줄 뿐, "
            "자동 위임/오케스트레이션 기능은 없다."
        )
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_setup = sub.add_parser("setup", help="GLM API 키/엔드포인트 설정 저장")
    p_setup.add_argument("api_key", help="GLM(Anthropic 호환) API 키")
    p_setup.add_argument("--base-url", dest="base_url", default=None, help=f"기본값: {DEFAULT_BASE_URL}")
    p_setup.add_argument("--model", dest="model", default=None, help="기본값: GLM 플랜의 실제 모델 ID 안내 문자열")
    p_setup.set_defaults(func=cmd_setup)

    p_status = sub.add_parser("status", help="GLM 설정 및 tmux 사용 가능 여부 확인")
    p_status.set_defaults(func=cmd_status)

    p_spawn = sub.add_parser("spawn", help="GLM 라우팅 Claude Code 를 tmux 새 창에서 시작")
    p_spawn.add_argument("--name", dest="name", default="glm", help="tmux 창 이름 (기본값: glm)")
    p_spawn.set_defaults(func=cmd_spawn)

    p_teardown = sub.add_parser("teardown", help="GLM 설정 삭제")
    p_teardown.set_defaults(func=cmd_teardown)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
