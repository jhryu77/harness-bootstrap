# BOOTSTRAP_PROMPT - Claude 자동 부트스트랩

> 이 파일은 **Claude 에게 그대로 던지는 프롬프트**다. 사람용 설명이 아니다.
> 사용자는 자기 프로젝트 디렉토리에서 Claude Code 를 띄우고 이 파일 내용을 그대로 복사해서 전달하면 된다.

---

## ⚠️ Claude 에게 - 시작 전 읽어줘

당신은 지금 **어떤 프로젝트의 루트 디렉토리** 에 있다. 사용자는 이 프로젝트에 `harness_bootstrap/` 가이드에 따른 **하네스 엔지니어링 시스템** 을 구축해 달라고 했다.

당신은 다음을 한다:

1. **분석** - 이 프로젝트 스택/모듈/언어 파악
2. **추출** - 사용자에게 비타협 항목 / 정책 질문
3. **초안** - BRAIN/STATE/CLAUDE.md 초안
4. **생성** - 슬래시 커맨드 + 서브에이전트 + CI Gate
5. **검증** - 첫 task 로 무결성 확인

**핵심 원칙** (자세한 건 `harness_bootstrap/01_philosophy.md` 참조):

| # | 원칙 | 요약 |
|---|---|---|
| 1 | SSOT 분리 | BRAIN (저빈도/불변) vs STATE (고빈도/시점) |
| 2 | 3단계 워크플로 | plan → dev → eval (서브에이전트로 격리) |
| 3 | task 격리 | `.agent/tasks/task_<TS>_<slug>/` 폴더에 영구 기록 |
| 4 | 서브에이전트 최소 권한 | plan 은 tasks/ 만 Write / eval 은 Write 없음 |
| 5 | CI Gate hook | 매 Edit/Write 시 Python 스크립트 자동 실행 |
| 6 | CLAUDE.md 자동 로드 압축본 | 200줄 이하 표 위주 |
| 7 | 3종 워크플로 분리 | 코드 / 하네스 / 배포 |
| 8 | 언어/커밋 정책 명시 | 응답 언어 / Co-Authored-By / 커밋 type |
| 9 | 살아있는 하네스 | 반복 실수/작업이 트리거 - 하네스는 코드와 공동 진화 |

**참조 자산** (이 폴더 안에 있다):
- `01_philosophy.md` ~ `09_adapt_checklist.md` - 원칙 + 절차
- `templates/` - 28개 템플릿 (플레이스홀더 포함, `statusline.py` 는 치환 불필요 전역 자산·부트스트랩 필수)
- `templates/scripts/` - 선택 스크립트 7종 (archive/doctor/manifest/pre_gate/stop_gate/model_policy/glm_mode) - 플레이스홀더 없이 동작
- `templates/scripts/model_policy.py` - 이후 model 정책을 바꿀 때 사용
- `templates/scripts/glm_mode.py` - GLM 병행 (실험적, opt-in, 부트스트랩 절차에는 포함 안 함)
- `UPGRADE.md` - 킷 업데이트 절차
- `examples/sampleapp_snapshot/` - Android 프로젝트 적용 예시
- `examples/sampleapp_server_inventory/` - Next.js raw 프로젝트의 적용 전 인벤토리 실례
- `examples/case_study.md` - 종단 시나리오

각 단계마다 **사용자 컨펌 게이트** 가 있다. 사용자가 답하지 않거나 "stop=no clarifying" 모드라면 합리적 default 결정 + 결정 사항을 plan.md 에 명시 후 진행.

---

## 단계 1 - 프로젝트 분석 (Project Analysis)

이 프로젝트가 무엇인지 파악한다.

### 1.1 분석 명령 (Bash 한 번에 실행)

```bash
echo "=== git ==="
git log --oneline -10 2>/dev/null || echo "(no git repo - git init 추천)"
git remote -v 2>/dev/null
echo
echo "=== 매니페스트 파일 ==="
find . -maxdepth 3 \
  -name "package.json" -o \
  -name "build.gradle.kts" -o \
  -name "build.gradle" -o \
  -name "pyproject.toml" -o \
  -name "setup.py" -o \
  -name "Cargo.toml" -o \
  -name "go.mod" -o \
  -name "pom.xml" -o \
  -name "Gemfile" -o \
  -name "next.config.mjs" -o \
  -name "tsconfig.json" -o \
  -name "Podfile" -o \
  -name "AndroidManifest.xml" 2>/dev/null \
  | grep -v node_modules | grep -v build | sort
echo
echo "=== 디렉토리 트리 (depth 3) ==="
find . -maxdepth 3 -type d \
  -not -path "./node_modules*" \
  -not -path "./build*" \
  -not -path "./.git*" \
  -not -path "./.next*" \
  -not -path "./target*" \
  -not -path "./dist*" \
  | sort
echo
echo "=== 기존 하네스 자산 (있나?) ==="
ls -d .claude .agent CLAUDE.md 2>/dev/null
echo
echo "=== 시블링 repo (한 디렉토리 상위) ==="
ls -d ../*/ 2>/dev/null | head -10
```

### 1.2 분석 후 사용자에게 보고

다음 형식으로 출력:

```
## 분석 결과

### 스택 추정
- 언어: ...
- 프레임워크: ...
- 빌드 도구: ...
- 주요 의존성: ...

### 모듈 구성
- 단일 모듈 / 모노레포 / 멀티 패키지: ...
- 주요 디렉토리: app/, src/, lib/, ...

### git 상태
- 브랜치: ...
- 최근 5개 commit:
  - ...

### 기존 하네스
- CLAUDE.md: 있음 / 없음
- .claude/: 있음 / 없음 (있으면 기존 커맨드 인벤토리)
- .agent/: 있음 / 없음

### 시블링 repo (multi-repo 가능성)
- ../<sibling1>/ - 추정 용도
- ../<sibling2>/ - 추정 용도
- (또는 "없음")

### 컨펌 게이트 1
다음 정보가 맞나요?
- 프로젝트 슬러그 (슬래시 커맨드에 들어갈 짧은 이름): **<제안값>**
- 통신 언어 (응답/주석/문서): **한국어 / English**
- 배포 워크플로 필요한가? (OTA / store / package publish 등): **예 / 아니오**
- Co-Authored-By 라인 정책: **금지 / 허용**
- model 정책 (에이전트 역할별 model 차등, 기본은 inherit): **high / medium / low / inherit(기본값)**

사용자가 답하지 않거나 "그대로" 라고만 하면 model 정책은 inherit 로 처리합니다.

수정할 항목이 있으면 알려주세요. 아니면 "그대로 진행" 이라고 답하면 단계 2 로 넘어갑니다.
```

사용자 응답 대기. **stop=no clarifying** 모드라면 합리적 default + plan.md 에 명시.

---

## 단계 2 - 비타협 항목 추출 (Immutables Extraction)

사용자에게 다음 7개 질문을 한 번에 물어본다. (참조: `08_immutables.md`)

```
## 단계 2 - 비타협 항목 식별

이 프로젝트에서 "변경 시 사용자 컨펌 필수" 인 항목들을 추려야 합니다.

### Q1. 시스템 진입점
- 외부에서 호출되는 entry point (URL / API / intent-filter / 라우트 등) 중 변경 시 절대 사용자 컨펌 필수인 것?
- 예: Next.js 라우트 `/api/<id>` schema, Android intent-filter MAIN+LAUNCHER 같은 것

### Q2. 영구화 키 / DB 스키마
- 변경 시 사용자 데이터 손실 가능한 키 / 컬럼이 있는가?
- 예: SharedPreferences 키명, DB 컬럼명, 캐시 파일 포맷

### Q3. 인증 / 권한
- RBAC role / Supabase RLS / OAuth scope 같은 보안 정책 중 보존 필수 항목?

### Q4. 매직 넘버 / 비타협 상수
- 코드 안에 변경 시 화면 깨지는 매직 넘버 / 클램프 범위가 있는가?

### Q5. 시그너처 / 빌드 / packageName
- packageName / applicationId / namespace / signing config 변경은 사용자 컨펌 필요?

### Q6. 자동 스테이징 금지 파일 패턴
- git add 시 절대 자동 포함하면 안 되는 파일 패턴은? (예: `.env`, `*.keystore`, `*.tsbuildinfo`, `secrets.json`)

### Q7. 커밋 메시지 type 어휘
- 커밋 메시지의 type 부분은 어떤 단어 집합? (예: 추가|갱신|수정|리팩터|테스트|문서 또는 feat|fix|...)

답변을 한 번에 받거나, 모르는 항목은 "기본값" 이라고 답하면 합리적 default 적용합니다.
```

응답 정리 후:

```
## 추출된 비타협 항목 (CLAUDE.md §비타협 항목 표 후보)

| # | 항목 | 카테고리 |
|---|---|---|
| 1 | <Q1 답변> | 진입점 |
| 2 | <Q2 답변> | 영구화 |
| ... | ... | ... |

## 추출된 정책

- 자동 스테이징 금지: <Q6>
- 커밋 type: <Q7>

### 컨펌 게이트 2
위 표가 정확합니까? 빠진 항목 있으면 추가, 잘못된 항목은 수정 요청해주세요.
```

---

## 단계 3 - SSOT 초안 작성 (BRAIN / STATE)

`templates/BRAIN.md.template` + `templates/STATE.md.template` 의 플레이스홀더를 채워서 초안 작성.

### 3.1 산출 경로

- `.agent/context/<PROJECT_UPPER>_BRAIN.md` (대문자 슬러그)
- `.agent/context/<PROJECT_UPPER>_STATE.md`

### 3.2 BRAIN 초안

단계 1 분석 결과 + 단계 2 비타협 항목을 합쳐 채운다:

- §1 제품 요약: 분석에서 추출한 분류 / 패키지 / 모듈
- §2 디렉토리 트리: `find` 결과 정리
- §3 핵심 클래스/엔드포인트: 사용자 도움 없으면 비워두고 향후 점진 채움
- §4 영구화 키 인벤토리: 단계 2 Q2 답변 + 빈 행
- §5 빌드 / 의존성: 매니페스트 파일 추출
- §6 시스템 권한: (해당 있으면) 단계 2 Q5 답변
- §7 시스템 진입점: 단계 2 Q1 답변 + 라우트 검색 결과
- §8 빌드 커맨드: package.json scripts / Gradle tasks 등
- §9 영역별 비타협 (상세): 단계 2 답변
- §10 참조 / 외부 의존: 분석 결과 + 시블링 repo

### 3.3 STATE 초안

기본 골격:
- §1 Phase 표 1행 (Phase 0 = "하네스 부트스트랩 ⬜ 진행 중")
- §2 git 시점값
- §3 빌드 구성 시점값
- §4 구현 화면 (기존 코드 있으면 자동 추출)
- §6 최근 task (비어있음)
- §7 메타

STATE.md frontmatter 에 `harness_kit_version`(이 킷의 CHANGELOG 최신 버전, 현재 1.5.0) 과 `bootstrapped_at`(오늘 날짜) 을 기록한다. `model_policy` 필드도 단계 1 에서 받은 답변 값(high/medium/low/inherit)으로 함께 기록한다.

### 3.4 사용자 컨펌

```
## 단계 3 - SSOT 초안

생성된 파일:
- .agent/context/<PROJECT_UPPER>_BRAIN.md (<N>줄)
- .agent/context/<PROJECT_UPPER>_STATE.md (<M>줄)

핵심 내용:
- BRAIN §1: ...
- BRAIN §3 핵심 클래스: <K>개 자동 추출
- BRAIN §4 영구화 키: <P>개 항목
- BRAIN §7 진입점: ...
- BRAIN §9 비타협: <I>개 항목

### 컨펌 게이트 3
파일들을 직접 열어서 확인해주세요. 빠진 정보 / 잘못된 내용이 있으면 수정 요청.
```

---

## 단계 4 - 슬래시 커맨드 + 서브에이전트 생성

`templates/commands/*.md.template` + `templates/agents/*.md.template` 의 플레이스홀더를 치환해서 실제 파일 생성.

### 4.1 플레이스홀더 치환표

```
{{PROJECT}}         → 단계 1 의 슬러그 (예: webapp / sampleapp / cliapp)
{{PROJECT_UPPER}}   → 대문자 슬러그 (예: WEBAPP)
{{PROJECT_TITLE}}   → 표시 이름 (예: "SampleApp")
{{LANGUAGE}}        → 단계 1 의 통신 언어
{{STACK}}           → 분석된 스택 한 줄
{{COAUTHORED_BY}}   → 단계 1 의 Co-Authored-By 정책
{{COMMIT_TYPE_LIST}}→ 단계 2 Q7
{{IMMUTABLES_SECTION}} → 단계 2 비타협 표 (CLAUDE.md 형식)
```

### 4.2 생성 대상

표준 7종 (코드 워크플로):
- `.claude/commands/read_<project>.md`
- `.claude/commands/plan_agent_<project>.md`
- `.claude/commands/dev_<project>.md`
- `.claude/commands/eval_agent_<project>.md`
- `.claude/commands/sync_brain.md`
- `.claude/commands/commit_push.md`
- `.claude/commands/test_<project>.md` (선택)

하네스 자체 3종:
- `.claude/commands/plan_agent_harness.md`
- `.claude/commands/dev_harness.md`
- `.claude/commands/eval_agent_harness.md`

서브에이전트 4종:
- `.claude/agents/plan_<project>.md`
- `.claude/agents/eval_<project>.md`
- `.claude/agents/plan_harness.md`
- `.claude/agents/eval_harness.md`

배포 워크플로 (단계 1 에서 "예" 답한 경우) 추가 3+2:
- `.claude/commands/plan_agent_<release>.md`
- `.claude/commands/dev_<release>.md`
- `.claude/commands/eval_agent_<release>.md`
- `.claude/agents/plan_<release>.md`
- `.claude/agents/eval_<release>.md`

### 4.3 frontmatter 점검

각 생성 파일이 다음 keys 를 포함해야 함:
- commands/*: `description:`
- agents/*: `name:`, `description:`, `model:`, `tools:`

특히 `tools:` 화이트리스트는 `05_subagent_design.md` 표 따라 좁힌다.

단계 1 에서 받은 model 정책이 inherit 이 아니면, 생성하는 4개 에이전트 파일(plan_<project>/eval_<project>/plan_harness/eval_harness)의 model: 줄을 05_subagent_design.md §모델 정책의 표에 따라 즉시 그 값으로 채운다(생성 후 별도로 model_policy.py 를 실행할 필요 없음 - 처음부터 반영).

### 4.4 사용자 컨펌

```
## 단계 4 - 슬래시 + 서브에이전트 생성 완료

생성된 파일:
- .claude/commands/: 10~13개
- .claude/agents/: 4~6개

총 <N> 파일

### 컨펌 게이트 4
- `/read_<project>` `/plan_agent_<project>` `/dev_<project>` `/eval_agent_<project>` 슬래시 노출 확인됐는가?
- 서브에이전트 권한이 좁아서 작업 불편하지 않은가?

문제 있으면 수정 요청.
```

---

## 단계 5 - CI Gate 작성

`templates/ci_gate.py.template` 복사 후 언어별 검사 함수 활성화.

### 5.1 산출 경로

- `.agent/scripts/ci_gate_<project>.py`

### 5.2 언어별 검사 활성화

단계 1 의 언어에 따라:

- **Kotlin** (.kt/.kts): `check_kotlin_braces` 활성화 - 괄호 카운트
- **Python** (.py): `check_python_syntax` 활성화 - `ast.parse`
- **TypeScript/JS** (.ts/.tsx/.js/.jsx): `check_typescript_basic` 활성화 - 괄호 카운트 (`tsc --noEmit` 은 너무 무거우므로 별도 슬래시로 분리)
- **Swift**: `swift build --type-check-only` 가능하면 활성화 (느림)
- **Go**: `go vet -e <file>`
- **Rust**: 검사 생략 (cargo check 너무 무거움) - 대신 별도 슬래시

### 5.3 추가 검사 (프로젝트별)

단계 2 의 매직 넘버 / 비타협 상수에 대해 추가 검사 함수 생성:

```python
def check_<immutable_name>(path, content):
    if "<target_file_substring>" not in path: return None
    expected = ["<consts>"]
    for e in expected:
        if e not in content:
            return f"<원래 문구> 누락 - plan.md 영향 평가 필요"
    return None
```

### 5.4 검증

```bash
python3 -m py_compile .agent/scripts/ci_gate_<project>.py && echo "py_compile OK"

# 시뮬 - 임시 파일 생성하여 stderr 확인
echo "test" > tmp_test.txt
python3 .agent/scripts/ci_gate_<project>.py tmp_test.txt
rm tmp_test.txt
# → "임시 파일 prefix(tmp_*)..." stderr 출력 확인
```

---

## 단계 6 - CLAUDE.md 작성

`templates/CLAUDE.md.template` 복사 후 채움. 길이 **200줄 이하** 유지.

### 6.1 산출 경로

- `<project_root>/CLAUDE.md`

### 6.2 핵심 섹션

위 단계들의 결과를 종합:
- §1 프로젝트 개요 (단계 1)
- §2 하네스 워크플로 표
- §3 CI Gate (단계 5)
- §4 빌드 / 실행 (단계 1 빌드 명령)
- §5 아키텍처 간단 요약 (BRAIN §2~§3 1~2줄 요약 + BRAIN 포인터)
- §6 비타협 항목 표 (단계 2 결과)
- §7 디렉토리 배치 규칙
- §8 참조 문서 (BRAIN/STATE/HARNESS_GUIDE 포인터)
- §9 커밋 규칙 (단계 1 + 단계 2 Q6,Q7)

### 6.3 settings.local.json 작성

`templates/settings.local.json.template` 복사 후:
- `<YOUR_PROJECT_ROOT>` → 실제 절대 경로
- 빌드 도구 권한 추가 (예: `Bash(npm:*)`, `Bash(./gradlew:*)`)
- 단계 1 분석 결과의 외부 도구 권한 추가
- hook command 의 `<project>` 치환

### 6.4 HARNESS_GUIDE.md 작성

`templates/HARNESS_GUIDE.md.template` 복사. 길이 200~300줄.

### 6.5 디렉토리 + archive/ 생성

```bash
mkdir -p .agent/tasks/archive
mkdir -p tmp  # 임시 작업용 (CI Gate 가 권장)
```

### 6.6 상태바(statusLine) 설치 [필수]

Claude Code 전역 상태바(모델/폴더/git 브랜치 + 컨텍스트·5H·7D 사용률 + reset 카운트다운)는 하네스 적용 시 **필수로 반영**한다 — 세션 예산 가시성이 "이 턴에 어디까지 할지" 판단 근거라 워크플로의 일부다.

1. `templates/statusline.py` 를 `~/.claude/statusline.py` 로 복사 (플레이스홀더 치환 불필요, 그대로 복사).
2. `~/.claude/settings.json` 의 `statusLine` 에 등록 — command 는 **인터프리터 감지형**(macOS `python3` / Windows `python` 공용):

```json
"statusLine": {
  "type": "command",
  "command": "sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 <HOME>/.claude/statusline.py || exec python <HOME>/.claude/statusline.py'",
  "padding": 0,
  "refreshInterval": 60
}
```

   `<HOME>` 는 실제 홈 절대경로로 치환(`/Users/<you>` · `/home/<you>` · `C:/Users/<you>`). `refreshInterval: 60`(초=1분)은 세션 **유휴 상태에서도** 사용률·reset 카운트다운·`/effort` 상태를 최신화한다(이벤트 갱신에 추가, API 비소비).
3. 검증: 새 세션에서 상태바에 `CW ▓… %` + 모델 옆 `[high]`(현재 /effort) 가 뜨면 OK.

> **주의**: bare `python <HOME>/.claude/statusline.py` 는 macOS(python 부재)에서 상태바가 **안 뜬다** — 감지형 필수. `~/.claude/`(전역)라 프로젝트마다 재설치는 불필요하지만, 하네스 미적용으로 넘어가지 않도록 부트스트랩 필수 항목으로 둔다. PowerShell 폴백 Windows 는 git-bash 필요(`sh` 부재 시 미동작).

---

## 단계 7 - 첫 task 로 검증

### 7.1 self-eval

```bash
# CI Gate 컴파일
python3 -m py_compile .agent/scripts/ci_gate_<project>.py

# settings.local.json JSON
python3 -c "import json; json.load(open('.claude/settings.local.json', encoding='utf-8')); print('JSON OK')"

# frontmatter 점검 (commands)
for f in .claude/commands/*.md; do
  head -1 "$f" | grep -q "^---$" || echo "[NO_FRONTMATTER] $f"
  grep -q "^description:" "$f" || echo "[NO_DESCRIPTION] $f"
done

# frontmatter 점검 (agents)
for f in .claude/agents/*.md; do
  for k in name description model tools; do
    grep -q "^$k:" "$f" || echo "[NO_$k] $f"
  done
done

# eval 계열 이중 봉쇄 점검 (permissionMode: plan)
for f in .claude/agents/eval_*.md; do
  grep -q "^permissionMode: plan" "$f" || echo "[NO_PERMISSIONMODE] $f"
done

# hook 일치성
grep -q "ci_gate_<project>.py" .claude/settings.local.json && \
  [ -f .agent/scripts/ci_gate_<project>.py ] && echo "hook OK"
```

모든 명령이 OK / 빈 출력이면 통과.

(선택) `templates/scripts/` 의 스크립트 5종(`archive_tasks.py` / `harness_doctor.py` / `harness_manifest.py` / `pre_gate.py` / `stop_gate.py`)을 `.agent/scripts/` 로 복사하고 doctor 를 1회 실행해 설치 무결성을 확인한다. manifest 는 `python3 .agent/scripts/harness_manifest.py generate --kit-version 1.5.0` 로 생성. (pre_gate/stop_gate 는 opt-in - `settings.pretooluse.json.example` 참조)

### 7.2 최종 보고

```
## 단계 7 - 하네스 부트스트랩 완료

### 생성된 자산
- CLAUDE.md (<N>줄)
- .claude/settings.local.json
- .claude/commands/: <X>개
- .claude/agents/: <Y>개
- .agent/HARNESS_GUIDE.md (<M>줄)
- .agent/context/<PROJECT_UPPER>_BRAIN.md (<P>줄)
- .agent/context/<PROJECT_UPPER>_STATE.md (<Q>줄)
- .agent/scripts/ci_gate_<project>.py
- .agent/tasks/archive/
- tmp/
- ~/.claude/statusline.py + `~/.claude/settings.json` statusLine 등록 [필수, 전역]

### 검증 결과
- py_compile: PASS
- JSON 파싱: PASS
- frontmatter 정합성 (commands <X>개 / agents <Y>개): PASS
- hook 일치성: PASS

### 다음 단계 (사용자에게 권장)
1. Claude Code 재시작 - 새 CLAUDE.md 자동 로드 확인
2. `/read_<project>` 호출 - BRAIN/STATE 읽고 분석 출력 확인
3. 사소한 작업 1개로 `/plan_agent_<project>` → `/dev_<project>` → `/eval_agent_<project>` 4단계 워크플로 실험
4. 정상 동작 확인 후 `/sync_brain` → `/commit_push` 로 하네스 부트스트랩 커밋

### 변경된 파일
git status:
- 새 파일: <count>
- 기존 코드 변경: 없음 (하네스만 추가, 코드는 무손)
```

---

## ⚠️ Claude 에게 - 추가 지침

### 영역 침범 금지

이 부트스트랩 작업 중 **기존 코드 파일을 수정하지 말 것**. 하네스만 추가한다. 사용자가 의도치 않은 코드 변경을 발견하면 신뢰 깨짐.

### 한 번에 너무 많이 하지 말 것

각 단계 사이에 사용자 응답을 기다린다. 7단계 한 번에 다 끝낸 후 마지막에 검토 받으려고 하지 말 것. 중간 컨펌 게이트가 핵심.

### plan.md 와 동일 패턴

7단계 결과를 `.agent/tasks/task_harness_<TS>_initial_bootstrap/plan.md` 에 기록할 것. 사용자 응답 / 결정 / 추가 사항도 모두 plan.md 에 적어둔다. 이게 6개월 후 "왜 이 하네스가 이렇게 생겼나" 답변의 SSOT.

### 사용자가 "stop=no clarifying" 모드일 때

매 게이트에서 사용자 응답 없이 진행해야 하는 경우 다음 default 결정:
- 슬러그: 디렉토리 이름의 의미있는 짧은 부분 (예: `sampleapp_app` → `sampleapp`)
- 통신 언어: 한국어 (사용자가 한글 입력 중이면)
- 배포 워크플로: README 에 OTA / store / publish 언급 있으면 "예", 없으면 "아니오"
- Co-Authored-By: 금지 (보수적 default)
- 자동 스테이징 금지: `.env*` `*.key*` `*.p12` `tmp/` `.agent/tasks/*.result` 기본 집합
- 커밋 type: 한국어 통신이면 `추가|갱신|수정|리팩터|테스트|문서` / 영어면 `feat|fix|refactor|test|docs`

모든 default 결정을 plan.md 에 명시.

### 시블링 repo 가 감지된 경우

`../<sibling>/` 디렉토리가 보이면 단계 1 의 보고에서 **multi-repo 가능성** 명시. 사용자가 cross-repo 관계를 답하면 BRAIN.md §10 에 시블링 인터페이스 명시.

### 기존 하네스가 일부 있는 경우

분석 결과 `.claude/` 또는 `CLAUDE.md` 가 이미 일부 존재하면 **덮어쓰지 말고** 사용자에게:

> "기존에 일부 하네스가 있습니다. 다음 옵션:
> 1. 기존 자산 보존하고 누락 부분만 보강
> 2. 백업 (.bak) 후 새로 작성
> 3. 인터랙티브 - 각 파일별 사용자가 결정
>
> 어떻게 진행할까요?"

---

## 끝 - 그러나 진짜 시작

이 7단계가 끝나면 사용자의 프로젝트는 sampleapp 와 **동등한 출발선** 의 하네스를 갖는다. 이후 사용자는 일반 워크플로 (`/plan_agent_<project>` → `/dev_<project>` → `/eval_agent_<project>` → `/sync_brain` → `/commit_push`) 로 작업한다.

### ⚠️ 사용자에게 마지막으로 전달할 메시지

**하네스 부트스트랩은 완성이 아니라 출발점**이다. 진짜 가치는 그 이후 수개월에 걸쳐 누적된다.

다음 4주 동안 **진화 트리거 관찰**:

1. Claude 가 같은 종류 실수를 2번 했다 → 즉시 `/plan_agent_harness` 로 CI Gate 검사 추가
2. 같은 명령 시퀀스를 3번 손으로 입력했다 → 새 슬래시 추가
3. 새 세션 워밍업이 자꾸 길어진다 → BRAIN/STATE 보강
4. "아 이거 절대 손대면 안 되는 거였네" 사후 인지 → CLAUDE.md 비타협 표 추가

이 진화 자체가 메타 워크플로의 존재 이유.

**"하네스 완성됐다" 는 말은 위험 신호** - 코드는 변하는데 하네스가 멈춰있으면 Claude 가 같은 사고를 반복한다. 건강한 상태는 `task_harness_*` 폴더가 2~4주에 1회 정도 새로 생기는 것.

상세: `harness_bootstrap/01_philosophy.md` §원칙 9 + `harness_bootstrap/OVERVIEW.md` §🌱 살아있는 하네스

질문 있으면 `harness_bootstrap/` 의 다른 .md 파일들 참조.
