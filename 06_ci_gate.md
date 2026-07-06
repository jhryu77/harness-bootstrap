# 06. CI Gate - PostToolUse Hook

> 매 Edit/Write 시 자동 실행되는 정적 검증. 위반 시 stderr → Claude 컨텍스트 자동 주입.

---

## 메커니즘

Claude Code 의 `.claude/settings.local.json` 의 `hooks.PostToolUse` 에 명시한 명령이 **매 Edit/Write 후 즉시** 실행된다:

```json
"hooks": {
  "PostToolUse": [{
    "matcher": "Edit|Write",
    "hooks": [{
      "type": "command",
      "command": "python .agent/scripts/ci_gate_<project>.py"
    }]
  }]
}
```

훅 동작:
1. Claude 가 Edit 또는 Write 도구 호출 완료
2. Claude Code 가 stdin 에 JSON (`{"file_path": "<path>", ...}`) 을 담아 command 실행
3. Python 스크립트가 file_path 읽고 검사
4. **stderr 출력이 있으면** Claude 다음 턴 context 에 자동 주입
5. **stdout 은 무시** (정상 시 무출력)

따라서 위반 발견 시 print 를 **반드시 stderr 로** 한다.

---

## 표준 검사 3종 (공통)

### 검사 1 - 임시 파일 위치

루트에 `tmp_*` `verify_*` `diag_*` `check_*` 직접 생성 금지. `tmp/` 폴더로 유도.

```python
TMP_PATTERNS = ("tmp_", "verify_", "diag_", "check_")

def check_tmp_location(path: str):
    base = os.path.basename(path)
    rel = _rel_to_root(path)
    is_root_level = ("\\" not in rel) and ("/" not in rel)
    if any(base.startswith(p) for p in TMP_PATTERNS) and is_root_level:
        return f"임시 파일 prefix({base.split('_', 1)[0]}_*)는 tmp/ 폴더에 생성하세요. 루트 직접 배치 금지."
    return None
```

이유: 정리되지 않은 검증 파일이 git 에 무심코 들어가는 것을 차단. 사용자가 명시적으로 `tmp/` 를 만들고 그 안에 둬야 의도가 분명.

### 검사 2 - 시크릿 패턴

```python
DEFAULT_SECRET_PATTERNS = [
    (re.compile(r"eyJ[A-Za-z0-9._-]{40,}"),         "JWT"),
    (re.compile(r"AKIA[0-9A-Z]{16}"),               "AWS Access Key"),
    (re.compile(r"AIza[0-9A-Za-z_-]{35}"),          "Google API Key"),
    (re.compile(r"ghp_[A-Za-z0-9]{36}"),            "GitHub PAT"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{82}"),    "GitHub fine-grained PAT"),
    (re.compile(r"gho_[A-Za-z0-9]{36}"),            "GitHub OAuth Token"),
    (re.compile(r"glpat-[A-Za-z0-9_-]{20}"),        "GitLab PAT"),
    (re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),   "Slack Token"),
    (re.compile(r"ya29\.[A-Za-z0-9_-]{20,}"),       "Google OAuth Access Token"),
    (re.compile(r"sk-[A-Za-z0-9_-]{20,}"),          "OpenAI/Anthropic 류 API Key (sk-)"),
    (re.compile(r"-----BEGIN (RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY-----"), "PEM Private Key"),
    (re.compile(r"-----BEGIN CERTIFICATE-----"),    "인증서 블록"),
]
```

위반 시 환경변수 / `secrets.properties` / `.env.local` 사용 안내. WARN 레벨 (FAIL 까지 안 가더라도 Claude 가 인지 후 정리).

false positive 주의: `sk-` 는 prefix 가 짧아 오탐 여지 - 오탐 발생 파일은 tmp/ 외부로 옮기지 말고 패턴 문맥을 좁혀 조정.

#### 확장 가이드 - 프로젝트별 추가 패턴

`.agent/config/security_patterns.json` 에 추가 패턴을 두면 `_load_extra_patterns()` 가 병합한다:

```json
[{"pattern": "MYCO_KEY_[A-Z0-9]{32}", "label": "사내 API Key"}]
```

**기본 패턴 제거는 불가 - 추가만 허용.** 이유: 배포 킷의 안전 기본값을 프로젝트 설정으로 약화시킬 수 없어야 시크릿 검사 우회가 원천 차단된다.

### 검사 3 - 언어별 구문 sanity

**Kotlin** (sampleapp 예시):

```python
def check_kotlin_braces(path, content):
    if not path.endswith((".kt", ".kts")):
        return None
    opens = content.count("{")
    closes = content.count("}")
    if opens != closes:
        return f"Kotlin 괄호 불일치: '{{' {opens} 개 / '}}' {closes} 개"
    return None
```

문자열/주석 정밀 파싱은 하지 않는다 (false positive 있음). **경량 카운트** 만으로 큰 누락 (편집 중 잘림 / 닫는 괄호 빼먹음) 을 잡는다.

**Python**:

```python
import ast
def check_python_syntax(path, content):
    if not path.endswith(".py"): return None
    try:
        ast.parse(content)
    except SyntaxError as e:
        return f"Python SyntaxError: {e.lineno}:{e.offset} {e.msg}"
    return None
```

**TypeScript/JavaScript**: ast 직접 파싱은 어렵다. 다음 중 선택:
- 외부 도구 (`npx tsc --noEmit <file>`) - 느림. CI Gate hook 에선 부담
- 간이 검사 - `function/const/import` 등 키워드와 `;` / 괄호 매칭
- skip - 매 Edit 마다 `npm run typecheck` 는 너무 비싸므로 별도 `/check_<project>` 슬래시로 분리

**Swift / Go / Rust**: 각 언어의 `swift build --type-check-only` / `go vet -e <file>` / `cargo check` 등으로. 빠른 검증 명령이 있는 언어만.

---

## 추가 검사 (프로젝트별)

### 매직 넘버 / 비타협 상수 변경 감지

예: sampleapp 의 `MIN_PERCENT 0.20 / MAX_PERCENT 0.80 / DEFAULT_PERCENT 0.70` 가 변경되면 경고:

```python
def check_split_ratio_consts(path, content):
    if "MainActivity.kt" not in path: return None
    expected = ["MIN_PERCENT = 0.20", "MAX_PERCENT = 0.80", "DEFAULT_PERCENT = 0.70"]
    for e in expected:
        if e not in content:
            return f"분할 비율 상수 변경 감지: '{e}' 없음. plan.md 영향 평가 필요."
    return None
```

### 인텐트 필터 / 라우트 누락 감지

```python
def check_launcher_intent_filter(path, content):
    if "AndroidManifest.xml" not in path: return None
    required = ["MAIN", "HOME", "DEFAULT", "LAUNCHER"]
    missing = [c for c in required if f"android.intent.category.{c}" not in content
               and f'action.{c}' not in content]
    if missing:
        return f"런처 인텐트 필터 누락: {missing}"
    return None
```

### 시크릿이 .env.example 에만 - .env 본체엔 placeholder

```python
def check_env_no_secret(path, content):
    if not path.endswith(".env.example"): return None
    suspicious = re.findall(r"(SECRET|TOKEN|KEY|PASS)=([A-Za-z0-9]{20,})", content)
    if suspicious:
        return f".env.example 에 실제 시크릿 의심 값: {[s[0] for s in suspicious]}"
    return None
```

---

## 훅 이벤트별 출력 채널과 확장 (opt-in)

CI Gate 는 PostToolUse 가 기본이지만, Claude Code 훅은 이벤트마다 유효한 출력 채널이 다르다:

| 이벤트 | 유효 출력 채널 | 용도 |
|---|---|---|
| PostToolUse | stderr → Claude 컨텍스트 주입 | ci_gate (기본) - 경고/FAIL 안내 |
| PreToolUse | stdout JSON `permissionDecision` (allow/ask/deny) | pre_gate (opt-in) - 커밋 게이트 + 위험 명령 차단 |
| Stop | systemMessage (advisory - 차단 없음) | stop_gate (opt-in) - 턴 종료 시 변경 파일 광역 검사 |

### pre_gate.py - PreToolUse 확장 (opt-in)

- `git commit` 감지 시 staged 파일 전체에 CI Gate 검사를 실행 → 실패 시 **deny** 로 커밋 자체를 차단한다. hook 이 도구 호출 전에 개입하므로 `--no-verify` 로도 우회 불가.
- 위험 Bash 명령 목록 내장: 파괴적 명령(예: 루트 재귀 삭제 / 보호 브랜치 force push / DROP DDL)은 deny, 작업 소실 경계 명령(`git reset --hard` / `git clean -f` / `git checkout -- .` / `truncate`)은 ask.
- 프로젝트별 패턴은 `.agent/config/bash_guard.json` 으로 **"추가만" 병합** (기본 목록 약화 불가 - security_patterns.json 과 동일 원칙).
- fail-open + 예산 규율: 스크립트 예외 시 조용히 allow, 전체 검사 예산 5초 - 초과 위험 검사는 넣지 않는다.
- 등록법: `templates/settings.pretooluse.json.example` 참조. **기본 미등록 (opt-in)**.

### stop_gate.py - Stop 확장 (opt-in, advisory 전용)

- 턴 종료(Stop) 시 `git status --porcelain` 의 변경 파일 전체를 ci_gate 로 일괄 검사해 systemMessage 로 **경고만** 낸다 - per-file PostToolUse 가 못 잡는 광역 회귀(예: 공유 모듈 수정이 다른 파일에 미치는 영향)를 커버한다.
- `stop_hook_active` 가 truthy 면 즉시 무출력 종료 - Stop 훅 재진입 루프 가드 (최우선).
- `.agent/tasks/.stop_gate_head` 에 HEAD SHA 를 기록해 **커밋당 1회**만 발동. 변경 파일 30개 초과 시 앞 30개만 검사하고 "외 N개 미검사" 표기 (5초 예산).
- **advisory 전용 - 어떤 경우에도 차단(block)하지 않는다.** fail-open (git 부재/예외 시 무출력 exit 0).
- 등록법: `templates/settings.pretooluse.json.example` 참조 (Stop 은 matcher 불필요). **기본 미등록 (opt-in)**.

### FROZEN 존 경고 (A13)

ci_gate 는 하네스 경로(`.claude/`, `.agent/context/` 등) 에 대한 Write/Edit 를 감지하면 stderr 경고를 낸다. `dev_harness` 승인 플로우 안에서는 무시해도 되는 신호이고, 그 밖의 일반 작업 중이라면 중단 신호다. deny 승격은 서브에이전트 컨텍스트 식별이 가능해지는 시점의 확장 옵션으로 남긴다.

---

## GLM 병행 (실험적, opt-in) - glm_mode.py

일부 개발 도구는 GLM(z.ai)을 Claude 와 자동으로 협업시키는 다중 에이전트 오케스트레이션을 제공하지만, harness_bootstrap 은 그 정도 런타임을 갖추고 있지 않다. `glm_mode.py` 는 "GLM 로 라우팅된 별도 Claude Code 프로세스를 tmux 새 창에 띄워주는 수동 유틸리티"일 뿐이다 - 두 창을 오가며 사람이 직접 작업을 나눈다. 자동 위임이 아니라는 점을 분명히 해둔다.

요구사항:
- tmux 필수 (Windows 는 WSL 경유)
- GLM 호환 API 계정 및 키 필요 (z.ai 등, 유료)
- Claude Code CLI(`claude`)가 PATH 에 있어야 함

명령 3개:
- `setup <key>` - 최초 1회, 키 저장
- `spawn` - 새 tmux 창에 GLM 라우팅 Claude Code 실행
- `status`, `teardown` - 상태 확인 / 종료

**기본 비활성.** 하네스의 어떤 hook 도 이 스크립트를 자동 호출하지 않는다 - 완전히 수동이다.

---

## 스크립트 표준 골격

`.agent/scripts/ci_gate_<project>.py`:

```python
#!/usr/bin/env python3
"""
ci_gate_<project>.py
Claude Code PostToolUse(Edit|Write) hook.
정상 시 무출력. 위반 시 stderr.
"""

import sys, os, re, json, pathlib

PROJECT_ROOT = str(pathlib.Path(__file__).resolve().parents[2])

# === 검사 패턴 정의 ===
TMP_PATTERNS = ("tmp_", "verify_", "diag_", "check_")
DEFAULT_SECRET_PATTERNS = [
    (re.compile(r"eyJ[A-Za-z0-9._-]{40,}"), "JWT"),
    # ... 위 표 참조
]

def _load_extra_patterns():
    """프로젝트별 추가 패턴 (.agent/config/security_patterns.json) - 확장 가이드 참조."""
    ...

SECRET_PATTERNS = DEFAULT_SECRET_PATTERNS + _load_extra_patterns()

def _rel_to_root(path: str) -> str:
    try:
        return os.path.relpath(os.path.abspath(path), os.path.abspath(PROJECT_ROOT))
    except ValueError:
        return path

# === 검사 함수들 ===
def check_tmp_location(path: str): ...
def check_secrets(path: str, content: str): ...
def check_<lang>_syntax(path: str, content: str): ...

# === 진입점 ===
def gate(path: str) -> None:
    if not path or not os.path.isfile(path):
        return
    rel = _rel_to_root(path)

    loc_msg = check_tmp_location(path)
    if loc_msg:
        print(f"\n[CI Gate FAIL] 파일 위치: {rel}\n  {loc_msg}\n", file=sys.stderr)
        return

    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception:
        return

    hits = []
    for name, fn in (("secrets", check_secrets), ("syntax", check_<lang>_syntax)):
        msg = fn(path, content)
        if msg:
            hits.append((name, msg))

    if hits:
        print(f"\n[CI Gate WARN] {rel}", file=sys.stderr)
        for name, msg in hits:
            print(f"  - {name}: {msg}", file=sys.stderr)
        print("", file=sys.stderr)

def _resolve_path_from_stdin() -> str:
    """hook 진입 시 stdin JSON 에서 file_path 추출."""
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
    if len(sys.argv) > 1:
        gate(sys.argv[1])
        return
    if not sys.stdin.isatty():
        fp = _resolve_path_from_stdin()
        if fp:
            gate(fp)

if __name__ == "__main__":
    main()
```

stdin JSON 의 file_path 추출 시 **여러 키를 모두 시도** (Claude Code 버전에 따라 키 이름 다를 수 있음).

---

## 직접 호출 (개발 시 디버깅)

```bash
python .agent/scripts/ci_gate_<project>.py <path/to/file>
```

가짜 임시 파일로 검사 시뮬:

```bash
echo "test" > tmp_test.txt
python .agent/scripts/ci_gate_<project>.py tmp_test.txt
# → stderr: "임시 파일 prefix(tmp_*) ..."
rm tmp_test.txt
```

---

## 검증 - eval_harness 단계에서

`eval_agent_harness` 가 CI Gate 무결성을 점검할 때:

```bash
python -m py_compile .agent/scripts/ci_gate_<project>.py && echo "py_compile OK"
python -c "import json; json.load(open('.claude/settings.local.json', encoding='utf-8')); print('JSON OK')"

# hook 일치성: settings 의 command 와 실제 스크립트 경로 일치 확인
grep -q "ci_gate_<project>.py" .claude/settings.local.json && \
  [ -f .agent/scripts/ci_gate_<project>.py ] && echo "hook OK"
```

이 셋이 모두 OK 여야 CI Gate 작동.

---

## 안티패턴

| 안티패턴 | 왜 나쁜가 |
|---|---|
| stdout 으로 위반 출력 | hook 은 stderr 만 Claude 컨텍스트에 주입. stdout 은 무시됨 |
| 정상 시 stdout 출력 | 매 Edit 마다 노이즈. Claude 가 무의미 메시지 처리하느라 컨텍스트 낭비 |
| 검사가 너무 무거움 (예: 매 Edit 마다 `tsc --noEmit`) | 응답 지연 폭발. CI Gate 는 **밀리초 단위 경량** |
| false positive 많은 검사 (정밀 파싱 시도) | Claude 가 무시하게 됨. 진짜 위반 감지 빈도 낮아짐 |
| 시크릿 검사 빠뜨림 | 가장 비싼 사고. 절대 빠지면 안 됨 |
| hook command 가 절대 경로 | OS/사용자 의존. 상대 경로 사용 |

---

## 다음 단계

- `07_task_lifecycle.md` - task 폴더 라이프사이클 + archive 자동화
- `08_immutables.md` - 비타협 항목 정의 가이드
