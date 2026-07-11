# Harness Onboarding Kit

> Claude Code 에 적용하는 **하네스 엔지니어링** 의 온보딩 패키지.
> 다른 개발자에게 통째로 전달하면 자기 프로젝트에 동일 철학으로 안전망을 구축할 수 있다.

> 💡 **한 페이지에서 전체 그림 + 모든 문서 링크가 필요하면 → [`OVERVIEW.md`](./OVERVIEW.md)**

---

## 무엇인가

Claude Code (Anthropic 의 공식 CLI) 로 코딩할 때 **컨텍스트 망각 / 비타협 항목 무심코 변경 / 셀프 PASS / 시크릿 누수** 같은 실패 모드를 차단하기 위한 9가지 원칙과, 그것을 구현하는 **표준 디렉토리/슬래시 커맨드/서브에이전트/CI Gate hook** 의 청사진. 한마디로 "Claude 가 폭주하지 않도록 잡아주는 안전 장치(harness)" 다.

⚠️ **가장 중요한 메시지** - 하네스는 **한 번 셋업 후 끝나는 결과물이 아니다**.

Claude 의 매 세션 학습이 휘발되는 한계 때문에, "이번에 깨달은 것" 을 **하네스 자산에 영구 기록** 해야 누적된다. Claude 의 반복 실수 + 사용자의 반복 작업 + 새 비타협 발견이 트리거가 되어 **코드와 함께 진화**한다. 메타 워크플로 (`/plan_agent_harness` 등) 가 그 진화를 빠르고 안전하게 만든다. 상세는 [`OVERVIEW.md`](./OVERVIEW.md) §🌱 살아있는 하네스.

---

## 누구를 위해

| 독자 | 진입점 |
|---|---|
| **사람 개발자** - 우리 하네스 구조를 이해하고 자기 프로젝트에 직접 적용하고 싶음 | `01_philosophy.md` → `02_architecture.md` → ... → `09_adapt_checklist.md` 순서 |
| **Claude 자신** - 다른 프로젝트 디렉토리에서 누군가 이 폴더를 던지면서 "이거 보고 우리 프로젝트에 하네스 만들어줘" 요청받음 | **`BOOTSTRAP_PROMPT.md` 만 읽으면 됨** (7단계 자동 분석) |

두 독자가 동일 정보를 다른 깊이로 사용한다.

---

## 폴더 구조

```
harness_bootstrap/
├── README.md                            ← 이 파일 (진입점)
├── OVERVIEW.md                          ← 한 페이지 전체 그림 + 문서 인덱스 ★
├── BOOTSTRAP_PROMPT.md                  ← Claude 에게 던지는 핵심 프롬프트 (7단계 자동 부트스트랩)
├── CHANGELOG.md                         ← 버전 이력
├── UPGRADE.md                           ← (선택) 킷 업데이트 절차 + 네임스페이스 소유권 규약
│
├── 01_philosophy.md                     9가지 핵심 원칙
├── 02_architecture.md                   .claude/ + .agent/ + CLAUDE.md 3 자산 구조
├── 03_workflow_patterns.md              일반 / 하네스 / 배포 / 서버사이드 워크플로 비교
├── 04_ssot_brain_state.md               BRAIN/STATE 분리 원칙
├── 05_subagent_design.md                서브에이전트 권한 최소화 + frontmatter 설계
├── 06_ci_gate.md                        PostToolUse hook Python 스크립트 작성법
├── 07_task_lifecycle.md                 task_<TS>_<slug>/ + archive 자동화
├── 08_immutables.md                     비타협 항목 정의 가이드
├── 09_adapt_checklist.md                사람 개발자 직접 적용 8단계 절차
│
├── templates/                           플레이스홀더 포함 템플릿
│   ├── CLAUDE.md.template
│   ├── BRAIN.md.template
│   ├── STATE.md.template
│   ├── HARNESS_GUIDE.md.template
│   ├── settings.local.json.template
│   ├── ci_gate.py.template
│   ├── statusline.py                    (필수) 전역 상태바 - ~/.claude/ 에 그대로 복사
│   ├── settings.pretooluse.json.example (선택) PreToolUse hook opt-in 등록 예시
│   ├── scripts/                         (선택) 스크립트 자산 7종 - .agent/scripts/ 로 복사
│   │   ├── archive_tasks.py             (선택) status 기준 task 아카이브 (dry-run 기본)
│   │   ├── harness_doctor.py            (선택) 설치 무결성 진단
│   │   ├── harness_manifest.py          (선택) 배포 파일 해시 manifest
│   │   ├── pre_gate.py                  (선택) PreToolUse 커밋 게이트 + 위험 명령 차단 (opt-in)
│   │   ├── stop_gate.py                 (선택) Stop advisory - 턴 종료 시 변경 파일 광역 검사 (opt-in)
│   │   ├── model_policy.py              (선택) 모델 정책 적용/조회
│   │   └── glm_mode.py                  (선택) GLM 병행 - 실험적/opt-in
│   ├── commands/                        9개 슬래시 커맨드 템플릿
│   │   ├── read_PROJECT.md.template
│   │   ├── plan_agent_PROJECT.md.template
│   │   ├── dev_PROJECT.md.template
│   │   ├── eval_agent_PROJECT.md.template
│   │   ├── sync_brain.md.template
│   │   ├── commit_push.md.template
│   │   ├── plan_agent_harness.md.template
│   │   ├── dev_harness.md.template
│   │   └── eval_agent_harness.md.template
│   └── agents/                          4개 서브에이전트 템플릿
│       ├── plan_PROJECT.md.template
│       ├── eval_PROJECT.md.template
│       ├── plan_harness.md.template
│       └── eval_harness.md.template
│
└── examples/
    ├── sampleapp_snapshot/                  Android 앱 하네스 풀 구성 예시
    │   ├── CLAUDE.md
    │   ├── HARNESS_GUIDE.md
    │   ├── settings.local.json          절대 경로 → 플레이스홀더 치환됨
    │   ├── ci_gate_sampleapp.py
    │   ├── commands/                    13개 슬래시 커맨드 예시
    │   └── agents/                      6개 서브에이전트 예시
    ├── sampleapp_server_inventory/
    │   └── INVENTORY.md                 raw Next.js 프로젝트의 인벤토리 실례 (적용 전 상태)
    └── case_study.md                    sampleapp_app 종단 시나리오 + sampleapp_server 적용 가이드
```

---

## 두 가지 사용 시나리오

### 시나리오 1 - Claude 에게 자동 적용 요청

가장 빠른 길. Claude Code 를 자기 프로젝트 디렉토리에서 띄운 후 이렇게 말한다:

> "`harness_bootstrap/BOOTSTRAP_PROMPT.md` 를 읽고 거기 절차에 따라 이 프로젝트에 하네스를 구축해줘."

Claude 가 7단계 자동 부트스트랩 수행:
1. 프로젝트 분석 (`find` `git log` `package.json` 등)
2. 비타협 항목 추출 (사용자 컨펌)
3. SSOT 초안 (BRAIN/STATE)
4. 슬래시 + 서브에이전트 생성
5. CI Gate Python 스크립트
6. CLAUDE.md 작성
7. 첫 task 로 검증 (`/eval_agent_harness` 동등)

각 단계에 사용자 컨펌 게이트가 있어 중간 중단 / 방향 수정 가능.

### 시나리오 2 - 사람 개발자 수동 적용

원칙을 이해하고 직접 작성하고 싶다면:

1. `01_philosophy.md` 부터 `09_adapt_checklist.md` 까지 순서로 읽음
2. `09_adapt_checklist.md` 의 8단계 절차 따라 직접 작성
3. `templates/` 의 플레이스홀더 치환
4. `examples/sampleapp_snapshot/` 참고하여 디테일 비교

평균 1~2시간 (프로젝트 복잡도에 따라).

---

## 빠른 적용 (TL;DR)

자기 프로젝트 디렉토리에서:

```bash
# 1. 디렉토리 만들기
mkdir -p .claude/commands .claude/agents
mkdir -p .agent/context .agent/scripts .agent/tasks/archive

# 2. 템플릿 복사 + 치환
PROJECT=<your_slug>
cp <onboarding>/templates/CLAUDE.md.template CLAUDE.md
cp <onboarding>/templates/BRAIN.md.template .agent/context/${PROJECT^^}_BRAIN.md
cp <onboarding>/templates/STATE.md.template .agent/context/${PROJECT^^}_STATE.md
cp <onboarding>/templates/HARNESS_GUIDE.md.template .agent/HARNESS_GUIDE.md
cp <onboarding>/templates/settings.local.json.template .claude/settings.local.json
cp <onboarding>/templates/ci_gate.py.template .agent/scripts/ci_gate_${PROJECT}.py
# 슬래시 / 에이전트 템플릿 9+4 개도 비슷하게 복사 후 PROJECT 치환

# 3. Claude Code 실행 → CLAUDE.md 자동 로드 확인 → /read_<project> 호출
```

PowerShell 에서는:

```powershell
# 1. 디렉토리 만들기
New-Item -ItemType Directory -Force .claude/commands, .claude/agents | Out-Null
New-Item -ItemType Directory -Force .agent/context, .agent/scripts, .agent/tasks/archive | Out-Null

# 2. 템플릿 복사 + 치환
$PROJECT = "<your_slug>"
Copy-Item <onboarding>/templates/CLAUDE.md.template CLAUDE.md
Copy-Item <onboarding>/templates/BRAIN.md.template ".agent/context/$($PROJECT.ToUpper())_BRAIN.md"
Copy-Item <onboarding>/templates/STATE.md.template ".agent/context/$($PROJECT.ToUpper())_STATE.md"
Copy-Item <onboarding>/templates/HARNESS_GUIDE.md.template .agent/HARNESS_GUIDE.md
Copy-Item <onboarding>/templates/settings.local.json.template .claude/settings.local.json
Copy-Item <onboarding>/templates/ci_gate.py.template ".agent/scripts/ci_gate_$PROJECT.py"
# 슬래시 / 에이전트 템플릿도 비슷하게 복사 후 PROJECT 치환

# 3. Claude Code 실행 → CLAUDE.md 자동 로드 확인 → /read_<project> 호출
```

플레이스홀더 (`{{PROJECT}}` 등) 는 `09_adapt_checklist.md` 의 표 참조.

---

## 메타 워크플로 - 하네스 자체를 고도화하는 슬래시

본 kit 이 제공하는 슬래시 중 **3개는 "자기 자신을 위한" 메타 워크플로**다:

- `/plan_agent_harness` - 하네스 변경 계획 (서브에이전트)
- `/dev_harness` - 메타 파일 편집 (메인 세션)
- `/eval_agent_harness` - 무결성 점검 (서브에이전트)

**왜 별도로 존재하나** - 4가지 이유:

1. **영역 침범 차단** - 코드 + 메타 동시 변경 시 plan 의 영향 평가 항목이 폭증하여 사용자 컨펌 게이트가 의미를 잃음
2. **셀프 변경의 위험** - Claude 가 자기 안전망(CI Gate / 권한 / archive 룰)을 무심코 약화시키면 다음 작업부터 보호망이 침묵으로 사라짐
3. **작업 흔적 보존** - `task_harness_<TS>_` prefix 로 6개월 후에도 "왜 이 슬래시가 추가됐는가" 즉시 검색 가능
4. **점검 도구가 다르다** - 일반 eval(컴파일/단말) vs 하네스 eval(JSON 파싱/frontmatter regex/hook 일치성)

**사용 시점 6가지**:
1. 새 슬래시 명령이 필요할 때
2. 서브에이전트 tools 권한 조정
3. CI Gate 검사 항목 추가 (같은 종류 사고 두 번 났을 때)
4. BRAIN.md 키 인벤토리 마이그레이션
5. 비타협 항목 표가 8개 넘었을 때
6. 다른 OS 환경 / 협업자 추가

상세 비교 + 안티패턴: [`OVERVIEW.md`](./OVERVIEW.md) §🛠️ 하네스 자체를 고도화하는 메타 워크플로

---

## 적용 예시 (examples/)

**sampleapp_app** (Android 앱)
- OTA 배포 / 크래시 보고 / 라이선스 / 진단 수집까지 포함한 풀 스택 하네스 구성
- examples/sampleapp_snapshot/ 에 전체 자산 수록

**sampleapp_server** (Next.js admin webapp)
- raw 상태 (아직 하네스 미적용)
- examples/sampleapp_server_inventory/ 에 적용 시 예상 구조 미리보기

두 예시가 **같은 하네스 골격** 을 서로 다른 스택에서 운영하는 모습을 보여준다.

---

## 라이선스

자유롭게 자기 프로젝트에 적용 / 수정 / 재배포 가능.

---

## 다음 읽을 곳

- **한 페이지에서 워크플로 + 모든 문서 인덱스 한눈에** → **[`OVERVIEW.md`](./OVERVIEW.md)** ★
- 5분 안에 핵심 잡고 싶다 → [`01_philosophy.md`](./01_philosophy.md) (9가지 원칙)
- Claude 가 자동으로 적용해주길 원한다 → [`BOOTSTRAP_PROMPT.md`](./BOOTSTRAP_PROMPT.md)
- 직접 손으로 적용하고 싶다 → [`09_adapt_checklist.md`](./09_adapt_checklist.md)
- 적용 예시를 먼저 보고 싶다 → [`examples/case_study.md`](./examples/case_study.md)
- sampleapp 예시 구성을 보고 싶다 → [`examples/sampleapp_snapshot/`](./examples/sampleapp_snapshot/)
