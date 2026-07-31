# 08. 비타협 항목 (Immutables)

> "Claude 가 무심코 건드리면 안 되는 항목" 을 **CLAUDE.md + BRAIN.md** 에 명시하여, plan 단계에서 영향 평가가 자동으로 일어나게 한다.

---

## 비타협 항목 이란

다음 셋 중 하나라도 해당하면 비타협 항목 후보다:

1. **변경 시 사용자 데이터 손실 가능** - 영구화 키 / DB 스키마 / 파일 포맷
2. **변경 시 제품 정체성 파괴** - 런처면 intent-filter / SDK면 public API / 서비스면 인증 플로우
3. **변경 시 외부 의존성 깨짐** - 시그너처 권한 / OAuth scope / DB RLS 정책

이 셋 중 하나에 해당하는 항목은 **변경 전에 사용자 컨펌 필수** 로 못박는다.

---

## 어디에 적는가

### CLAUDE.md (자동 로드)

자동 로드되어 **매 세션 처음부터** Claude 컨텍스트에 들어간다. 따라서 다음만 둔다:

- 비타협 항목의 **표 형식 요약** (한 줄씩)
- 변경 시 사용자 컨펌 의무 명시

### BRAIN.md (명시 Read)

상세 근거 + 매직 넘버 + 예외 케이스 + 변경 시 마이그레이션 절차.

CLAUDE.md 가 가벼운 인지용, BRAIN.md 가 무거운 참조용. plan 에이전트는 BRAIN.md 도 자동 Read 하므로 영향 평가 시 상세 표 확인 가능.

---

## 비타협 항목 카테고리

### A. 시스템 진입점 / 인터페이스

- **런처 프로젝트**: `<intent-filter>` 의 4개 카테고리 (MAIN + HOME + DEFAULT + LAUNCHER)
- **API 서버**: 공개 엔드포인트 URL + HTTP method
- **SDK / 라이브러리**: public API 시그너처
- **CLI 도구**: 명령어 이름 + 핵심 옵션

### B. 영구화 키 / 데이터 포맷

- SharedPreferences 파일명 + 키명
- DB 테이블명 + 컬럼명
- 파일 포맷 magic byte
- 캐시 디렉토리 구조

### C. 빌드 / 사인 / 런타임

- packageName / applicationId / namespace
- 시그너처 권한 화이트리스트
- sharedUserId (있다면)
- minSdk / targetSdk

### D. 상수 / 클램프 / 매직 넘버

- 범위 상수 (예: `PAGE_SIZE`, `MAX_PAGE_SIZE`)
- 클램프 함수 (`coerceIn`)
- 그리드 컬럼 수 (예: 리스트 column = 2, sw600dp 는 3)
- 매직 넘버 (예: `OTA_CHECK_TIMEOUT_MS = 10_000`)

### E. 보안 / 인증

- RBAC role 정의
- OAuth scope 집합
- Supabase RLS 정책
- 세션 만료 정책

### F. 디렉토리 / 배치 규칙

- "코드 루트 직접 `.kt` 금지" 같은 위치 규칙
- "임시 파일은 `tmp/` 만" - CI Gate 도 동일 규칙 적용
- "서브에이전트 산출물은 `tasks/` 하위만"

---

## CLAUDE.md 비타협 표 골격

```markdown
## 6. 앱 비타협 항목

| ID | 항목 | ZONE | 비고 |
|---|---|---|---|
| A1 | `<intent-filter>` 의 MAIN+LAUNCHER | Frozen | 변경 = 사용자 컨펌 |
| C1 | `packageName` / `applicationId` | Frozen | 변경 = 사용자 컨펌 |
| B1 | Room `@Database(version)` 증분 시 Migration 동반 | Frozen | 누락 = 데이터 손실 |
| ... | ... | ... | ... |

## 7. 저장 / 상수 비타협 항목

| ID | 항목 | ZONE | 비고 |
|---|---|---|---|
| D1 | `PAGE_SIZE 20 / MAX_PAGE_SIZE 100` 상수 | Frozen | 동시 변경 금지 |
| D2 | 페이지 적용 시 `coerceIn(1, MAX_PAGE_SIZE)` 호출 | Frozen | 클램프 누락 = FAIL |
| D3 | 리스트 그리드 column = 2 | Evolvable | 근거 명시 시 일반 task 경로에서 조정 가능 |
| ... | ... | ... | ... |
```

**ID 는 영구불변이다.** 첫 열은 순번(`#`)이 아니라 **카테고리 문자 + 번호**(A1/B1/C1/D1/E1/F1 — 위 A~F 카테고리에 대응)로 **영구 ID** 를 준다. 다른 문서가 `비타협 D2` 처럼 ID 로 참조하므로, **행이 늘거나 순서가 바뀌어도 ID 는 그대로 둔다.** 폐기된 항목의 ID 는 **재사용하지 않고 비워둔다**(참조 오염 방지). 새 항목은 **새 ID** 를 주고 기존 ID 를 재배치하지 않는다.

> **순번(1·2·3…)으로 참조하지 말 것.** 순번은 행이 늘 때마다 썩는다. 마찬가지로 **표에 행 수를 하드코딩하지 말 것**("(7행)" 식) - 항목이 늘면 어긋난다.

**표당 8개 이하** 가 인지 가능한 상한. 더 많으면 카테고리별로 표를 분할한다 (ID 의 카테고리 문자는 표를 나눠도 그대로 유지 - 참조가 안 깨진다).

각 항목은 **1줄 명확**. 산문 설명은 BRAIN.md 로 보냄.

### ZONE 태깅 가이드

- `Frozen` - 변경하려면 `/plan_agent_harness` 진입 + 사용자 컨펌 필수. 진입점 / 영구화 키 / 사인 / 보안 카테고리 (A·B·C·E) 가 대부분 해당.
- `Evolvable` - `/sync_brain` 또는 일반 task 경로에서 갱신 허용. 표시값 / 문서 포인터 등.
- 강제 수준 태그: 규칙 산문에는 `[HARD]` (위반 = FAIL) / `[SHOULD]` (권고) 를 인라인으로 쓸 수 있다 - CLAUDE.md 200줄 상한 내에서 표가 우선.

---

## BRAIN.md 비타협 상세 골격

```markdown
## 9. 저장 / 상수 비타협 항목 (상세)

| 영역 | 규칙 | 매직 넘버 | 변경 시 마이그레이션 |
|---|---|---|---|
| 페이지네이션 상수 | PAGE_SIZE/MAX_PAGE_SIZE 동시 변경 금지 | 20 / 100 | (자동) 기존 값 coerceIn 시 새 범위 적용 - 기능 안전 |
| 클램프 호출 | coerceIn 누락 시 과도 로드 | - | 코드 검색 (`coerceIn(1, MAX_PAGE_SIZE`) |
| Room 스키마 | @Database(version) 증분 시 Migration 동반 | - | Migration 누락 = 데이터 손실 |
| 리스트 그리드 | GridLayoutManager column = 2 | 2 | 변경 시 dev_sampleapp.md 에 근거 명시 |
| ... | ... | ... | ... |
```

마이그레이션 절차도 함께 적어두면 향후 plan 시 즉시 활용.

---

## plan_agent 의 영향 평가 체크리스트

`plan_<project>` 서브에이전트가 plan.md 작성 시 자동 포함하는 섹션:

```markdown
## 앱 진입 영향 평가 체크리스트

- [ ] MAIN / LAUNCHER 인텐트 필터 변경 여부
- [ ] packageName / applicationId 변경 여부
- [ ] INTERNET 권한(OTA) 제거 여부
- [ ] FileProvider authority 변경 여부
- [ ] 릴리스 시그너처 config 추가/제거 여부

**사용자 컨펌 필요 항목**: 위 체크리스트에서 ☑ 된 항목 나열

## 저장 / 상수 일관성 체크리스트

- [ ] Room entity(items) 컬럼 변경 여부
- [ ] @Database(version) 증분 시 Migration 동반 여부
- [ ] SortOrder enum 추가/순서·storageKey 변경 여부
- [ ] PAGE_SIZE / MAX_PAGE_SIZE / OTA_CHECK_TIMEOUT_MS 상수 변경 여부
- [ ] SharedPreferences 파일명("settings"/"sync_state")·키명 변경 여부

**리스크**: 위 체크리스트에서 ☑ 된 항목 있으면 마이그레이션 절차 명시
```

이 체크리스트가 plan.md 의 첫 1~2 페이지에 자동 포함되어, 사용자가 plan 검토 시 한눈에 확인 가능.

---

## 새 비타협 항목 추가 절차

새 항목 발견 시 (예: "TestActivity 의 onCreate 에 super.onCreate 호출 누락 시 크래시"):

1. `/plan_agent_harness` 진입
2. plan.md 에 "CLAUDE.md / BRAIN.md / plan_<project>.md 본문 갱신" 명시
3. `/dev_harness` 로 세 파일 갱신:
   - CLAUDE.md 의 비타협 표에 1줄 추가
   - BRAIN.md 의 상세 표 추가 + 마이그레이션 절차
   - plan_<project>.md 본문의 체크리스트 섹션에 한 줄 추가
4. `/eval_agent_harness` 로 무결성 확인
5. 다음 plan 부터 자동 적용

---

## 변경 후 검증

비타협 항목 변경이 PASS 되려면 다음을 만족:

| 항목 | 확인 |
|---|---|
| plan.md 에 영향 평가 ☑ 있음 | 명시 |
| 사용자 컨펌 받음 | plan.md "사용자 컨펌 필요 항목" 섹션 |
| 마이그레이션 절차 plan.md 에 명시 | (변경 항목 종류에 따라) |
| eval 단계에서 회귀 점검 통과 | CI Gate + 단말 검증 |
| BRAIN.md / CLAUDE.md 갱신 함께 진행 | sync_brain |

---

## 예시 - sampleapp 의 비타협 항목 (참조)

### CLAUDE.md §6 (앱 진입)

| ID | 항목 | ZONE |
|---|---|---|
| A1 | `<intent-filter>` 의 MAIN+LAUNCHER | Frozen |
| C1 | `packageName` / `applicationId` = com.sampleapp.app | Frozen |
| B1 | Room `@Database(version)` 증분 시 Migration 동반 | Frozen |
| B2 | Room entity 테이블/컬럼명 (`items`) | Frozen |
| C2 | 릴리스 시그너처 config | Frozen |
| C3 | `INTERNET` 권한 (OTA) | Frozen |
| A2 | `FileProvider` authority | Frozen |
| E1 | `DetailFragment.exported="false"` | Frozen |

### CLAUDE.md §7 (저장 / 상수)

| ID | 항목 | ZONE |
|---|---|---|
| D1 | `PAGE_SIZE 20 / MAX_PAGE_SIZE 100` 상수 | Frozen |
| D2 | 페이지 적용 시 `coerceIn(1, MAX_PAGE_SIZE)` 호출 | Frozen |
| D3 | `SYNC_INTERVAL_MIN 15 / MAX 1440` (분) clamp | Frozen |
| B3 | SharedPreferences 파일 분리 (`settings` ↔ `sync_state`) | Frozen |
| B4 | `SortOrder` enum 순서 / `storageKey` 변경 금지 | Frozen |
| D4 | 리스트 그리드 column = 2 | Frozen |
| D5 | SwipeThreshold 96dp / RippleRadius 24dp 분리 | Frozen |
| D6 | `OTA_CHECK_TIMEOUT_MS = 10_000` | Frozen |

8개씩 - 한 화면에 인지 가능한 한계.

> 참고: 위 골격 예시(§CLAUDE.md 비타협 표 골격)에서는 리스트 column 을 Evolvable 판단의 **예시**로 태깅했지만, sampleapp 예시는 보수적으로 Frozen 으로 운영한다. ZONE 판정은 프로젝트가 감당할 회귀 리스크에 따라 달라진다 - 확신이 없으면 Frozen 이 안전 기본값.

---

## 안티패턴

| 안티패턴 | 왜 나쁜가 |
|---|---|
| 비타협 항목을 코드 주석 한 줄로만 표시 | plan 시점 검색 안 됨. CLAUDE.md / BRAIN.md 에 명시 |
| CLAUDE.md 에 비타협 항목을 산문으로 적기 | 표가 아니면 plan 에이전트가 자동 체크리스트 생성 못함 |
| 8개를 훨씬 초과 (30개 등) | 인지 불가. 카테고리 분할 필요 |
| 신규 비타협을 plan_<project> 중에 추가 | 영역 침범. plan_harness 로 분리 |
| 마이그레이션 절차 없이 비타협 변경 | 회귀 폭발 |

---

## 다음 단계

- `09_adapt_checklist.md` - 사람 개발자의 직접 적용 절차
- `BOOTSTRAP_PROMPT.md` - 클로드에게 던지는 자동 분석 프롬프트
