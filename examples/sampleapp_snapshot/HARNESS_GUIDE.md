# sampleapp 하네스 엔지니어링 사용 가이드

> **목적**: Claude Code 단독으로 plan / dev / eval 사이클을 일관성 있게 운영하기 위한 운영 매뉴얼.
> **참조 모델**: 외부 풀 스케일 하네스(FullScaleApp)에서 차용하여 sampleapp 도메인에 맞게 단순화·재구성. 외부 의존 없음.

---

## 1. 전체 구조

```
sampleapp_launcher/                                 (Mac: /Users/<user>/workspace/sampleapp_launcher · 과거 Windows 시점: G:\WorkSpace\sampleapp)
├── CLAUDE.md                                  하네스 워크플로 + 비타협 항목 + 빌드 + 디렉토리 규칙
├── .claude/
│   ├── settings.local.json                    PostToolUse hook + 권한 화이트리스트
│   ├── commands/                              슬래시 커맨드 (UI 진입점, 10개)
│   └── agents/                                서브에이전트 (도구 물리 제한, 4개)
└── .agent/
    ├── HARNESS_GUIDE.md                       (이 파일) 운영 매뉴얼
    ├── context/
    │   ├── SAMPLEAPP_BRAIN.md                     불변 지식 (패키지/모듈/Prefs 키)
    │   └── SAMPLEAPP_STATE.md                     시점 스냅샷 (Phase / 빌드 / 최근 task)
    ├── scripts/
    │   └── ci_gate_sampleapp.py                   PostToolUse 정적 검증 (3검사)
    └── tasks/
        ├── task_YYYYMMDD_HHMM/                일반 작업 폴더 (plan.md + tasklist.md + sampleapp.result)
        ├── task_harness_YYYYMMDD_HHMM/        하네스 자체 작업 폴더
        └── archive/                     mtime 120분 초과 자동 이동
```

---

## 2. 핵심 워크플로 (Plan → Dev → Eval)

```
[메인 세션]
  /read_sampleapp                         BRAIN/STATE 로드 + 코드 인덱스 + 다음 액션 제안
       ↓
  /plan_agent_sampleapp <목적>            plan_sampleapp 서브에이전트 호출
       ↓                              → task_YYYYMMDD_HHMM/plan.md + tasklist.md 생성
                                      → archive 자동 (mtime 120분 초과)
  /dev_sampleapp                          메인 세션이 코드 구현
       ↓                              → 매 Edit/Write 시 CI Gate 자동 발화
  /eval_agent_sampleapp                   eval_sampleapp 서브에이전트 호출
       ↓                              → sampleapp.result 작성 (PASS/FAIL)
  PASS → ADB 설치 질문(A/B/C) → /sync_brain (필요 시) → /commit_push
  FAIL:RE_DEV → 원인 수정 후 /dev_sampleapp 재진입
  FAIL:RE_PLAN → /plan_agent_sampleapp 재수립
```

**역할 분담**:
| 주체 | 도구 | 책임 |
|---|---|---|
| 메인 세션 | 모두 (Edit/Write 포함) | 코드 구현 + 슬래시 진입 + 사용자 응답 처리 |
| `plan_sampleapp` 서브에이전트 | Read/Glob/Grep/Bash/**Write 한정**/TaskCreate | 계획 수립. Write 는 `.agent/tasks/task_*/` 하위만 |
| `eval_sampleapp` 서브에이전트 | Read/Glob/Grep/Bash/TaskList | 평가 + `sampleapp.result` Bash heredoc 작성. Edit/Write disallow |

---

## 3. 프로젝트 특성 (FullScaleApp 과 다른 점)

| 영역 | sampleapp |
|---|---|
| 모듈 | 단일 (`:app`). KMP/Compose Multiplatform **없음** |
| UI | View 시스템 + ConstraintLayout + Guideline + Fragment + ViewBinding |
| 도메인 | 차량용 런처 (CATEGORY_HOME / landscape / configChanges 풀세트) |
| 분할 | 좌/우 70:30 기본, 20%~80% 클램프, SharedPreferences 영구화 |
| 패널 임베드 | VirtualDisplay + reflection `injectInputEvent` (시그너처 권한 fail-soft 의무) |
| 보안 | DTx 비타협 항목 **없음** - 런처 도메인. allowBackup=true 허용 |
| 외부 의존 | 외부 SSOT/sibling 프로젝트/원격 API **없음** (자기 완결) |
| 통신 언어 | 한국어 (모든 문서 한글, KDoc 한글) |

---

## 4. CI Gate (자동 정적 검증)

`.claude/settings.local.json` 의 PostToolUse hook 이 매 `Edit|Write` 시 `ci_gate_sampleapp.py`(인터프리터 자동 감지: macOS python3/Windows python) 실행.

| # | 검사 | 위반 시 |
|---|---|---|
| 1 | **임시 파일 위치** - `tmp_*` / `verify_*` / `diag_*` / `check_*` 루트 직접 생성 금지 (tmp/ 폴더만 허용) | FAIL (즉시 stderr) |
| 2 | **시크릿 하드코딩** - JWT(`eyJ...`) / AWS(`AKIA...`) / Google(`AIza...`) / GitHub PAT(`ghp_/github_pat_`) / PEM Private Key | WARN |
| 3 | **Kotlin 괄호 매칭** - `.kt/.kts` 의 `{` `}` 카운트 비교 | WARN |

FullScaleApp 의 디자인 토큰 / 반응형 / DTx 보안 / Pose / RPC 검사 항목은 도메인 무관으로 모두 제거됨.

---

## 5. 슬래시 커맨드 / 서브에이전트 인벤토리

### 슬래시 커맨드 (`.claude/commands/`)

| 커맨드 | 역할 |
|---|---|
| `/read_sampleapp` | BRAIN/STATE 로드 + 코드 인덱스 + Phase·Prefs 키 현황 + 다음 액션 제안 |
| `/plan_agent_sampleapp` | `plan_sampleapp` 서브에이전트 호출 (계획 수립) |
| `/dev_sampleapp` | 메인 세션이 코드 구현. 5섹션 도메인 가이드 (런처 / 분할 / 슬롯 / 임베드 / Picker) |
| `/eval_agent_sampleapp` | `eval_sampleapp` 서브에이전트 호출 (평가) |
| `/plan_agent_harness` | `plan_harness` 서브에이전트 호출 (하네스 자체 변경 계획) |
| `/dev_harness` | 메인 세션이 `.claude/`·`.agent/` 자체 편집 |
| `/eval_agent_harness` | `eval_harness` 서브에이전트 호출 (하네스 무결성 평가) |
| `/sync_brain` | `SAMPLEAPP_STATE.md` 갱신 + `SAMPLEAPP_BRAIN.md` 갱신 필요 판별→컨펌 후 반영 |
| `/test_sampleapp` | 수동 검증 체크리스트 (Build / 런처 진입 / 분할 / 슬롯 / fail-soft) |
| `/commit_push` | git commit + push (Co-Authored-By 라인 금지) |

### 서브에이전트 (`.claude/agents/`)

| 에이전트 | 도구 |
|---|---|
| `plan_sampleapp` | Read/Glob/Grep/Bash/Write/TaskCreate/TaskList (Edit 없음, Write 는 `.agent/tasks/task_*/` 만) |
| `eval_sampleapp` | Read/Glob/Grep/Bash/TaskList. **disallowed: Edit, Write** |
| `plan_harness` | 동일 (대상만 `.claude/`·`.agent/`) |
| `eval_harness` | 동일 |

---

## 6. tasklist.md 표준 포맷 (5섹션)

```markdown
## sampleapp 검증 항목 (Ref: task_YYYYMMDD_HHMM)

### TC: 런처 진입
- [ ] CATEGORY_HOME / DEFAULT / LAUNCHER 정상 (홈 키로 후보 노출)
- [ ] landscape 강제 / configChanges 풀세트 보존

### TC: 분할 비율
- [ ] 초기 70% / 드래그 20%~80% 범위 클램프 (`coerceIn(MIN_PERCENT, MAX_PERCENT)`)
- [ ] ACTION_UP 후 SharedPreferences 저장 + 재시작 복원

### TC: 슬롯 - 앱 바인딩
- [ ] picker → 슬롯 적용 → PaneSlotPrefs 영구화
- [ ] 재시작 시 PackageManager.resolve 결과로 복원, stale 제거
- [ ] 자기 자신(`com.sampleapp.launcher`) 제외 (재귀 임베드 방지)

### TC: 패널 임베드 fail-soft
- [ ] 시그너처 미부여 환경에서 SecurityException 흡수
- [ ] `onEmbedFailed` Toast 안내, 크래시 0건
- [ ] reflection / hidden API 호출 모두 try-catch

### TC: 하네스 규격
- [ ] CI Gate 경고 0건
- [ ] plan.md 의 변경 파일 경계 준수
```

---

## 7. 하네스 관리 규칙 (12개)

1. **Plan 기반 개발** - 비타협 항목 변경은 `/plan_agent_sampleapp` 사이클을 거칠 것
2. **KST 타임스탬프** - `TZ="KST-9" date +%Y%m%d_%H%M` (Mac/Linux/Windows git-bash 모두 호환되는 POSIX offset)
3. **기기 테스트는 사용자 수동** - 에이전트는 `/test_sampleapp` 체크리스트 출력만, 실 설치는 사용자 컨펌 후
4. **CI Gate 준수** - 경고 stderr 출력 시 즉시 수정
5. **Brain/State 분리** - `/sync_brain` 은 STATE 만 매 task 후 갱신. BRAIN 은 패키지/모듈/Prefs 키 변경 시에만 수동 갱신
6. **tmp/ 폴더 격리** - 임시·실험 파일은 `tmp/` 만. 루트 직접 생성 시 CI Gate FAIL
7. **런처 비타협** - CATEGORY_HOME / DEFAULT / LAUNCHER 4개 카테고리 + landscape + configChanges 풀세트 보존
8. **분할 비율 비타협** - `MIN_PERCENT 0.20 / MAX_PERCENT 0.80 / DEFAULT_PERCENT 0.70` 상수 + `coerceIn` 클램프
9. **SharedPreferences 호환성** - `PaneSlot.storageKey` 변경 = 마이그레이션 필수, enum 순서 변경 금지
10. **Guideline 비율** - `layout_constraintGuide_percent` (0.0~1.0) 만 사용. dp 절대값 사용 금지
11. **시그너처 권한 fail-soft** - reflection / hidden API / `createVirtualDisplay` / `launchDisplayId` 호출 모두 try-catch 의무
12. **Co-Authored-By 라인 금지** - 사용자 선호. `/commit_push` 가 자동 생략

---

## 8. task 폴더 라이프사이클

```
생성        plan_sampleapp 가 mkdir -p .agent/tasks/task_${TS} (TS=KST 시각)
            ↓
작업        dev_sampleapp / eval_sampleapp 가 plan.md / tasklist.md / sampleapp.result 작성·갱신
            ↓
휴면        다음 plan_sampleapp 진입 시 mtime 120분 초과 폴더 자동 archive
            ↓
archive     .agent/tasks/archive/ 로 이동
```

**스캔 스니펫** (plan_sampleapp 진입부):
```bash
ARCHIVE_DIR=".agent/tasks/archive"
mkdir -p "$ARCHIVE_DIR"
find ".agent/tasks" -maxdepth 1 -type d -name "task_*" -mmin +120 | while read -r d; do
  mv "$d" "$ARCHIVE_DIR/" && echo "archived: $d"
done
TS=$(TZ="KST-9" date +%Y%m%d_%H%M)
TASK_DIR=".agent/tasks/task_${TS}"
mkdir -p "$TASK_DIR"
```

**잠금 메커니즘**: 작업 중 폴더는 plan/dev/eval 의 Write 발생 시 mtime 자연 갱신 → 120분 룰에 의해 자동 보호. 별도 .lock 파일 불필요.

---

## 9. 참조 레퍼런스 (자기 완결)

- 내부:
  - `.agent/context/SAMPLEAPP_BRAIN.md` ← 불변 SSOT
  - `.agent/context/SAMPLEAPP_STATE.md` ← 시점 SSOT
  - `CLAUDE.md` ← 프로젝트 메인 가이드
- 빌드:
  - `gradle/libs.versions.toml`
  - `app/build.gradle.kts`
- 외부 SSOT: **없음** (런처 자기 완결)
