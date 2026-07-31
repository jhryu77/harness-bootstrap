# sampleapp_server - Raw 프로젝트 인벤토리

> 이 폴더는 **하네스가 적용되지 않은 raw Next.js 프로젝트** 의 인벤토리 실례.
> sampleapp_app (Android, 하네스 풀 적용) 와 대비되는 second example.
> BOOTSTRAP_PROMPT.md 의 단계 1 (프로젝트 분석) 이 산출해야 할 결과의 **목표 형태**.

---

## 1. 기본 정보

| 항목 | 값 |
|---|---|
| 디렉토리 | `/Users/<user>/workspace/sampleapp_server` |
| git remote | (사용자 별 GitHub) |
| 마지막 commit (스냅샷 시점) | 2026-05-12 |
| 하네스 상태 | **.claude/ / .agent/ / CLAUDE.md 전부 미존재** |

## 2. 스택 (package.json 추출)

```json
{
  "name": "sampleapp-admin-webapp",
  "scripts": ["dev", "build", "start", "lint", "typecheck"],
  "dependencies": [
    "@sentry/nextjs",
    "@supabase/ssr",
    "@supabase/supabase-js",
    "@upstash/ratelimit",
    "@upstash/redis",
    "next",                  // 14.x App Router
    "react",
    "react-dom",
    "recharts",              // 차트
    "resend"                 // 이메일
  ]
}
```

| 레이어 | 기술 |
|---|---|
| Framework | Next.js 14 (App Router, RSC + Server Actions) |
| 언어 | TypeScript 5 |
| UI | Tailwind CSS 3 + Linear Style UI 토큰 |
| DB | Supabase Postgres + RLS |
| 인증 | Supabase Auth (email/password) + RBAC 3 role + lockout |
| 모니터링 | Sentry (env 옵션) |
| Rate Limit | Upstash Redis (env 옵션, in-memory fallback) |
| Email | Resend (env 옵션) |
| 차트 | Recharts |

## 3. 디렉토리 트리

```
sampleapp_server/
├── .env.local.example        환경변수 템플릿
├── .git/
├── .gitignore
├── README.md                 6KB - 기술 스택 + 디자인 시스템 + 라우트 표
├── DEPLOY.md                 5KB
├── app/                      Next.js App Router 라우트
│   ├── account/
│   ├── admins/
│   ├── api/
│   │   ├── auth/
│   │   ├── crash-reports/
│   │   ├── devices/
│   │   ├── licenses/
│   │   └── ota/
│   ├── audit/
│   │   └── access-logs/
│   ├── auth/
│   │   ├── callback/
│   │   └── reset-password/
│   ├── automation/
│   │   ├── [id]/
│   │   └── new/
│   ├── crash-reports/
│   │   └── [id]/
│   ├── dashboard/
│   ├── devices/
│   │   └── [id]/
│   ├── diagnostics/
│   │   └── [fingerprint]/
│   ├── licenses/
│   │   ├── [id]/
│   │   └── new/
│   ├── login/
│   ├── ota/
│   │   ├── [id]/
│   │   └── new/
│   └── settings/
├── components/
├── instrumentation.ts        Sentry init
├── lib/                      유틸 / Supabase client / RBAC / audit
├── middleware.ts             Next.js middleware (auth/RBAC)
├── next.config.mjs
├── package.json
├── package-lock.json
├── postcss.config.mjs
├── sentry.client.config.ts
├── sentry.edge.config.ts
├── sentry.server.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── tsconfig.tsbuildinfo      (build 산출 - gitignore)
└── vercel.json
```

## 4. 라우트 인벤토리 (22+ 페이지 + 5 API)

| 라우트 | 종류 | 용도 |
|---|---|---|
| `/login` | page | 로그인 화면 |
| `/dashboard` | page | 대시보드 (라이선스 + 단말 KPI) |
| `/licenses` | page | 라이선스 목록 |
| `/licenses/[id]` | dynamic page | 라이선스 상세 |
| `/licenses/new` | page | 라이선스 발급 |
| `/devices` | page | 단말 목록 |
| `/devices/[id]` | dynamic page | 단말 상세 |
| `/ota` | page | OTA 매니페스트 목록 |
| `/ota/[id]` | dynamic page | OTA 상세 |
| `/ota/new` | page | OTA 등록 |
| `/automation` | page | 자동화 매핑 목록 |
| `/automation/[id]` | dynamic page | 자동화 매핑 상세 |
| `/automation/new` | page | 자동화 매핑 신규 |
| `/crash-reports` | page | 크래시 보고 목록 |
| `/crash-reports/[id]` | dynamic page | 크래시 보고 상세 |
| `/diagnostics` | page | 단말 진단 데이터 목록 |
| `/diagnostics/[fingerprint]` | dynamic page | 단말 진단 상세 |
| `/audit/access-logs` | page | 접속 로그 감사 |
| `/admins` | page | 관리자 사용자 관리 |
| `/account` | page | 본인 계정 |
| `/settings` | page | 설정 |
| `/auth/callback` | route | Supabase Auth 콜백 |
| `/auth/reset-password` | page | 비밀번호 재설정 |
| `/api/auth/...` | route handler | 인증 API |
| `/api/crash-reports/...` | route handler | 크래시 보고 API |
| `/api/devices/...` | route handler | 단말 API |
| `/api/licenses/...` | route handler | 라이선스 API |
| `/api/ota/...` | route handler | OTA 매니페스트 API |

## 5. 외부 의존 / 환경변수 (.env.local.example 추정)

- `NEXT_PUBLIC_SUPABASE_URL` - Supabase 프로젝트 URL
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` - Supabase anon key
- `SUPABASE_SERVICE_ROLE_KEY` - Supabase service role (서버만)
- `SENTRY_DSN` / `NEXT_PUBLIC_SENTRY_DSN` - Sentry
- `UPSTASH_REDIS_REST_URL` / `UPSTASH_REDIS_REST_TOKEN` - Upstash
- `RESEND_API_KEY` - Email
- 기타 RBAC / 도메인 설정

## 6. sibling repo 인터페이스

sampleapp_app (Android client) 와의 공유 DB tables:
- `licenses` - 라이선스 발급/조회
- `devices` - 단말 등록 1:N
- `ota_manifests` - APK URL + SHA-256
- `crash_reports` - UncaughtExceptionHandler 송신
- `device_diagnostics` - Phase Z 진단 데이터
- `access_log_queue` - 접속 로그
- `audit_logs` / `admin_users` - admin 전용

Edge Functions (client 호출):
- `license-check`, `license-issue`, `license-restore`
- `ota-manifest`
- `crash-report`
- `diagnostics-report`
- (선택) `toss-webhook`

## 7. 하네스 적용 시 예상 비타협 항목

`BOOTSTRAP_PROMPT.md` 단계 2 에서 사용자가 결정해야 할 항목들 (예상):

### 인증 / 권한
- Supabase RLS 정책 변경 시 사용자 컨펌
- RBAC role 정의 (super_admin / admin / viewer) 변경 시 컨펌
- middleware.ts 의 라우트 가드 패턴 변경 시 컨펌

### API / 응답 스키마
- `/api/licenses` 응답 schema (Android client 가 의존)
- `/api/ota` 응답 schema (OTA 매니페스트 포맷)
- Server Actions return type 일관성

### DB / Storage
- Supabase 테이블 컬럼 명/타입 변경 시 마이그레이션 동반
- ota_manifests 의 `apk_url` 형식 (Storage public URL 패턴)

### 환경변수 / 시크릿
- `.env.local` 자동 스테이징 금지 (`.gitignore` 강제 + CI Gate `.env.example` 시크릿 검사)
- `SUPABASE_SERVICE_ROLE_KEY` 클라이언트 측 노출 차단

### 외부 서비스
- Sentry / Upstash / Resend 환경변수 누락 시 fail-soft (env 옵션이므로 미설정 가능)

## 8. 하네스 적용 시 예상 Phase 분류

새 STATE.md §1 의 첫 Phase 표 후보:

| # | Phase | 상태 |
|---|---|---|
| 0 | 하네스 부트스트랩 | ⬜ (지금 진행 중) |
| 1 | Next.js App Router + Supabase Auth 기본 골격 | ✅ (이미 구현됨) |
| 2 | RBAC 3 role + middleware 가드 | ✅ |
| 3 | 라이선스 22 페이지 + API 5종 | ✅ |
| 4 | 크래시 보고 / 진단 / 감사 로그 통합 뷰 | ✅ |
| 5 | Sentry / Upstash / Resend 통합 | ✅ |
| 6 | 디자인 시스템 (Linear Style UI 토큰) | ✅ |
| 7 | Vercel 배포 자동화 (git push 트리거) | ⬜ |
| 8 | E2E 테스트 (Playwright) | ⬜ |
| 9 | 새 기능 - 라이선스 갱신 알림 자동 발송 | ⬜ |

기존 코드가 잘 정리되어 있어서 부트스트랩 시 대부분 Phase 는 ✅ 마킹.

## 9. 하네스 적용 시 슬래시 매핑 후보

- `<project>` slug 후보: `webapp` / `admin` / `server`
- 추천: **`webapp`** (가장 짧고 의미 명확)

표준 7종 + 하네스 3종 = 10개. 배포 워크플로 (Vercel) 는 자동화이므로 별도 슬래시 불필요.

## 10. 적용 시 CI Gate 추가 검사 후보

`ci_gate_webapp.py` 에 표준 3종 + 추가:

```python
def check_env_example_secret(path, content):
    """`.env.example` 에 실제 시크릿 의심값"""
    if not path.endswith(".env.example"): return None
    suspicious = re.findall(r"(SECRET|TOKEN|KEY|PASS|DSN)=([A-Za-z0-9_\-]{20,})", content)
    if suspicious:
        return f".env.example 에 실제 시크릿 의심값: {[s[0] for s in suspicious]}"
    return None

def check_typescript_basic(path, content):
    """TS/TSX 괄호 매칭 경량"""
    if not path.endswith((".ts", ".tsx")): return None
    opens = content.count("{")
    closes = content.count("}")
    if abs(opens - closes) > 0:
        return f"TS 괄호 불일치: '{{' {opens} 개 / '}}' {closes} 개"
    return None

def check_service_role_key_clientside(path, content):
    """클라이언트 컴포넌트에 SERVICE_ROLE_KEY 사용"""
    if "/api/" in path or "use server" in content: return None
    if "use client" in content and "SERVICE_ROLE_KEY" in content:
        return "클라이언트 컴포넌트에 SUPABASE_SERVICE_ROLE_KEY 사용 - 보안 사고. 서버 측 (Route Handler / Server Action) 으로 이동"
    return None
```

---

## 11. 결론

sampleapp_server 는 **이미 완성도 높은 Next.js 프로젝트** 지만 하네스가 없어서:

- 매 Claude 세션 컨텍스트 재구축 비용
- 비타협 항목 (RLS / RBAC) 무심코 변경 위험
- task 작업 흔적 휘발 - "왜 이렇게 했더라" 회귀

`harness_bootstrap/BOOTSTRAP_PROMPT.md` 의 7단계 적용으로 30~60분 만에 sampleapp_app 와 동등한 안전망을 갖춘다.

핵심 포인트: **같은 하네스 골격이 스택 차이를 흡수**. Kotlin/Gradle (launcher) 와 TypeScript/Next.js (server) 모두 동일 SSOT 분리 + 3단계 워크플로 + CI Gate hook + 권한 격리 패턴 적용.
