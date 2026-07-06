# 03. 워크플로 패턴

> 동일한 plan → dev → eval 패턴이 **3종 (또는 4종)** 으로 분기되는 이유와 흐름.

---

## 왜 분기하는가

대상 영역이 다르면 **권한 / 점검 항목 / SSOT 갱신 대상** 이 다르기 때문이다. 한 종으로 통합하면:

- 하네스 변경 도중 코드 손댐 (영역 침범)
- 배포 작업이 BRAIN 을 갱신하는 권한 부여 (불필요 위험)
- 일반 코드 작업이 OTA 메타 검증을 강제 (오버헤드)

각 워크플로는 **plan agent / dev / eval agent** 3개의 슬래시 + (선택적으로) **dev 가 다루는 영역 화이트리스트** 를 갖는다.

---

## 워크플로 1 - 일반 코드 (`<project>`)

대상: 비즈니스 코드 (`app/src/`, `src/`, `lib/`, 라우트, UI 등).

```
/read_<project>              세션 워밍업 - BRAIN/STATE/코드인덱스 자동 Read
       ↓
/plan_agent_<project>        plan 서브에이전트 → plan.md + tasklist.md
       ↓
/dev_<project>               메인 세션이 Edit/Write 실행
       ↓
/eval_agent_<project>        eval 서브에이전트 → result PASS/FAIL
       ↓
사용자 확인 PASS
       ↓
/sync_brain                  STATE.md 갱신 + BRAIN.md 갱신 필요 판별→컨펌 (Phase 표 / 화면 목록 / 최근 task)
       ↓
/commit_push                 자동 스테이징 필터 + 메시지 type 선택
```

**전형 사용** - 새 화면 추가 / 버그 수정 / 리팩터.

`/plan_agent_<project>` 진입 시 plan 에이전트가 **자동으로 비타협 항목 체크리스트** 를 plan.md 에 채워서 사용자 컨펌 게이트를 만든다.

### 수용 기준 (Binary AC) - plan.md 필수 섹션

서술형 기준("동작이 자연스러울 것")은 eval 판정이 주관적이 된다 - **검증 명령 + 기계 판정 가능한 pass 조건** (exit code / 출력 문자열 / 파일 존재) 으로 못박아 eval 재현성을 확보한다.
eval 은 이 표를 그대로 실행-대조하여 result 에 `ac_pass: "N/M"` 을 기록한다.

| AC-ID | 검증 명령 | pass 조건 |
|---|---|---|
| AC-1 | `./gradlew :app:compileDebugKotlin` | exit 0 |
| AC-2 | `grep -c "coerceIn(MIN_PERCENT" MainActivity.kt` | 출력 ≥ 1 |
| AC-3 | `adb shell dumpsys package <pkg> \| grep versionCode` | versionCode=<N> 포함 |

소규모 수정 (파일 1~2개, ~50 LOC) 은 AC 3개 이하로 충분하다.

### Tier - task 규모별 산출물 차등

AC 표 강제가 소규모 수정에서 형식주의가 되는 것을 막는 안전판 - 과잉 형식화가 plan 이탈을 부르는 역효과를 예방한다.

| Tier | 판정 조건 | plan 산출물 | AC |
|---|---|---|---|
| S | 자동 판정 규칙(아래) 충족 | plan.md 단일 (축약 - 리스크/의존성/후속task 섹션 생략 가능) | 3개 이하 |
| M | S 조건 미충족 (또는 승격 근거 명시) | plan.md + tasklist.md | 제한 없음 |
| L | 다파일 / 설계 판단 필요 / 비타협 인접 | plan.md + tasklist.md + analysis_report.md | 제한 없음 + 검증 시나리오 필수 |

plan.md frontmatter 의 `tier:` 필드로 선언한다.

#### Tier S 자동 판정 규칙 - 근거 없이는 벗어나지 못한다

초기 설계는 "plan 에이전트가 판정해 명시"라고만 돼 있었는데, 실무에서 이러면 plan 에이전트가 보수적으로 매번 M 을 골라 Tier S 가 유명무실해진다. 그래서 방향을 뒤집는다 - **S 가 기본값이고, M/L 로 올리려면 근거가 필요하다**:

1. 사용자 요청 문구에 버그 / 수정 / 오류 / crash / exception / fix / hotfix 류 키워드가 있는가
2. Glob/Grep 으로 즉시 추정 가능한 변경 예상 파일 수가 2개 이하인가
3. 비타협 항목(BRAIN.md 진입점/영구화 키)에 직접 걸리지 않는가

세 조건 모두 충족 → Tier S 를 기본값으로 배정. 하나라도 불충족·불명확하면 plan.md 변경 범위 절에 왜 S 로 부족한지 1줄 근거를 적고 Tier M 으로 배정한다. (구체 절차는 `templates/agents/plan_PROJECT.md.template` §Tier 판정 - 서브에이전트가 실제로 따르는 본문은 여기가 아니라 그 템플릿이다. `.claude/` `.agent/` 만 배포되고 이 문서(01~09)는 킷 저장소에만 있기 때문.)

### plan 감사 게이트 + HUMAN GATE (Tier M/L)

plan 산출물을 작성자(plan 에이전트)가 아닌 쪽 - **eval 에이전트의 plan 감사 모드** - 이 적대적으로 검증한다. 감사 항목 4종: Binary AC 표의 기계 판정 가능성 / 비타협 체크리스트 누락 / 변경 범위-순서 서술 모순 / 대응 없는 리스크.

흐름: plan → (Tier M/L) plan 감사 → **HUMAN GATE (사용자 승인 - 감사 PASS 로 대체 불가, 자율 bypass 금지)** → dev.

재시도 상한: plan 감사 3회 / eval FAIL 재순환 3회 - 상한 도달 시 사용자 에스컬레이션.

### @MX 태그 규율 - 태그 없음이 정상

취지: 위험/중요 코드에만 코드 주석 태그를 달아 plan/eval 시 grep 한 번으로 위험 지점을 찾는다. 남발은 신호대잡음비를 죽인다 - **태그 없음이 정상 상태**.

태그 3종 + 부여 조건 (제안값 - 프로젝트별 조정 가능):

| 태그 | 부여 조건 |
|---|---|
| `@MX:ANCHOR` | 참조 fan-in 3 이상인 핵심 지점 - 파일당 3개 상한 |
| `@MX:WARN <REASON>` | 위험 로직 - REASON 없는 WARN 금지 |
| `@MX:TASK task_<TS>_<slug>` | 해당 변경의 근거 task 폴더 역추적 |

수명주기: 참조 대상(태그가 가리키는 task 폴더/심볼)이 사라지면 `@MX:LEGACY` 로 강등 후 다음 리팩터에서 제거 - 낡은 태그 방치 금지.

설정 예시 (프로젝트가 `.agent/config/mx_tags.json` 으로 저장 가능):

```json
{"fan_in_anchor": 3, "anchor_per_file": 3, "warn_requires_reason": true}
```

eval 연계: eval 은 `grep -rn "@MX:WARN" <변경 파일>` 로 위험 지점 회귀를 우선 점검할 수 있다.

---

## 워크플로 2 - 하네스 자체 (`harness`)

대상: `.claude/` `.agent/` `CLAUDE.md` - **메타 영역**.

```
/plan_agent_harness          plan 서브에이전트 (write 권한 tasks 만)
       ↓
/dev_harness                 메인 세션 (메타 파일 편집 - 코드 영역은 제외)
       ↓
/eval_agent_harness          eval 서브에이전트 (CI Gate 자체 점검 / hook 일치성 / frontmatter 정합성)
```

**전형 사용**:
- 새 슬래시 커맨드 추가
- 서브에이전트 권한 조정
- CI Gate 검사 항목 추가
- BRAIN.md 키 인벤토리 마이그레이션

**중요** - 하네스 변경이 코드 변경을 유발하는 경우 (예: BRAIN 의 SharedPreferences 키 추가 → 코드 마이그레이션 필요) **별도 plan_agent_<project> task** 로 분리. 한 task 가 코드 + 하네스를 동시에 손대지 않는다.

`eval_agent_harness` 의 점검 항목:
- 디렉토리/파일 무결성 (commands/ agents/ 필수 파일 존재)
- frontmatter 정합성 (name / description / model / tools 키 모두 존재)
- `python -m py_compile ci_gate_<project>.py` 통과
- `json.load(settings.local.json)` 통과
- hook command 와 실제 스크립트 경로 일치
- archive/ 디렉토리 존재

---

## 워크플로 3 - 배포 (`<release>`)

대상: versionCode/version 증분 + Storage 업로드 + DB 토글 + 단말 검증 등 외부 영향 변경.

```
/plan_agent_<release>        versionCode 결정 + R8 keep / 시그너처 / Storage URL 영향 평가
       ↓
/dev_<release>               빌드 + 사인 + APK 메타 + MCP INSERT (is_active=false)
       ↓
사용자: Dashboard 업로드 / Vercel deploy / DB row 활성화 등 외부 액션
       ↓
/eval_agent_<release>        Storage 확인 + 토글 + 단말 logcat + HOME 발화 검증
       ↓
사용자 확정
       ↓
/sync_brain → /commit_push
```

**전형 사용** - OTA 신버전 출시 / 패키지 deploy / DB migration.

배포 워크플로는 **외부 시스템과 상호작용** 한다는 점이 핵심:
- Supabase Storage / DB → MCP execute_sql / 마이그레이션
- Vercel / Cloudflare / Play Console → 사용자 액션
- 단말 / 실제 디바이스 → adb logcat / screenshot

따라서 eval 단계가 **단말 또는 외부 서비스 응답을 직접 검증** 한다.

배포 없는 프로젝트 (라이브러리 / 도구 / 학습용) 는 이 워크플로 자체를 갖지 않는다.

---

## 워크플로 4 (선택) - 서버사이드 (`<server>`)

대상: Supabase Edge Function / Postgres migration / Next.js API route 등.

```
/plan_agent_<server>         schema diff + Edge Function 영향 / RLS 정책 평가
       ↓
/dev_<server>                Edge Function deploy / apply_migration
       ↓
/eval_agent_<server>         curl / MCP execute_sql / Edge logs / Sentry 확인
```

sampleapp 의 경우 server 측 (sampleapp_server) 작업은 **별도 repo 의 자체 워크플로** 로 처리한다. 단일 사용자가 server 와 client 양쪽을 동시 작업할 때 **각 repo 에서 독립 워크플로** 를 진입하는 패턴.

---

## 슬래시 매핑 - 프로젝트별 명명 규칙

`<project>` 자리에 들어갈 후보:
- Android client: `sampleapp` / `launcher` / `client`
- Next.js admin: `admin` / `webapp` / `server`
- iOS app: `ios`

본래 프로젝트의 통념 명칭을 따른다. 다만 **너무 짧으면 (예: `app`) 혼란**, **너무 길면 (예: `sampleapp_launcher_main`) 타이핑 부담**. 보통 6~10자 추천.

---

## 워크플로 비교표

| 항목 | 일반 코드 | 하네스 | 배포 | 서버사이드 |
|---|---|---|---|---|
| dev 범위 | `app/src/` | `.claude/` `.agent/` `CLAUDE.md` | 빌드 산출물 + 외부 업로드 | `supabase/` `app/api/` |
| 사용자 외부 액션 필요 | 보통 없음 | 없음 | **있음 (Dashboard 업로드)** | **있음 (deploy)** |
| eval 의존 외부 시스템 | (대부분 없음) | (없음) | **단말 + Storage + DB** | **DB + Edge logs** |
| SSOT 갱신 대상 | STATE.md | BRAIN.md or HARNESS_GUIDE.md | STATE.md + (BRAIN.md versionCode) | STATE.md + BRAIN.md DB schema |
| 비타협 항목 점검 | **강한** (런처 / Prefs 등) | **강한** (hook / 권한) | **매우 강한** (versionCode / 시그너처) | **강한** (RLS / 인증) |
| 평균 소요 | 30분~수시간 | 10~30분 | 1~3시간 (외부 액션 포함) | 30분~2시간 |

---

## 안티패턴

| 안티패턴 | 왜 나쁜가 |
|---|---|
| 일반 코드 plan 에서 .claude 손대기 | 영역 침범. 하네스 워크플로로 분리해야 |
| 배포 workflow 에서 코드 신규 추가 | 배포는 잠긴 코드 빌드만. 신규 코드면 일반 워크플로 선행 |
| plan 없이 dev 직진 | 영향 평가 누락 |
| eval 통과 후 추가 변경 | "PASS 후 일변경" → 회귀. 새 task 로 다시 진입 |
| 한 task 가 코드 + 하네스 + 배포 모두 손댐 | 점검 항목 폭발. 분리 |

---

## 다음 단계

- `04_ssot_brain_state.md` - BRAIN/STATE 의 구체 작성법
- `05_subagent_design.md` - 서브에이전트 frontmatter 의 권한 화이트리스트
