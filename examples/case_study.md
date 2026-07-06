# Case Study - sampleapp 두 repo 의 하네스 적용 시나리오

> 동일 사용자가 운영하는 **2 repo** 의 비교 - sampleapp_launcher (Android, 하네스 풀 적용) + sampleapp_server (Next.js admin, 하네스 미적용 raw).
> 이 문서는 onboarding kit 을 어떤 식으로 두 종류 상황에 적용하는지의 종단 사례.

---

## 1. sampleapp_launcher - 하네스 풀 적용 상태

### 1.1 컨텍스트

- 분류: 차량용 Android SampleApp 런처
- 스택: Kotlin / Gradle / ConstraintLayout
- 모듈: 단일 `:app` + companion APK
- 상태: Phase O10 (크래시 보고 + 진단 수집) 완료, OTA 풀 사이클 검증 통과

### 1.2 적용된 하네스 자산

```
sampleapp_launcher/
├── CLAUDE.md                          172줄 - 자동 로드 압축본
├── .claude/
│   ├── settings.local.json            83줄 - PostToolUse hook + 권한 화이트리스트
│   ├── commands/    13개              read/plan/dev/eval(sampleapp) + sync_brain + commit_push + test_sampleapp + harness 3종 + ota_release 3종
│   └── agents/      6개               plan/eval (sampleapp / harness / ota_release)
└── .agent/
    ├── HARNESS_GUIDE.md               200줄 - 운영 매뉴얼
    ├── context/
    │   ├── SAMPLEAPP_BRAIN.md             367줄 - 패키지/디렉토리 트리/클래스 책임/12개 SharedPreferences 키 인벤토리/카컴페터 분석
    │   └── SAMPLEAPP_STATE.md             426줄 - Phase 표 30+ 행/구현 화면 표/최근 task 5개
    ├── scripts/ci_gate_sampleapp.py       144줄 - 임시파일/시크릿/Kotlin 괄호 검사
    └── tasks/
        ├── task_<TS>_<slug>/          활성 task 폴더 (mtime 120분 룰)
        └── archive/             30+ 완료 task 보관
```

### 1.3 비타협 항목 (CLAUDE.md §6~§7)

런처 비타협 8개:
1. `<intent-filter>` 의 MAIN+HOME+DEFAULT+LAUNCHER
2. `screenOrientation="landscape"`
3. `configChanges` 8종 풀세트
4. `launchMode="singleTask"` + `stateNotNeeded="true"`
5. `resizeableActivity="false"`
6. `AppPickerActivity.exported="false"`
7. 시그너처 권한 4종 (CAPTURE_VIDEO_OUTPUT / INTERNAL_SYSTEM_WINDOW / INJECT_EVENTS / MANAGE_ACTIVITY_TASKS)
8. 자기 자신 picker 제외 (`InstalledApps.selfPkg` 필터)

분할/Prefs 비타협 8개:
1. `MIN_PERCENT 0.20 / MAX_PERCENT 0.80 / DEFAULT_PERCENT 0.70` 상수
2. 비율 적용 시 `coerceIn(...)`
3. `layout_constraintGuide_percent` (0.0~1.0)
4. SharedPreferences 파일 분리 (`split_ratio` ↔ `pane_slots`)
5. `PaneSlot` enum 순서 / `storageKey` 변경 금지
6. Picker 그리드 column = 6
7. DividerHandle 24dp / DividerVisual 4dp 분리
8. `VIRTUAL_DISPLAY_FLAG_TRUSTED = 1 shl 5 = 32`

### 1.4 종단 시나리오 - Phase Z (단말 진단 수집) 작업

작업 흐름:

```
1. /read_sampleapp
   → SAMPLEAPP_BRAIN.md + SAMPLEAPP_STATE.md 자동 로드
   → 현재 Phase 표 / 구현 화면 / 영구화 키 인벤토리 / 최근 task 출력

2. /plan_agent_sampleapp "단말 OS/하드웨어 진단 수집 + Supabase 송신 인프라"
   → plan_sampleapp 서브에이전트 진입
   → archive/ 로 mtime 120분 초과 폴더 자동 이동
   → 신규 task_20260512_1757_device_diagnostics_collection/ 생성
   → plan.md (영향 평가 + 변경 순서 + 리스크 + 사용자 컨펌 항목) 작성
   → tasklist.md (체크박스 단위) 작성

3. 사용자 컨펌 (plan.md §사용자 컨펌 항목)
   - Supabase 신규 테이블 추가 (device_diagnostics) → 컨펌
   - 신규 SharedPreferences 파일 (diagnostics_prefs) 추가 → 컨펌

4. /dev_sampleapp
   → 메인 세션이 plan 에 따라 직접 Edit/Write
   → 매 Edit 후 PostToolUse hook (ci_gate_sampleapp.py) 자동 실행
   → 신규 파일 14개 (DiagnosticsManager + 12 collector + ...) 추가
   → SampleAppApplication.onCreate 에서 호출

5. supabase/migrations/20260512175700_create_device_diagnostics.sql 작성
   → MCP apply_migration 으로 적용

6. supabase/functions/diagnostics-report/index.ts 작성
   → MCP deploy_edge_function

7. /eval_agent_sampleapp
   → eval_sampleapp 서브에이전트 진입
   → 컴파일 검증 (./gradlew :app:compileDebugKotlin) PASS
   → 인텐트 필터 보존 확인
   → 분할 비율 상수 보존 확인
   → 영구화 키 인벤토리 일관성
   → device_diagnostics.result 파일 Bash heredoc 작성

8. 단말 실측 검증 (별도 task - mac 인계)
   → task_20260512_2038_phase_z_mac_validation/
   → Step 3 (gradle installDebug)
   → Step 4 (Logcat + cold start) - 사용자 액션
   → Step 5 (Supabase MCP execute_sql) - Claude
   → Step 6 (12 검증 포인트 대조) - Claude
   → TEST-DEVICE-01 단말에서 code=201 + DB row 1건 + fp_source=serial 확인

9. PASS 후 /sync_brain
   → SAMPLEAPP_STATE.md §1 Phase Z 행 추가 (✅)
   → §3 빌드 구성 시점값 (versionCode=9) 갱신
   → §6 최근 task 5개 갱신

10. /commit_push
    → 자동 스테이징 필터 (tasks/*.result 제외)
    → 커밋 메시지 "추가: Phase Z 단말/OS 호환성 진단 수집 인프라 (dev + eval PASS, mac 인계)"
    → main 푸시
```

총 소요 - 약 6시간 (분석 + 코드 + 검증 + 단말 실측 인계).

각 단계가 task 폴더에 영구 기록되어, 6개월 후 누군가 "왜 Phase Z 가 도입되었나" 질문에 task_20260512_1757 의 plan.md + handoff_mac.md + result 로 즉시 답변 가능.

---

## 2. sampleapp_server - 하네스 미적용 raw 상태

### 2.1 컨텍스트

- 분류: A/B Car런처 Admin Webapp (실 서비스)
- 스택: Next.js 14 (App Router, RSC + Server Actions) + TypeScript 5
- 인프라: Supabase Auth + RBAC + Audit / Sentry / Upstash Redis / Resend / Recharts / Tailwind
- 라우트: 22+ 페이지 (account / admins / audit / auth / automation / crash-reports / dashboard / devices / diagnostics / licenses / login / ota / settings)
- API: /api/auth /api/crash-reports /api/devices /api/licenses /api/ota
- 상태: **`.claude/` / `.agent/` / `CLAUDE.md` 전부 미존재 (raw)**

### 2.2 onboarding kit 적용 시 해야 할 일

`BOOTSTRAP_PROMPT.md` 의 7단계를 그대로 수행:

#### 단계 1 - 프로젝트 분석 (Claude 가 자동 수행)

```bash
find . -maxdepth 3 -name "package.json" -o -name "*.config.ts" -o -name "next.config.*"
git log --oneline -10
cat package.json
ls app/
```

산출:
- 스택: Next.js 14 + TS 5 + Supabase + Sentry
- 모듈: 단일 Next.js 모노 + lib/ + components/
- 라우트 패턴: App Router (page.tsx) + 동적 라우트 (`[id]`, `[fingerprint]`)
- API: Route Handlers (`route.ts`)

#### 단계 2 - 비타협 항목 추출 (사용자 컨펌)

질문 항목 후보:
- "Supabase RLS 정책 변경 시 사용자 컨펌 필수?"
- "RBAC role 정의 (super_admin / admin / viewer) 변경 시 컨펌 필수?"
- "API 응답 schema (라이선스 / OTA 매니페스트) 변경 시 컨펌 필수?"
- "Sentry / Upstash / Resend 환경변수 패턴은?"
- ".env.example 의 어떤 키들이 절대 .env.local 에 실제값으로 들어가면 안 되는가?"

산출 (가정):
- 비타협: Supabase RLS / RBAC role / API response schema / 인증 콜백 URL
- 자동 스테이징 금지: `.env.local` `.env.development` `*.tsbuildinfo`

#### 단계 3 - SSOT 초안 작성

`WEBAPP_BRAIN.md` 예시:
```
§1 제품 요약: A/B Car런처 Admin Webapp, com.sampleapp.admin
§2 디렉토리 트리: app/ + lib/ + components/ + supabase migrations/edge functions
§3 핵심 라우트: 22 페이지 + 5 API
§4 영구화: Supabase DB tables (licenses / devices / ota_manifests / crash_reports / audit_logs / admin_users)
§5 빌드: Next.js 14, Node 20, npm
§6 인증: Supabase Auth (email/password) + RBAC 3 role + lockout
§7 라우트 진입점: Server Actions vs Route Handlers
§8 빌드 커맨드: npm run dev / npm run build / npm run typecheck
§9 비타협: RBAC role / RLS / API schema (위 단계 2 결과)
§10 외부 의존: Supabase / Sentry / Upstash / Resend
```

`WEBAPP_STATE.md` 예시 - 초기:
```
§1 Phase: 하네스 부트스트랩 ⬜ (지금 진행 중)
§2 git: 현재 브랜치 + HEAD
§3 빌드: package.json version
§4 화면 22개 (✅ 또는 ⬜)
§6 최근 task: (비어 있음)
```

#### 단계 4 - slash command + subagent 생성

`{{PROJECT}}` = `webapp`

생성 파일:
- `.claude/commands/read_webapp.md`
- `.claude/commands/plan_agent_webapp.md`
- `.claude/commands/dev_webapp.md`
- `.claude/commands/eval_agent_webapp.md`
- `.claude/commands/sync_brain.md`
- `.claude/commands/commit_push.md`
- `.claude/commands/plan_agent_harness.md`
- `.claude/commands/dev_harness.md`
- `.claude/commands/eval_agent_harness.md`
- `.claude/agents/plan_webapp.md`
- `.claude/agents/eval_webapp.md`
- `.claude/agents/plan_harness.md`
- `.claude/agents/eval_harness.md`

배포 워크플로는 **Vercel deploy 가 있으나 자동화 (git push 트리거)** 이므로 별도 `<release>` 슬래시는 불필요. 대신 supabase 마이그레이션 / Edge Function deploy 가 별도 워크플로 후보.

#### 단계 5 - CI Gate 작성

`.agent/scripts/ci_gate_webapp.py`:
- 공통 검사 2종 (임시파일 / 시크릿)
- TypeScript 경량 검사 (괄호 매칭) - 표준 `check_typescript_basic`
- 추가: `.env.example` 의 의심 시크릿 검사 (`SECRET=실제값` 패턴)

#### 단계 6 - CLAUDE.md 작성

200줄 이하 압축본. 비타협 항목 표 + 빌드 명령 (`npm run dev` / `npm run build` / `npm run typecheck`).

#### 단계 7 - 첫 task 실행으로 검증

`/eval_agent_harness` 진입 → 디렉토리/파일/frontmatter/JSON/hook 모두 PASS 확인.

### 2.3 결과

sampleapp_server 가 raw 상태에서 **약 30~60분** 만에 sampleapp_launcher 와 동등한 하네스를 갖게 된다.

이때 client / server 간 인터페이스는 **각 BRAIN.md §10 외부 의존** 에 명시:

```
[sampleapp_launcher BRAIN §10]
- sampleapp_server (sibling repo): Supabase 인증/라이선스 발급 처리 - admin webapp
- 인터페이스: Supabase REST/Edge Function URL
- Edge Function: license-check, license-issue, ota-manifest, crash-report, diagnostics-report

[sampleapp_server BRAIN §10]
- sampleapp_launcher (sibling repo): Android client, Supabase 인증 토큰 발급/소진
- 인터페이스: Supabase RLS 정책 + RBAC role 정의 (admin_users.role)
- 공유 DB tables: licenses / devices / ota_manifests / crash_reports
```

두 repo 의 BRAIN.md 가 서로의 인터페이스를 정의하면 cross-repo 작업이 명시적이 된다.

---

## 3. 두 사례에서 본 onboarding kit 효과

| 항목 | sampleapp_launcher | sampleapp_server (적용 후 가정) |
|---|---|---|
| 하네스 적용 비용 | 이미 적용 (30+ task 누적) | 약 30~60분 (BOOTSTRAP_PROMPT 활용) |
| Phase 추적 가능성 | 30+ 행 표로 즉시 보임 | 즉시 부트스트랩 가능 |
| 비타협 항목 자동 점검 | plan_sampleapp 가 자동 체크리스트 | plan_webapp 도 자동 체크리스트 |
| 새 세션 워밍업 | `/read_sampleapp` 1회로 풀 컨텍스트 | `/read_webapp` 1회로 풀 컨텍스트 |
| 시크릿/임시파일 누수 차단 | CI Gate 작동 중 (Kotlin) | CI Gate 작동 (TypeScript + `.env.example` 검사) |
| cross-repo 작업 | sibling_repo permission + plan_agent 분리 진입 | 동일 |

**핵심 통찰**: 같은 하네스 골격이 Android (Kotlin) / Next.js (TypeScript) 두 스택에 동일하게 적용 가능. 차이는 **CI Gate 의 언어별 검사** 와 **CLAUDE.md / BRAIN.md 의 도메인 비타협 항목** 뿐.

---

## 4. 운영 패턴

같은 사용자가 client + server 양쪽 작업할 때:

1. client 변경: `sampleapp_launcher/` cwd 진입 → `/plan_agent_sampleapp` 등
2. server 변경: `sampleapp_server/` cwd 진입 → `/plan_agent_webapp` 등
3. cross-repo (예: API schema 변경) - **두 repo 각각 plan task 진입** → BRAIN.md §10 외부 의존 인터페이스 갱신 → 양쪽 dev → 각자 eval → 양쪽 commit_push

cross-repo 단일 task 로 묶지 않는다. 각 repo 의 영향 평가가 독립적이어야 안전.
