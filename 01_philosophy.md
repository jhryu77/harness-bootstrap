# 01. 하네스 엔지니어링 철학

> 이 문서는 우리 harness 가 따르는 **9가지 핵심 원칙** 을 담는다.
> 다른 프로젝트에 이식할 때는 **원칙은 그대로**, 구현 세부는 그 프로젝트에 맞게 변환한다.
>
> ⚠️ **9번째 원칙 (살아있는 하네스) 이 가장 중요** - 한 번 셋업 후 동결되는 것이 아니라 코드와 함께 진화한다.

---

## 왜 "하네스" 인가

말 그대로 "Claude 가 폭주하지 않도록 잡아주는 안전 장치 (harness)" 다.

LLM 코딩 보조는 강력하지만 다음 실패 모드가 흔하다:

| 실패 모드 | 우리 대응 |
|---|---|
| 컨텍스트 망각 (다음 세션 = 빈 상태) | **CLAUDE.md + BRAIN/STATE SSOT 자동 로드** |
| 비타협 항목을 무심코 변경 | **CLAUDE.md 와 plan agent 가 비타협 표 미리 주입** |
| 충동적 코드 변경으로 멀쩡한 곳 깨뜨림 | **3단계 워크플로 (plan → dev → eval) 강제** |
| 임시 파일/시크릿 무의식 커밋 | **CI Gate hook 으로 매 Edit/Write 정적 검증** |
| 무한 자가 합리화 (스스로 PASS 선언) | **plan / dev / eval 을 별도 서브에이전트로 권한 격리** |
| 작업 흔적 휘발 (왜 그렇게 했는지 사라짐) | **task_\<TS\>_\<slug\>/ 폴더에 plan.md + tasklist.md + result 영구 보존** |

이 표가 곧 우리 하네스의 존재 이유다.

---

## 9가지 핵심 원칙

### 원칙 1 - SSOT (Single Source of Truth) 분리

지식을 **저빈도 (BRAIN)** 와 **고빈도 (STATE)** 로 명확히 분리한다.

| 구분 | BRAIN.md | STATE.md |
|---|---|---|
| 갱신 주기 | 거의 영구 (수개월~수년) | 매 task 마다 |
| 내용 | 패키지 구조 / 핵심 클래스 / 키 인벤토리 / 비타협 항목 / 빌드 토폴로지 | 현재 Phase / 구현된 화면 목록 / 최근 task 요약 / 현재 git HEAD |
| 자동 갱신 도구 | (수동, plan_harness 경유) | `/sync_brain` 슬래시 |

**원칙적으로 둘은 분리되어야 한다.** STATE 가 매번 바뀌어도 BRAIN 은 안정. BRAIN 이 바뀔 때는 마이그레이션이 함께 가야 함을 의미.

### 원칙 2 - 3단계 워크플로 (plan → dev → eval)

모든 비-사소 작업은 다음 3단계를 거친다:

```
[1] plan_agent  → task_<TS>/plan.md + tasklist.md 작성 (서브에이전트 격리, Write 권한 tasks/ 만)
       ↓
[2] dev         → 메인 세션이 plan 에 따라 코드/문서 편집 (Edit/Write 권한 풀)
       ↓
[3] eval_agent  → result 파일 작성 PASS/FAIL 판정 (서브에이전트 격리, Write 권한 result 만)
       ↓
[4] 사용자 컨펌 → /sync_brain → /commit_push
```

**각 단계가 독립 서브에이전트** 이고 권한이 다르다. dev 에이전트가 자기 작업을 자기가 PASS 선언하지 못한다.

### 원칙 3 - task 격리

모든 작업은 `task_<YYYYMMDD>_<HHMM>_<slug>/` 폴더에 영구 기록된다:

```
.agent/tasks/task_20260512_2038_phase_z_mac_validation/
├── plan.md          # 변경 범위 / 영향 평가 / 비타협 확인 / 단계별 흐름
├── tasklist.md      # 체크박스 형식 실행 단위
└── <project>.result # eval 단계의 PASS/FAIL 판정
```

120분 mtime 초과 시 `archive/` 자동 이동. 활성 작업과 완료 작업이 시각적으로 분리된다.

### 원칙 4 - 서브에이전트 최소 권한

`.claude/agents/*.md` frontmatter 에서 각 서브에이전트의 **tools** 화이트리스트를 좁힌다:

- **plan_xxx**: Read / Glob / Grep / Bash / **Write** (단 tasks/ 하위만) / TaskCreate
- **eval_xxx**: Read / Glob / Grep / Bash / TaskList (Write 없음 + permissionMode: plan - result 는 YAML 텍스트로 반환, 기록은 메인 세션)

이로써 plan 에이전트가 코드를 수정하거나, eval 에이전트가 자기 PASS 결과를 임의로 조작하는 것을 구조적으로 차단한다.

### 원칙 5 - CI Gate hook

`.claude/settings.local.json` 의 PostToolUse hook 으로 매 Edit/Write 시 Python 스크립트를 자동 실행한다.

```json
"hooks": {
  "PostToolUse": [{
    "matcher": "Edit|Write",
    "hooks": [{ "type": "command", "command": "python .agent/scripts/ci_gate_<project>.py" }]
  }]
}
```

검사 3종 (공통):
1. **임시 파일 위치** - 루트에 `tmp_*` `verify_*` `diag_*` `check_*` 직접 생성 차단 → `tmp/` 폴더 유도
2. **시크릿 패턴** - JWT / AWS / Google API / GitHub PAT / PEM Private Key 정규식
3. **언어별 구문 sanity** - Kotlin `{}` 매칭 / Python AST / TS 등 (프로젝트별 추가)

위반 시 **stderr 출력 → Claude 컨텍스트에 자동 주입** → 즉시 인지 후 수정.

### 원칙 6 - CLAUDE.md 자동 로드 압축본

`CLAUDE.md` 는 매 Claude Code 세션 시작 시 **자동 로드** 된다. 따라서 여기에 다음 압축 정보만 둔다:

- 프로젝트 한줄 소개 + 패키지/스택
- 하네스 워크플로 표 (슬래시 커맨드 → 역할 매핑)
- **비타협 항목 표** (런처 / 분할 / Prefs 등 - 변경 시 사용자 컨펌 필수 항목)
- 빌드/실행 커맨드 정형구
- 커밋 규칙 (자동 스테이징 금지 패턴 / Co-Authored-By 정책)
- BRAIN/STATE/HARNESS_GUIDE 로 가는 포인터

**CLAUDE.md 자체에 코드 변경 가이드를 길게 쓰지 않는다** - 거기에 둘 내용은 워크플로상 `dev_<project>.md` (슬래시 커맨드) 가 담당.

### 원칙 7 - 3종 워크플로 분리

같은 plan/dev/eval 패턴이지만 **대상 영역에 따라 3종으로 분리**한다:

| 워크플로 | 대상 | 슬래시 커맨드 |
|---|---|---|
| 일반 코드 | 프로젝트 비즈니스 코드 (`app/src/...`) | `/plan_agent_<project>` / `/dev_<project>` / `/eval_agent_<project>` |
| 하네스 자체 | `.claude/` `.agent/` `CLAUDE.md` 변경 | `/plan_agent_harness` / `/dev_harness` / `/eval_agent_harness` |
| 배포 | versionCode 증분 + Storage 업로드 + DB 토글 | `/plan_agent_<release>` / `/dev_<release>` / `/eval_agent_<release>` |

각 워크플로의 서브에이전트가 **다른 권한** 을 갖는다. 하네스 변경 도중에 코드를 손대거나, 배포 작업이 BRAIN 을 갱신하는 등 영역 침범을 차단.

### 원칙 8 - 응답 언어 / 커밋 정책 명시

암묵적으로 두지 않고 **CLAUDE.md 에 명시**한다:

- "모든 응답 / 주석 / 문서는 **한국어**" (또는 영어, 프로젝트별)
- "Co-Authored-By 라인 **금지** / **허용**" (사용자 선호)
- "자동 스테이징 금지 파일 패턴" (`*.keystore` `.env` `.env.*` `local.properties` `tasks/*.result` `tmp/` 등)
- "커밋 메시지 type 어휘" (`추가|갱신|수정|리팩터|테스트|문서` 또는 영문 `feat|fix|refactor|test|docs`)

명시하지 않으면 Claude 가 매 세션 다른 결정을 내려서 일관성이 깨진다.

### 원칙 9 - 하네스는 살아있다 (Living Harness)

**가장 중요한 원칙**. 하네스는 한 번 부트스트랩하면 끝나는 결과물이 **아니다**.

**Claude 의 실수 + 사용자의 반복 작업 + 발견되는 새 비타협 항목 + 진화하는 컨텍스트** 가 하네스를 지속적으로 진화시킨다. 개발 코드와 **공동 진화** 한다.

#### 진화 트리거 4종

| 트리거 | 신호 | 진화 액션 |
|---|---|---|
| **Claude 의 반복 실수** | 같은 종류 사고가 두 번 발생 (예: 시크릿 누수 / 매직 넘버 변경 / 임시 파일 루트 생성) | CI Gate 검사 항목 추가 / CLAUDE.md 비타협 표 보강 |
| **사용자의 반복 작업** | 같은 단계 시퀀스를 손으로 3회 이상 입력 (예: "BRAIN 읽어 → 코드 인덱스 → git log") | 새 슬래시 커맨드 추가 (예: `/read_<project>`) |
| **컨텍스트 휘발** | 새 세션 / 다른 환경에서 같은 정보를 재구축하느라 시간 낭비 | BRAIN/STATE 에 영구 기록 또는 CLAUDE.md 자동 로드 강화 |
| **새 비타협 발견** | "이거 변경하면 사용자 데이터 손실/제품 정체성 파괴" 사후 인지 | BRAIN.md §비타협 + plan_agent 체크리스트에 추가 |

이 트리거가 발견되면 **즉시 `/plan_agent_harness`** 진입. 차일피일 미루지 않는다. "다음에 정리해야지" 는 같은 사고의 3번째 반복으로 이어진다.

#### 진화 곡선 예시 - sampleapp

```
Phase 0 (부트스트랩, day 0):
  - 슬래시 5개 (read/plan/dev/eval/commit_push)
  - CI Gate 검사 1종 (임시 파일 위치)
  - BRAIN.md 30줄 / STATE.md 20줄

Phase 1~3 (week 1~3, 좌우분할 + Picker + 임베드 구현):
  - 슬래시 추가: sync_brain (STATE 자동 갱신 필요성 발견)
  - CI Gate 추가: Kotlin 괄호 검사 (편집 중 잘림 사고 2회)
  - BRAIN.md 80줄 (디렉토리 트리 + 클래스 책임 + 영구화 키 2개)

Phase L (라이선스, week 5):
  - 슬래시 추가: plan_agent_ota_release / dev_ota_release / eval_agent_ota_release (배포 워크플로 분리)
  - CI Gate 추가: 시크릿 패턴 (한 번 SUPABASE_ANON_KEY 누수 사고)
  - BRAIN.md 200줄 (8개 SharedPreferences + Supabase 의존)

Phase O10 (크래시 보고, week 8):
  - 서브에이전트 추가: eval_ota_release (단말 + Storage + DB 통합 검증)
  - CI Gate 추가: 분할 비율 상수 회귀 검사 (MIN/MAX/DEFAULT 누가 무심코 변경한 사고)
  - BRAIN.md 367줄 (11개 Prefs + 카컴페터 분석 §11 추가)
  - 메타 워크플로 자체 진화: plan_harness 의 본문에 "BRAIN 키 인벤토리 마이그레이션 시 코드 동반" 명시 추가

Phase Z (단말 진단, week 10):
  - BRAIN.md 12개 Prefs (diagnostics_prefs 추가)
  - STATE.md §6 Phase 표 30+ 행
  - 12 SharedPreferences 인벤토리 + 외부 인터페이스 8종

→ 10주 동안 하네스 자체가 30+ 회 진화. 모든 진화가 task_harness_<TS>/ 폴더에 기록.
```

처음의 5개 슬래시 / 1종 검사가 10주 후 **13 슬래시 / 6 서브에이전트 / 3종 CI Gate 검사 / 367줄 BRAIN** 으로 성장. 같은 곡선이 코드 측의 `Phase 1 → Phase O10` 진행과 동기.

#### 진화 비용 = 메타 워크플로 자체의 가치

만약 하네스가 동결된 결과물이면 진화 자체가 **무겁고 위험한 작업** 이 된다. 메타 워크플로 (`plan_harness/dev_harness/eval_harness`) 가 **진화를 안전하고 빠른 절차** 로 만든다:

- 일반 작업 중 트리거 발견 → `/plan_agent_harness` 10~30분 → 진화 완료
- frontmatter 회귀 / hook 일치성 자동 점검으로 진화가 다른 부분을 안 깨는 확신

즉 메타 워크플로는 **하네스의 self-amendment 메커니즘**. 헌법의 개헌 절차와 같은 구조.

#### "완성" 의 함정

"우리 하네스 완성됐다" 는 표현은 **위험 신호**. 둘 중 하나:

1. 프로젝트가 정지 (개발이 안 일어남)
2. 하네스가 코드 변화를 따라가지 못하고 있음 (=진화 부채 누적)

건강한 상태는 `task_harness_*` 폴더가 **2~4주에 1회 정도** 생성되는 것. 너무 빈번하면 변경 불안정, 너무 드물면 진화 부채.

---

## 안티패턴 (피해야 할 것)

| 안티패턴 | 왜 나쁜가 |
|---|---|
| CLAUDE.md 에 모든 컨텍스트를 다 적기 | 자동 로드 비용. SSOT 분산. STATE 갱신 비용 폭증 |
| plan 단계 생략하고 바로 dev | 영향 평가 누락 → 비타협 항목 무심코 변경 |
| eval 단계 생략 (메인 세션이 셀프 PASS) | 자기검증 무력화 |
| task 폴더 없이 작업 | 작업 흔적 휘발. 회귀 시 추적 불가 |
| 서브에이전트에 Edit/Write 풀권한 부여 | 권한 격리 무력화 |
| CI Gate 를 IDE 별 별도 스크립트로 분리 | hook 일관성 깨짐 |
| BRAIN 과 STATE 를 한 파일로 합치기 | 갱신 빈도 차이로 인한 conflict 폭증 |
| **하네스를 한 번 셋업 후 동결** | Claude 의 반복 실수 / 사용자 반복 작업이 진화 부채로 누적 |
| **같은 사고 3회 발생까지 메타 변경 미루기** | 다음 작업에서 4번째 같은 사고 보장됨 |
| 메타 변경을 일반 task 에 섞기 | plan 의 영향 평가 폭증 + 진화 흔적 검색 불가 |

---

## 다음 단계

- `02_architecture.md` - 위 원칙들이 어떤 파일/디렉토리로 구현되는지
- `03_workflow_patterns.md` - 3종 워크플로의 실제 흐름
- `04_ssot_brain_state.md` - BRAIN/STATE 의 구체 작성법
