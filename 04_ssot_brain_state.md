# 04. SSOT - BRAIN / STATE 분리

> 지식을 **저빈도(BRAIN)** vs **고빈도(STATE)** 로 명확히 나누고, 갱신 주체를 다르게 둔다.

---

## 왜 둘로 나누는가

**서로 다른 갱신 주기** 의 정보를 한 파일에 두면 다음 문제가 발생:

| 문제 | 사례 |
|---|---|
| diff 폭발 | "Phase 표 한 줄 갱신" 인데 git diff 가 BRAIN 의 200줄 같이 보임 |
| 자동 로드 비용 | STATE 가 자주 길어지는데 CLAUDE.md 처럼 자동 로드되면 매번 비싸짐 |
| 갱신 주체 혼동 | sync_brain 이 BRAIN 도 갱신? 혹은 plan_agent 가 STATE 도? |
| 마이그레이션 위험 | 키 인벤토리 (BRAIN) 가 Phase 진행 (STATE) 옆에 있으면 같이 쓰다 누락 |

따라서:

```
BRAIN.md   = 거의 영구. /sync_brain 이 신호 판별 → 컨펌 후 갱신 (별도 절차 아님).
STATE.md   = 매 task. /sync_brain 슬래시 1개로 일괄 갱신.
```

---

## BRAIN.md - 저빈도 SSOT

### 무엇을 두는가

| 섹션 | 내용 |
|---|---|
| **1. 제품 요약** | 분류 / 패키지명 / 모듈 구성 / UI 프레임워크 / 통신 언어 |
| **2. 모듈 디렉토리 트리** | 핵심 폴더 구조 (트리 형태). 디테일은 코드가 SSOT, 여기는 윤곽만 |
| **3. 핵심 클래스/엔드포인트 책임** | 각 클래스/라우트 한 줄 책임 - 이 표 보면 어느 파일 가야 할지 즉시 판단 |
| **4. SharedPreferences / DB 키 인벤토리** | 영구화 키 모음. 변경 시 사용자 데이터 손실 → 마이그레이션 의무 |
| **5. 빌드 / 의존성** | Java / Kotlin / AGP / Gradle / compileSdk / minSdk / 의존성 목록 |
| **6. 시스템 권한** | 시그너처 권한 / hidden API / fail-soft 의무 |
| **7. 시스템 진입점 (intent-filter / 라우트 표) | MAIN+LAUNCHER 또는 Next.js 라우트 표 |
| **8. 빌드 커맨드** | `./gradlew :app:installDebug` / `npm run build` 등 정형구 |
| **9. 분할 / Picker / 인증 등 영역별 비타협** | 매직 넘버 / 클램프 함수 / 자기 자신 필터 |
| **10. 참조 / 외부 의존** | 외부 SDK / 다른 repo / 외부 API URL |
| **11. (선택) 참조 분석 / 경쟁사** | 비교 대상의 reverse 분석 - 마케팅 / 기술 결정 근거 자료 |

### 무엇을 두지 않는가

- 현재 Phase 진행도 → STATE
- 최근 task 목록 → STATE
- 시점 git HEAD → STATE
- 일시적 진행 노트 → task 폴더

### 작성 톤

- **표 위주** - 사람이 빠르게 스캔 가능
- 산문은 각주 형태로 짧게 (예: `> ★ ... 2026-05-12 grep 재검증` 같은 출처/시점 메타)
- 마지막 갱신 시각 헤더 1줄 (`> **마지막 갱신**: YYYY-MM-DD`)

### 변경 절차

BRAIN.md 변경은 다음 경로로 일어난다:

1. **sync_brain (판별 → 컨펌 → 반영)** - 기본 경로. `last 갱신` 시점 이후 diff 를 신호 표(핵심 클래스/엔드포인트, 영구화 키 신규 추가, 의존성, 권한, 진입점, 비타협 항목)와 자동 대조 → 신호가 있으면 섹션별 diff 제시 → 사용자 컨펌 → 승인 시 그 자리에서 반영. 별도 task 로 미루지 않는다.
2. **plan_harness → dev_harness → eval_harness** - 하네스 메커니즘 자체(새 커맨드/서브에이전트/hook/비타협 표의 구조 변경)를 바꿀 때만.
3. **plan_agent_<project> (코드 마이그레이션 동반)** - 기존 영구화 키의 이름/타입 변경·삭제처럼 사용자 데이터 마이그레이션이 필요한 경우. plan.md 에 BRAIN 변경 영향 평가를 명시하고 dev 단계에서 코드와 함께 반영.

자유롭게 메인 세션이 손대지 않는다 - 어느 경로든 diff 제시 + 컨펌은 필수.

---

## STATE.md - 고빈도 SSOT

### 무엇을 두는가

| 섹션 | 내용 |
|---|---|
| **1. 현재 Phase 상태** | Phase 표 (`✅ / ⬜ / 🚧` 마크) + 한 줄 근거. 가장 자주 갱신되는 표 |
| **2. git 저장소** | 현재 브랜치 / 최근 commit 5~10개 / 원격 동기화 상태 |
| **3. 빌드 구성 (현 시점)** | versionCode / versionName / 시점값 (BRAIN 의 ranges 와 다름) |
| **4. 구현 화면 / 컴포넌트 목록** | 화면별 ✅/⬜ + 위치 (BRAIN 의 디렉토리 트리는 윤곽이지만 여기는 실제 구현 진행) |
| **5. 시스템 권한 환경 가정** | 현재 단말 환경 (시그너처 사인 / 일반 환경 등) |
| **6. 최근 task 요약** | task_<TS>_<slug>/ 의 plan.md 핵심 1~3줄 요약 + 결과 |
| **7. 메타** | STATE.md 자체의 마지막 sync_brain 시각 / 다음 검토 시점 |

### 자동 로드 여부

**자동 로드 안 함**. `/read_<project>` 슬래시 호출 시 명시 Read.

이유: STATE 가 자주 길어지고, 매 세션 전부 읽으면 비용. read 슬래시가 한 번 읽으면 그 세션 내내 컨텍스트.

### 작성 톤

- **표 + 시각** 우선
- "마지막 갱신: YYYY-MM-DD HH:mm KST" 헤더 1줄 (BRAIN 보다 빈번)
- 진행 표시는 `✅ / ⬜ / 🚧` 일관 사용
- 최근 task 의 한 줄 요약은 **plan.md 의 1줄 + result 의 1줄** 합쳐서 작성

### 갱신 절차

`/sync_brain` 슬래시 1개로 메인 세션이 직접 갱신.

`sync_brain.md` 슬래시는 일반적으로 다음을 수행:

1. 현재 git status / git log -10 출력
2. `.agent/tasks/task_*` 디렉토리 mtime 순 5개
3. 각 task 의 plan.md 첫 30줄 요약 + result 파일 헤더
4. STATE.md 의 Phase 표 / 화면 목록 / 최근 task 요약 갱신
5. BRAIN.md `last 갱신` 이후 diff 를 신호 표와 대조 → 신호 있으면 diff 제시 + 컨펌 → 승인 시 BRAIN.md 반영
6. "마지막 갱신" 시각 갱신 (STATE, 반영 시 BRAIN 도)

---

## 명명 규칙

| 파일 | 명명 |
|---|---|
| BRAIN | `<PROJECT>_BRAIN.md` - 예: `SAMPLEAPP_BRAIN.md`, `WEBAPP_BRAIN.md` |
| STATE | `<PROJECT>_STATE.md` - 예: `SAMPLEAPP_STATE.md`, `WEBAPP_STATE.md` |
| 위치 | `.agent/context/` |

대문자 PROJECT 명을 사용하는 이유: 파일명만으로 SSOT 임을 시각 구별.

---

## 폐기 자산 명단 - 이름 변경의 안전망

살아있는 하네스는 슬래시/에이전트 이름이 필연적으로 바뀐다. 낡은 문서 / auto-memory / 습관이 **옛 이름을 호출하는 사고** 를 막으려면, 개명·폐기 시 HARNESS_GUIDE.md 의 "폐기 자산" 표에 기록한다:

| 폐기 이름 | 대체 | 폐기 시점 | 사유 |
|---|---|---|---|

운영 규칙:

- 폐기된 이름으로 호출 요청이 오면 **실행하지 않고** 대체 이름을 안내한다.
- 표에 없는 미지의 이름은 신규 여부를 사용자에게 확인한다.

기록 주체: `/plan_agent_harness` task 의 일부로 기록한다 (dev_harness 가 HARNESS_GUIDE.md 갱신).

---

## Authority References - 복붙 금지 규칙

권위 문서 (BRAIN / STATE / HARNESS_GUIDE / CLAUDE.md) 의 내용을 커맨드 본문이나 다른 문서에 **복사하지 않는다** - 항상 "참조: <파일> §<섹션>" 포인터만 둔다.

- 이유: 복사본은 원본 갱신에서 누락돼 드리프트의 씨앗이 된다.
- 예외: 자동 로드되는 CLAUDE.md 의 표 요약 - 단, 원본이 BRAIN 임을 명시할 것.

---

## BRAIN 과 STATE 사이 모호한 정보 처리

### 예시 1 - "versionCode 9"

- BRAIN.md §5 빌드 의존성에는 **"versionCode: (현재 동적)"** 정도로 두고 시점값 명시 X
- STATE.md §3 빌드 구성에 **"versionCode=9 / versionName=0.1.9"** 시점값 명시

### 예시 2 - "Supabase 테이블 device_diagnostics 스키마"

- BRAIN.md §10 외부 의존에 **"device_diagnostics: fingerprint(PK) + app_version_code + build_info(jsonb) + ... 12 컬럼"** 영구 스키마
- STATE.md §6 최근 task 에 **"task_20260512_2038: TEST-DEVICE-01 row 삽입 PASS"** 시점값

### 판단 기준

- "**6개월 후에도 같은 값** 일 것인가?" → BRAIN
- "**다음 task** 면 바뀔 것인가?" → STATE

---

## /read_<project> 의 역할

세션 워밍업 슬래시. 다음을 수행:

```
1. Read .agent/context/<PROJECT>_BRAIN.md
2. Read .agent/context/<PROJECT>_STATE.md  (또는 §1~6 발췌)
3. find <code_root> -name "*.<lang>" 코드 인덱스
4. grep intent-filter / route 매핑
5. git log --oneline -5
6. ls -dt .agent/tasks/task_* | head -5
7. 표 형식으로 사용자에게 출력 (Phase / 구현 화면 / 키 인벤토리 / 인텐트 / 최근 task / 다음 권장 액션)
```

이게 첫 응답에 자동으로 떠야 새 세션이 즉시 컨텍스트를 가진다.

---

## 안티패턴

| 안티패턴 | 왜 나쁜가 |
|---|---|
| BRAIN 에 "이번 sprint 의 todo" 적기 | 시점값 → STATE 로 |
| STATE 에 "전체 키 인벤토리" 적기 | 영구값 → BRAIN 으로. STATE 가 부풀고 매번 sync_brain diff 커짐 |
| BRAIN/STATE 를 한 파일로 합치기 | 갱신 주체 혼동 + diff 폭발 |
| sync_brain 이 컨펌 없이 BRAIN 을 갱신 | 판별은 자동이어도 반영은 반드시 컨펌 후 - 무단 반영은 드리프트를 못 잡은 채 덮어씀 |
| read_<project> 가 STATE 만 읽음 | 컨텍스트 절반 누락 |

---

## 다음 단계

- `05_subagent_design.md` - 서브에이전트 권한 화이트리스트
- `06_ci_gate.md` - PostToolUse hook 작성법
