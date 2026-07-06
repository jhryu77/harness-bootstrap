# OVERVIEW - 한 페이지 전체 그림

> 이 파일 **하나만 봐도** 워크플로우 + 모든 문서 위치를 잡을 수 있다.
> 개별 깊이는 각 문서 링크로 진입.

---

## ⚡ 30초 요약

Claude Code 에 적용하는 **하네스 (안전망)** 패키지. 9가지 원칙으로 컨텍스트 망각 / 비타협 변경 / 셀프 PASS / 시크릿 누수를 막는다. 자기 프로젝트에 **30~60분** 만에 동등한 안전망 구축 가능.

⚠️ **하네스는 한 번 셋업 후 동결되는 결과물이 아니다.** Claude 의 반복 실수 + 사용자의 반복 작업 + 새 비타협 발견이 트리거가 되어 **코드와 공동 진화**한다. 메타 워크플로 (`/plan_agent_harness` 등) 가 그 진화를 안전하게 만든다.

---

## 🗺️ 전체 워크플로우 - 한 작업의 라이프사이클

```
사용자                          Claude 메인 세션                서브에이전트 (격리 권한)        외부 시스템
───────                         ──────────────                  ──────────────────────         ──────────

1. 세션 시작
   ──────────────────▶  ⓪ CLAUDE.md 자동 로드 ◀── (200줄 압축본)
                          (워크플로 표 + 비타협 항목 + 빌드 명령어 컨텍스트)

2. /read_<project>
   ──────────────────▶  Read BRAIN.md + STATE.md
                          + 코드 인덱스 + git log
                          → "현재 상태" 출력

3. /plan_agent_<project>
   ──────────────────▶  Agent(subagent_type=plan_<project>)
                          │
                          ├──────────────────────────▶  plan_<project> 진입
                          │                              │
                          │                              ├── archive (mtime+120 →archive/)
                          │                              ├── task_<TS>_<slug>/ 폴더 생성
                          │                              ├── plan.md  ← 변경 범위/영향평가/리스크
                          │                              └── tasklist.md  ← 체크박스
                          │                              [Write 권한: tasks/ 만]
                          │◀──────────────────────────  결과 보고
                          │
                          요약 출력
   ◀──────────────────  사용자 컨펌 게이트
                        (비타협 항목 ☑ 항목 컨펌)

4. /dev_<project>
   ──────────────────▶  plan.md 읽고 Edit/Write
                          │
                          ├── 매 Edit/Write 후
                          │   ┌─── PostToolUse hook ───┐
                          │   │  python ci_gate_*.py    │ → stderr 위반 시
                          │   │  - tmp_* 위치           │   Claude context 자동 주입
                          │   │  - 시크릿 패턴          │
                          │   │  - Kotlin 괄호 / TS 등  │
                          │   └─────────────────────────┘
                          │
                          tasklist 체크박스 진행
                          (MCP / Bash / Edit 풀권한)

5. /eval_agent_<project>
   ──────────────────▶  Agent(subagent_type=eval_<project>)
                          │
                          ├──────────────────────────▶  eval_<project> 진입
                          │                              │
                          │                              ├── tasklist 완료율
                          │                              ├── compile/typecheck Bash 실행
                          │                              ├── 비타협 회귀 점검 (grep)
                          │                              ├── 단말/외부 검증 (해당 시)  ────▶ adb / curl / MCP
                          │                              └── result YAML 텍스트 반환 (기록: 메인)
                          │                              [Write 권한: 없음]
                          │◀──────────────────────────  PASS / FAIL 보고
                          │
                          판정 출력
   ◀──────────────────  사용자 확정

6. /sync_brain
   ──────────────────▶  STATE.md §1 Phase / §3 빌드 / §6 task 갱신
                          BRAIN.md 갱신 신호 판별 → 있으면 diff 제시 + 컨펌 → 반영

7. /commit_push
   ──────────────────▶  자동 스테이징 필터
                          (*.keystore, .env, tasks/*.result, tmp/ 제외)
                          ──────────▶ git commit + push  ─────────────────────────▶ origin
                          (Co-Authored-By 정책 적용)

8. 120분 후 자동
                          ──────────▶ archive/  (다음 plan 진입 시)
```

**핵심 격리**:
- 메인 세션 = Edit/Write 풀권한
- plan_agent = Write 는 tasks/ 만 / Edit 없음
- eval_agent = Write 없음 + permissionMode: plan / result 는 텍스트 반환 (기록: 메인 세션)

---

## 🔀 워크플로 3종 + 1 (선택)

| 종 | 대상 | 슬래시 |
|---|---|---|
| **일반 코드** | `app/src/` / `src/` / 비즈니스 로직 | `/read_<p>` `/plan_agent_<p>` `/dev_<p>` `/eval_agent_<p>` |
| **하네스 자체** ★ | `.claude/` `.agent/` `CLAUDE.md` | `/plan_agent_harness` `/dev_harness` `/eval_agent_harness` |
| **배포 (선택)** | versionCode 증분 + Storage + DB 토글 + 단말 | `/plan_agent_<release>` `/dev_<release>` `/eval_agent_<release>` |
| **서버사이드 (선택)** | Supabase Edge Function / migration / API route | (`<server>` 슬래시 또는 별도 repo) |

상세 비교: [`03_workflow_patterns.md`](./03_workflow_patterns.md)

---

## 🛠️ 하네스 자체를 고도화하는 메타 워크플로 - 왜 별도로 존재하나

`/plan_agent_harness` → `/dev_harness` → `/eval_agent_harness` 는 **하네스 자기 자신을 변경하기 위한** 메타 워크플로다. 일반 코드 워크플로와 같은 plan/dev/eval 3단계 패턴이지만 **대상 / 권한 / 점검 항목** 이 완전히 다르다.

### 무엇을 다루나

- 새 슬래시 커맨드 추가 / 기존 삭제
- 서브에이전트 tools 화이트리스트 / Write 경로 권한 변경
- CI Gate 검사 항목 추가 (예: 새 시크릿 패턴 / 새 매직 넘버 회귀 검사)
- CLAUDE.md / HARNESS_GUIDE.md 갱신
- BRAIN.md 의 SharedPreferences / DB 키 인벤토리 마이그레이션 (코드 변경 동반 시)
- `.claude/settings.local.json` 의 권한 화이트리스트 변경
- archive 룰 / mtime 임계값 조정

### 왜 별도 워크플로인가 - 4가지 이유

#### 1. **영역 침범 차단** - 가장 큰 이유

한 task 가 "비즈니스 코드 + 하네스 메타 자산" 을 동시 손대면 plan 단계에서 점검할 항목이 폭증한다. 코드 비타협 + 하네스 무결성을 한 plan 에 다 채우면 한 페이지에 들어가지 않고, 사용자 컨펌 게이트 의미가 흐려진다.

분리해서:
- 일반 워크플로 → "이 코드 변경이 비타협 항목을 깨지 않나?"
- 하네스 워크플로 → "이 메타 변경이 기존 슬래시 / 서브에이전트 / hook 일치성을 깨지 않나?"

각자 자기 영역만 깊게 검토.

#### 2. **셀프 변경의 위험** - Claude 가 자기 안전망을 손대는 작업

하네스 변경은 본질적으로 **"Claude 가 자기 자신을 통제하는 장치를 수정"** 하는 행위다. 예:

- CI Gate hook 의 시크릿 패턴을 무심코 약화 → 다음부터 시크릿 누수 감지 못함
- plan 에이전트의 Write 권한을 풀어줌 → 서브에이전트 격리 깨짐
- archive 룰 mtime 을 0 분으로 변경 → 활성 task 폴더가 즉시 archive

이런 변경이 **무심코 일어나면 다음 작업부터 안전망이 침묵으로 사라진다**. 따라서 **dev_harness 전후 항상 eval_harness 가 무결성 회귀를 점검** 한다:

- frontmatter 정합성 (name/description/model/tools 4키 존재)
- settings.local.json JSON 파싱
- hook command 와 실제 스크립트 경로 일치
- CI Gate Python py_compile 통과
- archive/ 디렉토리 존재
- 기존 슬래시 워크플로 sanity

이 점검을 일반 eval 에 섞으면 **자기검증 신뢰성이 떨어진다** (일반 eval 의 코드 비타협 회귀 점검에 묻힘).

#### 3. **작업 흔적의 영구 보존**

"왜 슬래시가 12개나 되지?" "왜 plan_sampleapp 의 tools 에 Edit 가 빠졌지?" 같은 질문이 6개월 후 발생한다. 일반 코드 변경과 섞이면 git log 에서 찾기 어렵다.

`task_harness_<TS>_<slug>/` 라는 **별도 prefix** 로 폴더 명명 → 검색 / 인덱싱 즉시 가능. archive 후에도 `.agent/tasks/archive/task_harness_*` 로 구분 유지.

sampleapp 예시:
```
task_harness_20260504_2012_bootstrap/        ← 하네스 첫 부트스트랩
task_harness_20260512_2122_onboarding_kit/   ← onboarding 패키지 추출
task_harness_<...>_command_addition/         ← 새 슬래시 추가 (가상)
task_harness_<...>_ci_gate_secret_pattern/   ← CI Gate 정규식 추가 (가상)
```

각 task 폴더의 plan.md 가 "왜 그 변경을 했는가" 의 SSOT.

#### 4. **점검 도구가 다르다**

일반 eval = 컴파일 / 단위 테스트 / 비타협 grep / 단말 검증 / 외부 시스템 응답.

하네스 eval = JSON 파싱 / py_compile / frontmatter regex / hook 일치성 / 디렉토리 무결성.

같은 `eval_agent` 슬래시에 둘을 다 우겨넣으면 어느 한쪽이 부실해진다. 분리 = 각 영역에 적절한 점검 깊이.

### 언제 사용하나 - 신호 6가지

다음 중 하나라도 해당하면 일반 `/plan_agent_<project>` 대신 `/plan_agent_harness` 사용:

1. "이 슬래시 명령이 자주 필요한데 매번 손으로 같은 단계를 입력하고 있다" → 새 슬래시 추가
2. "서브에이전트가 Edit 권한을 못 받아서 본문에 우회 지시문이 길어진다" → tools 화이트리스트 조정
3. "최근 같은 종류의 사고가 두 번 났다 (예: 시크릿 누수 / 매직 넘버 변경)" → CI Gate 검사 추가
4. "BRAIN.md 의 키 인벤토리가 코드와 어긋났고, 기존 키 이름/타입 변경이라 마이그레이션이 필요하다" → 코드는 일반 워크플로, BRAIN 구조 변경 + 마이그레이션 절차는 하네스 (단순 신규 항목 반영은 `/sync_brain` 이 처리하므로 여기 해당 안 됨)
5. "비타협 항목 표가 8개 넘어서 인지 한계" → 카테고리 분할 / BRAIN.md 로 이동
6. "다른 개발자와 협업 / 다른 OS 환경 추가" → settings.local.json 권한 확장

### 일반 워크플로와 비교

| 항목 | 일반 코드 | 하네스 자체 |
|---|---|---|
| 슬래시 prefix | `/<verb>_agent_<project>` | `/<verb>_agent_harness` |
| task 폴더 prefix | `task_<TS>_<slug>/` | `task_harness_<TS>_<slug>/` |
| dev 범위 | `app/src/` / `src/` / `lib/` | `.claude/` `.agent/` `CLAUDE.md` |
| plan 영향 평가 | 비타협 항목 (런처 / 분할 / 인증) | 하네스 무결성 (hook / frontmatter / 권한 / archive) |
| eval 점검 도구 | 컴파일 / 단위 테스트 / 단말 / 외부 응답 | JSON 파싱 / py_compile / frontmatter regex / 디렉토리 |
| BRAIN / STATE 갱신 | STATE.md (Phase / 화면) + BRAIN.md 내용 동기화 (`/sync_brain` 판별→컨펌) | HARNESS_GUIDE.md / BRAIN.md 구조·마이그레이션 |
| 평균 소요 | 30분 ~ 수시간 | **10 ~ 30분** (작고 빠름) |

### 주의 - 코드 + 하네스 동시 변경이 필요한 경우

흔한 시나리오: 새 SharedPreferences 키를 추가하면서 BRAIN.md §4 키 인벤토리도 갱신해야 함. 두 가지로 갈린다:

**(A) 신규 키 추가 (기존 키 이름/타입은 그대로)** - BRAIN.md §4.3 정책상 마이그레이션 불필요. 하네스 task 자체가 필요 없다:

```
1. /plan_agent_<project> → /dev_<project> → /eval_agent_<project>  (코드에 새 키 사용)
2. /sync_brain  - 신규 키 신호 감지 → BRAIN.md §4 diff 제시 → 컨펌 → 반영
```

**(B) 기존 키의 이름/타입 변경·삭제** - 사용자 데이터 마이그레이션이 필요하므로 **한 task 로 묶지 않고** 두 task 를 순서대로:

```
1. /plan_agent_harness
   - BRAIN.md 키 인벤토리 갱신 + 마이그레이션 절차 plan
   - 사용자 컨펌 게이트
   - /dev_harness 로 BRAIN.md 갱신
   - /eval_agent_harness 로 무결성 확인

2. /plan_agent_<project>
   - 코드에 마이그레이션 로직 구현 plan
   - /dev_<project>
   - /eval_agent_<project>
```

**한 plan 에 코드 변경과 하네스 구조 변경을 함께 적지 않는다.**

### 상세

- [`03_workflow_patterns.md`](./03_workflow_patterns.md) §워크플로 2 - 하네스 자체
- [`05_subagent_design.md`](./05_subagent_design.md) §plan_harness / eval_harness frontmatter
- [`examples/sampleapp_snapshot/agents/plan_harness.md`](./examples/sampleapp_snapshot/agents/plan_harness.md) - sampleapp 예시의 plan_harness 본문
- [`examples/sampleapp_snapshot/agents/eval_harness.md`](./examples/sampleapp_snapshot/agents/eval_harness.md) - sampleapp 예시의 eval_harness 본문

---

## 🌱 살아있는 하네스 - 진화 메커니즘 (가장 중요한 개념)

**하네스는 한 번 부트스트랩하면 끝나는 결과물이 아니다.** 개발 코드와 마찬가지로 **공동 진화** 한다. BOOTSTRAP_PROMPT 7단계는 출발점일 뿐, **진짜 가치는 그 이후 수개월 동안 누적되는 진화** 에서 나온다.

### 왜 진화하는가

Claude 의 학습이 매 세션 리셋되는 한계 때문이다. 사람 개발자라면 "이런 사고 두 번째네, 다음부터 조심해야지" 로 기억에 박히지만, Claude 는 **다음 세션에 같은 사고를 한다**. 따라서 그 학습을 **하네스 자산에 영구 기록** 해야 누적된다:

- "임시 파일을 루트에 만들면 안 되는 걸 깨달았다" → CI Gate 검사 추가 (영구)
- "비타협 항목 X 를 잊지 말아야 한다" → CLAUDE.md 비타협 표 추가 (자동 로드)
- "같은 워밍업 단계를 매번 입력하고 있다" → 슬래시 커맨드 추가 (1회 호출로 자동)

**하네스 진화 ≒ Claude 의 "장기 기억" 외부화**.

### 진화 트리거 4종

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│   트리거                                  →  진화 액션            │
│   ─────                                     ─────────             │
│                                                                  │
│   1. Claude 의 반복 실수                  →  CI Gate 검사 추가    │
│      (같은 사고 2회 이상)                    + CLAUDE.md 비타협 표 │
│                                                                  │
│   2. 사용자의 반복 작업                   →  새 슬래시 커맨드     │
│      (같은 명령 3회 이상 입력)               (`/<verb>_<obj>`)    │
│                                                                  │
│   3. 컨텍스트 휘발                        →  BRAIN/STATE 갱신     │
│      (매 세션 같은 정보 재구축)              또는 CLAUDE.md 보강  │
│                                                                  │
│   4. 새 비타협 발견                       →  BRAIN §비타협 + plan │
│      ("아 이거 변경하면 망함" 사후 인지)     체크리스트 추가      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                  /plan_agent_harness  (10~30분)
                              │
                              ▼
                  하네스 진화 1회 완료
                  (task_harness_<TS>_/ 폴더에 기록)
```

### 진화 곡선 예시 - sampleapp

```
주차    │ 슬래시 │ CI Gate │ 서브에이전트 │ BRAIN.md │ Phase
────────┼────────┼─────────┼──────────────┼──────────┼──────────────────
week 0  │   5    │    1    │      2       │   30줄   │ 부트스트랩
week 3  │   7    │    2    │      2       │   80줄   │ Phase 3.5 (임베드)
week 5  │  10    │    3    │      4       │  200줄   │ Phase L (라이선스)
week 8  │  13    │    3    │      6       │  300줄   │ Phase O10 (크래시)
week 10 │  13    │    3    │      6       │  367줄   │ Phase Z (진단)
```

10주 동안 슬래시 5→13 / 서브에이전트 2→6 / BRAIN 30→367줄. **하네스 자체가 30+ 회 진화** 했고, 매 진화가 `task_harness_<TS>_/` 폴더에 기록되어 6개월 후에도 "왜 이 슬래시가 추가됐나" 즉시 검색 가능.

### 진화 시점 - 두 가지 황금률

**황금률 1**: **같은 사고 2번째에 즉시 메타 변경**.

"3번째 사고 나면 진짜 정리해야지" 는 **4번째 사고를 예약**한다. 일반 작업 중 트리거 발견 → 그 task 끝나면 즉시 `/plan_agent_harness` → 10~30분 → 다음 작업부터 그 사고 영구 차단.

**황금률 2**: **건강한 진화 빈도 = 2~4주에 1회**.

- 너무 빈번 (주 2회 이상): 하네스 자체가 불안정. 기존 워크플로가 깨질 수 있음
- 너무 드물 (3개월 이상 변경 없음): 진화 부채 누적. Claude 가 같은 실수를 반복하는데도 메타가 따라가지 못함

`ls -dt .agent/tasks/task_harness_* | head -3` 으로 최근 메타 task 시점 확인. 마지막 진화가 3개월 전이면 점검 시점.

### 자기 안전 - 메타 워크플로가 진화를 안전하게 만든다

진화 자체가 위험하다. CI Gate 패턴을 무심코 약화하면 다음부터 시크릿 감지 못함. archive mtime 을 0 으로 만들면 활성 task 가 즉시 사라짐.

그래서 `/plan_agent_harness` 가 진화 의도 명시 + `/eval_agent_harness` 가 무결성 회귀 자동 점검:

- frontmatter 4키 정합성
- JSON 파싱
- hook command ↔ 실제 스크립트 일치
- archive 디렉토리 존재
- 기존 슬래시 sanity

이 안전망 덕분에 **진화가 빠르고 부담 없음**. 사람이 "오늘 새 슬래시 추가하기 부담스럽네" 로 미루지 않는다.

### "완성" 의 함정 ⚠️

"우리 하네스 완성됐다" 는 표현은 **두 가지 위험 신호** 중 하나:

1. **프로젝트 자체가 정지** (개발이 안 일어남)
2. **진화 부채 누적** (코드는 변하는데 하네스가 따라가지 못함 = Claude 가 같은 실수 반복)

하네스가 진짜 살아있다면 `task_harness_*` 폴더가 **꾸준히** 생긴다. 마지막 메타 task 가 6개월 전이라면 점검 필요.

### 적용 - 첫 부트스트랩 후 4주

BOOTSTRAP_PROMPT 7단계로 부트스트랩 완료 후 첫 4주는 **진화 트리거 관찰 기간**. 다음 신호들을 잡으면 즉시 `/plan_agent_harness`:

- [ ] Claude 가 같은 종류 코드 변경을 2번 무심코 했다 → CI Gate 검사 후보
- [ ] 같은 단계 (예: "BRAIN 읽고 git log 확인하고 task 폴더 보고") 를 3번째 손으로 입력한다 → 새 슬래시 후보
- [ ] 새 세션 워밍업에 5분 이상 걸린다 → BRAIN/STATE 보강 후보
- [ ] "어 이거 못 만지는 건데?" 사후 인지 1건 → 새 비타협 항목 후보
- [ ] 다른 환경 (Mac↔Windows / 다른 협업자) 추가 → settings.local.json 권한 확장
- [ ] 새 외부 의존 (Sentry / Upstash 등) 추가 → BRAIN §10 갱신

상세: [`01_philosophy.md`](./01_philosophy.md) §원칙 9 - 하네스는 살아있다

---

## 📂 모든 문서 인덱스 (67 파일)

### 진입점 (5개)

| 문서 | 1줄 요약 |
|---|---|
| [`README.md`](./README.md) | 사람 개발자 진입점. 2가지 사용 시나리오 안내 |
| (이 파일) [`OVERVIEW.md`](./OVERVIEW.md) ★ | **한 페이지 전체 그림 + 워크플로 다이어그램 + 문서 인덱스** |
| [`BOOTSTRAP_PROMPT.md`](./BOOTSTRAP_PROMPT.md) ★ | **Claude 에게 던지는 7단계 자동 부트스트랩 프롬프트** |
| [`CHANGELOG.md`](./CHANGELOG.md) | 버전 이력 + 향후 개선 후보 |
| [`UPGRADE.md`](./UPGRADE.md) | 킷 업데이트 절차 + 네임스페이스 소유권 규약 + 버전별 마이그레이션 노트 |

### 핵심 원칙 9개 문서 (필요 깊이만큼)

| 문서 | 무엇을 다루나 | 누가 읽을까 |
|---|---|---|
| [`01_philosophy.md`](./01_philosophy.md) | **9가지 핵심 원칙** + 안티패턴 | 모두 (5분) |
| [`02_architecture.md`](./02_architecture.md) | `.claude/` `.agent/` `CLAUDE.md` 자산 구조 + 데이터 흐름 + mono/multi repo | 적용 전 모두 |
| [`03_workflow_patterns.md`](./03_workflow_patterns.md) | **4종 워크플로 비교표** + 흐름 다이어그램 | 모두 |
| [`04_ssot_brain_state.md`](./04_ssot_brain_state.md) | BRAIN(저빈도) vs STATE(고빈도) 분리 + 작성 가이드 | 직접 적용자 |
| [`05_subagent_design.md`](./05_subagent_design.md) | 서브에이전트 frontmatter + tools 화이트리스트 | 직접 적용자 |
| [`06_ci_gate.md`](./06_ci_gate.md) | PostToolUse hook + Python 스크립트 표준 골격 | 직접 적용자 |
| [`07_task_lifecycle.md`](./07_task_lifecycle.md) | task_<TS>_<slug>/ + 120분 archive 자동화 | 운영자 |
| [`08_immutables.md`](./08_immutables.md) | 비타협 항목 카테고리 6종 + plan 자동 체크리스트 | 정책 결정자 |
| [`09_adapt_checklist.md`](./09_adapt_checklist.md) | **사람 개발자 직접 적용 8단계** + FAQ | 수동 적용자 |

### 템플릿 28개 - 플레이스홀더 치환해서 사용 (statusline.py / scripts/ 는 치환 불필요, 설정 예시는 {{PROJECT}} 치환 필요)

| 디렉토리 | 파일 | 역할 |
|---|---|---|
| [`templates/`](./templates/) (루트) | `CLAUDE.md.template` | 자동 로드 압축본 (200줄 이하 권장) |
| | `BRAIN.md.template` | 저빈도 SSOT - 패키지/디렉토리/키 인벤토리/비타협 |
| | `STATE.md.template` | 고빈도 SSOT - Phase 표/git/최근 task |
| | `HARNESS_GUIDE.md.template` | 운영 매뉴얼 |
| | `settings.local.json.template` | Claude Code 권한 + PostToolUse hook |
| | `ci_gate.py.template` | 표준 검사 3종 + 언어별 확장 |
| | `statusline.py` | (선택) 전역 상태바 - CW/5H/7D 사용률 + reset 카운트다운. 치환 불필요, `~/.claude/` 복사 |
| | `settings.pretooluse.json.example` | (선택) PreToolUse hook opt-in 등록 예시 - pre_gate.py 활성화용 |
| [`templates/scripts/`](./templates/scripts/) | `archive_tasks.py` | (선택 자산) status 기준 task 아카이브 - dry-run 기본, `--apply` 시 이동 |
| | `harness_doctor.py` | (선택 자산) 설치 무결성 진단 - frontmatter/hook/드리프트 점검 |
| | `harness_manifest.py` | (선택 자산) 배포 파일 해시 manifest 생성 - 킷 업데이트 대조용 |
| | `pre_gate.py` | (선택 자산) PreToolUse 커밋 게이트 + 위험 명령 차단 - **opt-in** |
| | `stop_gate.py` | (선택 자산) Stop 훅 advisory - 턴 종료 시 git 변경 파일 광역 검사, systemMessage 경고만 - **opt-in** |
| | `model_policy.py` | (선택 자산) 에이전트별 model 정책 적용/조회 (`set <tier>` / `show`) |
| | `glm_mode.py` | (선택 자산) GLM(z.ai) 병행 - **실험적/opt-in**, tmux 새 창에 GLM 라우팅 Claude Code 수동 실행 |
| [`templates/commands/`](./templates/commands/) | `read_PROJECT.md.template` | 세션 워밍업 슬래시 |
| | `plan_agent_PROJECT.md.template` | plan 서브에이전트 호출 |
| | `dev_PROJECT.md.template` | 메인 세션 dev 가이드 + 비타협 점검 |
| | `eval_agent_PROJECT.md.template` | eval 서브에이전트 호출 |
| | `sync_brain.md.template` | STATE 갱신 |
| | `commit_push.md.template` | git 자동화 (스테이징 필터 + 메시지 type) |
| | `plan_agent_harness.md.template` | 하네스 자체 변경 plan |
| | `dev_harness.md.template` | 하네스 편집 가이드 |
| | `eval_agent_harness.md.template` | 하네스 무결성 평가 호출 |
| [`templates/agents/`](./templates/agents/) | `plan_PROJECT.md.template` | plan 서브에이전트 frontmatter + 본문 |
| | `eval_PROJECT.md.template` | eval 서브에이전트 (Write 없음) |
| | `plan_harness.md.template` | 하네스 plan 서브에이전트 |
| | `eval_harness.md.template` | 하네스 무결성 점검 서브에이전트 |

### 예시 25개

| 디렉토리/파일 | 무엇 |
|---|---|
| [`examples/sampleapp_snapshot/`](./examples/sampleapp_snapshot/) (23 파일) | sampleapp_launcher (Android 차량 런처) **하네스 풀 구성 예시** |
| └ `CLAUDE.md` | 172줄 - 실제 자동 로드 가이드 |
| └ `HARNESS_GUIDE.md` | 200줄 - 실제 운영 매뉴얼 |
| └ `settings.local.json` | 48개 권한 화이트리스트 + hook (절대경로 → 플레이스홀더 치환) |
| └ `ci_gate_sampleapp.py` | 144줄 - Kotlin 괄호 검사 포함 |
| └ `commands/` (13 파일) | read / plan / dev / eval (×sampleapp/harness/ota_release) + sync_brain / commit_push / test_sampleapp |
| └ `agents/` (6 파일) | plan/eval × (sampleapp/harness/ota_release) |
| [`examples/sampleapp_server_inventory/INVENTORY.md`](./examples/sampleapp_server_inventory/INVENTORY.md) | **raw Next.js 프로젝트 인벤토리** - 하네스 적용 전 상태 실례 |
| [`examples/case_study.md`](./examples/case_study.md) ★ | **두 사례 비교 종단 시나리오** - sampleapp_launcher Phase Z 의 10단계 흐름 + sampleapp_server 적용 가이드 |

---

## 🎯 시나리오별 권장 진입점

| "나는 ..." | 추천 경로 |
|---|---|
| 우리 하네스가 뭐 하는 건지 5분 안에 알고 싶다 | [`01_philosophy.md`](./01_philosophy.md) |
| 내 프로젝트에 자동으로 적용하고 싶다 | [`BOOTSTRAP_PROMPT.md`](./BOOTSTRAP_PROMPT.md) - Claude 에게 던지기 |
| 내 손으로 직접 설정하고 싶다 | [`09_adapt_checklist.md`](./09_adapt_checklist.md) → templates/ 치환 |
| 적용 예시를 먼저 보고 싶다 | [`examples/case_study.md`](./examples/case_study.md) |
| Android / Kotlin 프로젝트 적용 | [`examples/sampleapp_snapshot/`](./examples/sampleapp_snapshot/) 참고 |
| Next.js / TypeScript / Supabase 적용 | [`examples/sampleapp_server_inventory/INVENTORY.md`](./examples/sampleapp_server_inventory/INVENTORY.md) |
| 워크플로 표만 빠르게 보고 싶다 | [`03_workflow_patterns.md`](./03_workflow_patterns.md) |
| 권한 격리 (서브에이전트 frontmatter) 가 궁금 | [`05_subagent_design.md`](./05_subagent_design.md) |
| CI Gate 의 Python 스크립트 작성법 | [`06_ci_gate.md`](./06_ci_gate.md) |
| 비타협 항목 어떻게 추출하나 | [`08_immutables.md`](./08_immutables.md) |
| 다른 repo 와 인터페이스 어떻게 관리 | [`02_architecture.md`](./02_architecture.md) §Mono-repo vs Multi-repo |
| 새 슬래시 / 서브에이전트 추가 절차 | [`02_architecture.md`](./02_architecture.md) §슬래시 매핑 + [`05_subagent_design.md`](./05_subagent_design.md) |

---

## ⚙️ 9가지 핵심 원칙 (한 줄 요약)

상세: [`01_philosophy.md`](./01_philosophy.md)

| # | 원칙 | 한 줄 |
|---|---|---|
| 1 | **SSOT 분리** | BRAIN(저빈도) vs STATE(고빈도) - 갱신 주체 다름 |
| 2 | **3단계 워크플로** | plan → dev → eval, 각 단계 다른 서브에이전트 |
| 3 | **task 격리** | task_<TS>_<slug>/ 폴더에 plan/tasklist/result 영구 기록 |
| 4 | **서브에이전트 최소 권한** | plan = tasks/ 만 Write / eval = Write 없음 |
| 5 | **CI Gate hook** | 매 Edit/Write 시 Python 스크립트 자동 실행 |
| 6 | **CLAUDE.md 자동 로드** | 200줄 이하 표 위주 압축본 |
| 7 | **3종 워크플로 분리** | 코드 / 하네스 / 배포 영역 침범 차단 |
| 8 | **언어/커밋 정책 명시** | 응답 언어 / Co-Authored-By / 커밋 type 어휘 |
| 9 | **살아있는 하네스** ★ | 한 번 셋업으로 끝 아님. 실수/반복작업이 트리거가 되어 코드와 공동 진화 |

---

## 🚀 빠른 적용 (TL;DR)

자기 프로젝트 루트에서 Claude Code 띄운 후:

```
"harness_bootstrap/BOOTSTRAP_PROMPT.md 를 읽고 거기 7단계 절차에 따라
 이 프로젝트에 하네스를 구축해줘."
```

Claude 가 다음을 수행:

1. 프로젝트 분석 (`find` `git log` `package.json`)
2. 비타협 항목 추출 (사용자 컨펌)
3. BRAIN.md / STATE.md 초안
4. 슬래시 + 서브에이전트 생성
5. CI Gate Python 스크립트
6. CLAUDE.md 작성
7. 첫 task 로 무결성 검증

각 단계마다 사용자 컨펌 게이트가 있어 중간 수정 가능.

---

## 🏗️ 아키텍처 3 자산 (필요한 모든 파일)

```
<your_project_root>/
├── CLAUDE.md                   ① 자동 로드 (~200줄 압축)
├── .claude/                    ② Claude Code 설정
│   ├── settings.local.json     권한 + PostToolUse hook
│   ├── commands/               슬래시 *.md (~10개)
│   └── agents/                 서브에이전트 *.md (~4개)
└── .agent/                     ③ 우리 자체 컨텍스트
    ├── HARNESS_GUIDE.md        운영 매뉴얼
    ├── context/
    │   ├── <P>_BRAIN.md        저빈도 SSOT
    │   └── <P>_STATE.md        고빈도 SSOT
    ├── scripts/
    │   └── ci_gate_<p>.py      PostToolUse 정적 검증
    └── tasks/
        ├── task_<TS>_<slug>/   활성 task
        └── archive/      120분 자동 이동
```

상세: [`02_architecture.md`](./02_architecture.md)

---

## 🔍 검증 사례 (examples/)

- **sampleapp_launcher** (Android 차량용 런처) - OTA 배포 / 크래시 보고 / 진단 수집까지 포함한 풀 스택 구성 예시
- **sampleapp_server** (Next.js admin webapp, sibling repo) - 하네스 적용 전(raw) 인벤토리 예시

같은 골격이 **Kotlin/Gradle** (launcher) 와 **TypeScript/Next.js/Supabase** (server) 두 스택에 동일 적용 가능함을 보여주는 case study: [`examples/case_study.md`](./examples/case_study.md)

---

## ❓ FAQ 빠른 답변

| Q | A | 상세 |
|---|---|---|
| 기존 코드 변경 안 하나요? | 안 함. 하네스만 추가, 코드는 무손 | [`BOOTSTRAP_PROMPT.md`](./BOOTSTRAP_PROMPT.md) §주의 |
| 작은 프로젝트도 필요? | 3단계 워크플로는 큰 작업에 가치. 1인 사이드 프로젝트도 SSOT + CI Gate 만 적용 가능 | [`09_adapt_checklist.md`](./09_adapt_checklist.md) |
| Claude 가 풀권한이면 안 되나? | 셀프 PASS 가능 + 비타협 무심코 변경. 서브에이전트 격리가 핵심 | [`05_subagent_design.md`](./05_subagent_design.md) §안티패턴 |
| CLAUDE.md 가 길어지면? | BRAIN/HARNESS_GUIDE 로 옮김. CLAUDE.md 는 표 위주 200줄 이하 | [`04_ssot_brain_state.md`](./04_ssot_brain_state.md) §명명 규칙 |
| 새 슬래시 추가 절차? | `/plan_agent_harness` 진입 → 새 .md 작성 → eval | [`02_architecture.md`](./02_architecture.md) §슬래시 매핑 |
| GLM 같은 외부 모델을 병행하고 싶다 | glm_mode.py 참조 (실험적, tmux+GLM 계정 필요) | 06_ci_gate.md §GLM 병행 |

---

## 📦 LOC / 파일 통계

- 총 **67 파일** / 약 10,400 LOC
- 진입점 5 (UPGRADE 포함) / 핵심 문서 9 / 템플릿 28 (선택 스크립트 7종 + statusline.py + 설정 예시 1 포함) / 예시 25
- 시크릿 / 절대 경로 / 개인·조직 식별자 미포함 (전수 검증 완료 - 프로젝트명·패키지·URL·단말 식별자 포함)

---

## 끝

질문이 남으면 → 해당 주제 문서의 **링크 클릭**.
직접 적용하려면 → [`BOOTSTRAP_PROMPT.md`](./BOOTSTRAP_PROMPT.md) (자동) 또는 [`09_adapt_checklist.md`](./09_adapt_checklist.md) (수동).
