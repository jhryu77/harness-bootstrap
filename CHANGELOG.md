# CHANGELOG

> harness_bootstrap kit 의 변경 이력.

---

## v1.7.0 - 2026-07-16

> 사촌 프로젝트(R_D 하네스) 운영 중 드러난 개선을 역전파. 킷은 "1 repo = 1 하네스" 전제라 멀티프로젝트 전용 개선(CLAUDE.md 사본 동기화 / 중앙 프로젝트 목록 / gc_check)은 반영하지 않았다.

### Fixed

- **harness_doctor BRAIN 드리프트 정규식이 볼드 표기를 놓침** - `last_synced_commit\s*[:=]` 이 `> **last_synced_commit**: <hash>` 같은 **볼드** 표기를 못 잡아 그 BRAIN 을 **조용히 skip** 했다. 필드명 뒤 `\**` + 값 앞 char class 에 `*` 추가로 평문·볼드·백틱 모두 매칭. (`templates/scripts/harness_doctor.py`) 단일 repo `cwd=root` 가정은 그대로 유지(킷 모델에서 옳음).

### Changed

- **permissionMode: plan 의 근거 상태 정직화** - `05` 가 "permissionMode: plan 을 병행하면 **Bash 리다이렉션/heredoc 경유 쓰기까지 차단 → 자기 PASS 조작이 구조적으로 차단**"이라고 **단언**했으나 근거가 없었다. 공식 문서는 리다이렉트가 권한 프롬프트를 띄운다고만 하고 서브에이전트에서의 프롬프트 처리를 명시하지 않는다. "이중 봉쇄 → **2층 방어**", "차단됨 → 미확인"으로 정정하고 근거 상태 표를 추가. **이 구성이 지키는 것은 "에이전트가 쓰려 하지 않는다"이지 "물리적으로 못 쓴다"가 아니다.** (부트스트랩된 프로젝트에 거짓 보안 확신을 전파하던 문제)
- **비타협 표: 순번 → 영구 ID** - `08` 표 첫 열을 `#`(순번) 에서 **카테고리 문자+번호 영구 ID**(A1/B1/D2…)로. 순번은 행이 늘 때마다 참조가 썩는다. 다른 문서는 `비타협 D2` 처럼 ID 로 참조하고, 폐기 ID 는 재사용하지 않는다. "표에 행 수 하드코딩 금지" 규율 추가. `examples/sampleapp_snapshot/CLAUDE.md` 동기화.

### Added

- **dev(메인세션) 루프 모델 티어링** - `model_policy.py` 는 서브에이전트만 티어링했는데, 정작 토큰을 가장 많이 쓰는 dev 는 메인세션 멀티턴이라 커버되지 않았다(커맨드 frontmatter model 은 "호출한 그 턴만" 유효 - 공식 문서). `set <tier> --with-session-baseline` 옵션으로 `settings.local.json` 의 model 도 세션 baseline 으로 설정해 dev 루프까지 티어링. `05` 에 "티어링 갭" 절 추가.
- **sync_brain 서브에이전트 옵션 패턴** - `05` 에 "선택 패턴" 절 + `templates/agents/sync_brain.md.template`(옵션 자산). 기본값은 커맨드 유지. 컨텍스트 격리/모델 티어링이 필요할 때만 디스패처+서브에이전트로. PATCH/HANDOFF 반환 프로토콜(쓰기 안 줌). plan/eval 과 격리 이유가 다름(셀프 PASS 차단 아님)을 명시. "신규 에이전트는 만든 세션에서 호출 불가(레지스트리 세션 시작 시 고정)" 함정 문서화.

### 결정 (반영하지 않음)

- **CLAUDE.md 사본 동기화 / 중앙 projects.json / gc_check** - R_D 는 정션/하드링크로 CLAUDE.md 2벌을 동기화하고 중앙 프로젝트 목록을 두지만, 킷은 "1 repo = 1 하네스 + 단일 CLAUDE.md + 포인터(복사 금지)" 원칙이라 대응 개념이 없다. gc_check 은 R_D 에서도 규칙 대부분이 오탐으로 판명돼 미도입.

---

## v1.6.5 - 2026-07-11

### Fixed

- **CI Gate hook 크로스플랫폼 (윈도우/맥 공용)** - PostToolUse hook·pre_gate·stop_gate command 가 bare `python …` 이라 **macOS 에서 exit 127 로 조용히 실패**했다(macOS 는 `python` 이 PATH 에 없고 `python3` 만 존재. Windows 는 보통 반대). command 를 `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 … || exec python …'` **인터프리터 감지형**으로 교체 - Claude Code hook 은 macOS=sh / Windows=git-bash(기본) 로 실행되므로 한 줄로 양 OS 공용. `command -v` 로 **인터프리터 존재만** 판별해 `exec`(스크립트 종료코드에 `||` 를 걸면 CI Gate 의 non-zero=위반보고를 폴백으로 오인해 이중 실행되므로 금지). 대상: `templates/settings.local.json.template`, `templates/settings.pretooluse.json.example`, `examples/sampleapp_snapshot/settings.local.json` + hook JSON 을 보여주는 문서(`01/02/06/09`).
- **문서·에이전트·스크립트의 수동 python 명령 정합** - eval_harness/dev_harness 실행 블록은 `command -v` 감지형으로, 그 외 문서/테이블/docstring 의 실행 명령(`python -m py_compile`, `python .agent/scripts/*.py` 등)은 canonical `python3` 로 통일(테이블 `||` 파손·가독성 회피). `python3` 부재 Windows 는 `python` 대체 - `CLAUDE.md.template`/`06_ci_gate.md` 에 인터프리터 규약 주석 추가. (스크립트 내부 서브프로세스는 `pre_gate.py` 가 `sys.executable` 사용으로 기존부터 크로스플랫폼 안전 - 무변경.)

### Changed

- **상태바(statusLine) 부트스트랩 필수화** - `templates/statusline.py`(전역 상태바: 모델/폴더/git + 컨텍스트·5H·7D 사용률·reset 카운트다운)를 종전 "(선택) 개인 자산" 에서 **하네스 적용 시 필수 반영**으로 승격(세션 예산 가시성 = 워크플로 판단 근거). `BOOTSTRAP_PROMPT.md` 에 필수 스텝 `6.6 상태바 설치` 신설, `OVERVIEW.md`/`README.md`/`statusline.py` docstring 의 "(선택)" → "(필수)". 등록 command 도 감지형(`sh -c 'command -v python3 … && exec python3 … || exec python …'`)으로 - bare `python <HOME>/.claude/statusline.py` 는 macOS 에서 상태바가 안 떴다.

### Added

- **statusLine 에 `/effort` 상태 표시** - `templates/statusline.py` 가 세션 JSON 의 `effort.level`(low/medium/high/xhigh/max, 공식 docs 확인 + 실측)을 모델 라벨 옆 `[high]` 로 강도색 표기(low=녹/medium=청/high=황/xhigh=마젠타/max=적). 모델이 effort 파라미터 미지원이면 필드 부재 → 우아하게 생략.
- **statusLine `refreshInterval: 60` 권장** - 세션 **유휴 상태에서도** 사용률·reset 카운트다운·`/effort` 상태가 갱신되도록 등록 예시(BOOTSTRAP 6.6 / 09 단계9 / docstring)에 `"refreshInterval": 60`(초=1분) 추가. Claude Code 문서상 이벤트 갱신에 **추가로** 동작하며 로컬 실행이라 API 토큰 무소비.

---

## v1.6.4 - 2026-07-06

### Changed

- **Tier S 자동 판정 규칙 구체화** - 기존 "plan 에이전트가 판정해 명시"는 규칙이 없어 실무에서 매번 보수적으로 M 이 배정되고 Tier S 가 유명무실해지기 쉬웠다. `templates/agents/plan_PROJECT.md.template` 에 구체 규칙 추가 - 버그/수정류 키워드 + 변경 파일 ≤2개 + 비타협 항목 비접촉 세 조건을 모두 충족하면 Tier S 가 **기본값**, M/L 로 올리려면 근거 1줄이 필요한 방향으로 뒤집었다.
- **Tier S 전용 축약 plan.md** - 리스크/의존성/후속task 섹션 생략 가능, `tasklist.md`(산출물 2) 자체를 생성하지 않음 (plan.md 의 "변경 순서" 절이 대체). `templates/commands/plan_agent_PROJECT.md.template`, `templates/agents/eval_PROJECT.md.template` 도 tasklist.md 부재를 FAIL 사유로 취급하지 않도록 동기화
- `03_workflow_patterns.md` Tier 절에 위 규칙 반영 + "왜 이 문서(01~09)가 아니라 템플릿 본문에 규칙을 직접 써야 하는가"(01~09 는 킷 저장소에만 있고 배포되지 않음) 명시

---

## v1.6.3 - 2026-07-06

### Changed

- **`/sync_brain` 이 BRAIN.md 갱신까지 한 흐름에서 처리** - 기존에는 BRAIN(저빈도 SSOT) 갱신이 항상 별도 `/plan_agent_harness` 진입을 요구해 번거로웠다. 이제 `/sync_brain` 이 `last 갱신` 이후 diff 를 신호 표(핵심 클래스/엔드포인트, 신규 영구화 키, 의존성, 권한, 진입점, 비타협 항목)와 자동 대조하고, 신호가 있으면 섹션별 diff 를 제시해 사용자 컨펌을 받은 뒤 그 자리에서 반영한다. 기존 키의 이름/타입 변경처럼 마이그레이션이 필요한 구조 변경만 `/plan_agent_harness` 로 남긴다.
- `templates/commands/sync_brain.md.template`, `04_ssot_brain_state.md`, `03_workflow_patterns.md`, `OVERVIEW.md`, `templates/HARNESS_GUIDE.md.template`, `examples/sampleapp_snapshot/` 전반에 위 절차 반영

---

## v1.6.2 - 2026-07-06

### Added

- `templates/statusline.py` 에 `session_name` 표시 추가 (`--name` 플래그 또는 `/rename` 으로 설정한 커스텀 세션 이름, 없으면 표시 안 함)

### Fixed

- **stdin 인코딩 버그** - `sys.stdout` 만 UTF-8 로 재설정하고 `sys.stdin` 은 재설정하지 않아, Windows 환경에서 콘솔 코드페이지(cp949 등) 기본값으로 `json.load(sys.stdin)` 이 비 ASCII 필드를 읽는 시점부터 깨지는 문제. `session_name` 처럼 한글이 포함된 필드에서 발생. `sys.stdin.reconfigure(encoding="utf-8")` 를 읽기 전에 추가해 해결

---

## v1.6.1 - 2026-07-06

### Changed

- `templates/statusline.py` 설치 안내에 `refreshInterval`(초 단위) 옵션 언급 추가 - 유휴 상태에서도 5H/7D 카운트다운이 갱신되도록. 이벤트 기반 갱신을 대체하지 않고 추가로 동작하며, 로컬 실행이라 API 토큰을 소비하지 않는다.

---

## v1.6.0 - 2026-07-04

### Added

- **모델 정책 선택 + 상시 변경** - 부트스트랩 시 model 정책(high/medium/low/inherit) 질문 + `model_policy.py`(선택 스크립트, set/show) 로 언제든 재적용. 4개 핵심 에이전트(plan/eval x project/harness) 역할별 매핑표는 05_subagent_design.md 참조. 기본값은 변함없이 model: inherit
- **GLM 병행 옵션 (실험적, opt-in)** - `glm_mode.py`(선택 스크립트). GLM(z.ai) 라우팅 Claude Code 를 tmux 새 창에 띄우는 수동 유틸리티(setup/spawn/status/teardown). Claude Code 의 자동 다중 에이전트 오케스트레이션이 아니라 사람이 직접 작업을 나누는 방식. 기본 비활성, 어떤 hook 도 자동 호출하지 않음

### Changed

- README.md "무엇인가" 절에 harness 비유 문장 재배치
- 선택 스크립트 5종 → 7종

---

## v1.5.0 - 2026-07-04

### Changed

- **task 폴더 개명**: `.agent/signals/` → **`.agent/tasks/`**, 그 안의 `archive_tasks/` → **`archive/`** - 역할이 이름에 드러나도록. 문서/템플릿/스크립트/예시 전면 반영 (스크립트 3종 경로 상수 포함)
- 출처·검증 이력 문구 제거 - "~에서 검증되었다/실제 자산" 류 주장을 예시(example) 프레이밍으로 전환 (README/OVERVIEW/CHANGELOG/BOOTSTRAP/01/02/08/09)
- 라이선스 절에서 원본 출처 서술 삭제

### 마이그레이션 (기존 적용 프로젝트)

- UPGRADE.md 의 v1.4.0 → v1.5.0 체크리스트 참조 (폴더 이동 + settings allow 목록 + 스크립트 재배포)

---

## v1.4.0 - 2026-07-04

### Added

- **plan 감사 게이트 + HUMAN GATE** (A15) - eval 에이전트의 "plan 감사 모드" (Tier M/L, 전용 에이전트 신설 없이 경량 번안). 감사 4항목(AC 기계판정성/비타협 누락/범위 정합/리스크 대응), 재시도 상한 3회, 감사 PASS ≠ 착수 (HUMAN GATE - 사용자 승인 필수), eval FAIL 재순환 상한 3회
- **stop_gate.py** (A16, opt-in) - Stop 훅 advisory: 턴 종료 시 git 변경 파일 광역 검사 → systemMessage 경고만 (차단 없음), stop_hook_active 루프 가드, HEAD SHA 기록으로 커밋당 1회
- **세션 핸드오프 3블록 규칙** (A16) - 전제검증/실행 명령/다음 액션, 트리거 3종 (컨텍스트 임계치/task 완료/커밋 푸시). commit_push 는 푸시 후 자동 출력
- **@MX 태그 규율** (A18) - 태그 없음이 정상. ANCHOR(fan-in 3+, 파일당 3 상한)/WARN(REASON 필수)/TASK(task 폴더 역추적), 깨진 참조는 LEGACY 강등. 03 문서 + dev 템플릿

### Changed

- settings.pretooluse.json.example 에 Stop 훅 블록 추가 (opt-in 훅 예시 통합)
- 스크립트 4종 → 5종 (stop_gate.py)

### 결정

- plan 감사 주체 = 기존 eval 에이전트의 plan 감사 모드 (오픈 결정 3 - 서브에이전트 4종 유지)
- 미러 패리티(배포본-원본 드리프트 자동 검증) 검토 항목은 보류

---

## v1.3.0 - 2026-07-04

### Added

- **templates/scripts/ 4종 (선택 자산)** - `archive_tasks.py`(status 기준 아카이브) / `harness_doctor.py`(설치 진단) / `harness_manifest.py`(해시 manifest + merge-gitignore) / `pre_gate.py`(PreToolUse 커밋 게이트+위험 명령, opt-in)
- **UPGRADE.md** - 킷 업데이트 절차 + 네임스페이스 소유권 규약 + 버전별 마이그레이션 노트
- **settings.pretooluse.json.example** - PreToolUse opt-in 등록 예시
- **plan.md frontmatter status(active/done)/tier(S/M/L) 필드** - archive 판정의 SSOT + 산출물 차등 (A8/A17)
- **STATE §6 에 ac_pass/커밋 SHA 열** (A9), **FROZEN 존 경고** (A13), **컨텍스트 다이어트 규칙** (A14, 02/04)
- **06_ci_gate 훅 이벤트별 출력 채널 표** (A11)

### Changed

- archive 자동화: status 기준 스크립트 권장, mtime find 는 fallback

### 결정

- 스크립트 허용선 확정: Python 표준 라이브러리 / 전부 선택 자산 / PreToolUse 는 opt-in (오픈 결정 1)

---

## v1.2.0 - 2026-07-04

### Added

- **Binary AC 표** (A1) - plan.md 필수 섹션 "수용 기준(Binary AC)", eval 은 실행-대조 후 ac_pass N/M 기록
- **eval 이중 봉쇄** (A2) - eval 계열 frontmatter 에 permissionMode: plan 병행, result 는 YAML 텍스트 반환(기록: 메인 세션) 로 전환
- **PASS 증거 하드룰** (A3) - 모든 check 에 evidence 필수, 의심되면 FAIL
- **ZONE 태깅** (A4) - 비타협 표에 Frozen/Evolvable 열, 08_immutables.md 태깅 가이드
- **시크릿 패턴 확장** (A5) - GitHub OAuth/GitLab/Slack/sk-/ya29/인증서 + PEM 접두 변형, .agent/config/security_patterns.json "추가만" 병합
- **폐기 자산 명단 규칙** (A6) - HARNESS_GUIDE 폐기 표 + 호출 거부 규칙
- **킷 버전 스탬프** (A7 전반부) - STATE frontmatter harness_kit_version/bootstrapped_at
- **진화 부채 지표** (A19) - read/sync 출력에 마지막 하네스 task 시점 + 90일 경고
- **NOT for / MUST INVOKE 컨벤션** (A20) - 에이전트 description 관할 명시
- **하네스 커맨드 템플릿 2종 신규** - dev_harness / eval_agent_harness (templates 18 → 20개)

### Changed

- 원칙 개수 표기 정정 (8가지 → 9가지, README/OVERVIEW/BOOTSTRAP 원칙 표 9행화)
- harness_onboarding 경로 참조 → harness_bootstrap 통일
- 주요 bash 블록에 PowerShell 등가 병기 착수 (A17 전반부)

---

## v1.1.0 - 2026-07-03

### Added

**`templates/statusline.py`** - Claude Code 전역 상태바 스크립트 (선택 자산, 플레이스홀더 치환 불필요)
- 1행: 모델 / 컨텍스트 크기(200K/1M) / Claude Code 버전 / 현재 폴더 / git 브랜치
- 2행: CW(컨텍스트) / 5H(5시간 rate limit) / 7D(7일 rate limit) 사용률 막대 + 세션 비용
- 5H / 7D 는 `rate_limits.*.resets_at` (epoch 초) 기반 **reset 까지 남은 시간 카운트다운** 표시 (예: `(1h47m)` / `(2d0h)`)
- Claude Code 공식 stdin 세션 JSON 만 사용, 외부 의존성 없음 (python 3.7+)
- 설치: `~/.claude/statusline.py` 로 복사 후 `~/.claude/settings.json` 의 `statusLine.command` 에 등록
- git 브랜치는 subprocess 없이 `.git/HEAD` 직접 파싱 (statusLine 타임아웃 회피, worktree/submodule 대응)

### Changed

- `README.md` / `OVERVIEW.md` - templates 인덱스에 statusline.py 반영 (17 → 18개, 총 57 파일)

---

## v1.0.0 - 2026-05-12

### Added

**핵심 문서 9종** (`01_*.md` ~ `09_*.md`)
- `01_philosophy.md` - **9가지** 핵심 원칙 (SSOT 분리 / 3단계 워크플로 / task 격리 / 권한 최소화 / CI Gate / 자동 로드 / 워크플로 분리 / 정책 명시 / **살아있는 하네스 = 코드와 공동 진화**)
- `02_architecture.md` - `.claude/` + `.agent/` + `CLAUDE.md` 3 자산 + 데이터 흐름 + mono/multi repo 패턴
- `03_workflow_patterns.md` - 일반 / 하네스 / 배포 / 서버사이드 4종 워크플로
- `04_ssot_brain_state.md` - BRAIN/STATE 분리 + 갱신 절차
- `05_subagent_design.md` - frontmatter tools 화이트리스트 설계
- `06_ci_gate.md` - PostToolUse hook + 표준 검사 3종 + 추가 검사 패턴
- `07_task_lifecycle.md` - task_<TS>_<slug>/ + 120분 archive
- `08_immutables.md` - 비타협 항목 카테고리 + plan_agent 자동 체크리스트
- `09_adapt_checklist.md` - 사람 개발자 직접 적용 8단계 + FAQ

**진입점 4종**
- `README.md` - 사람 독자 진입점 (시나리오 2가지 안내)
- `OVERVIEW.md` - **한 페이지 전체 그림 + 모든 문서 인덱스** (워크플로 ASCII 다이어그램 + 시나리오별 권장 진입점)
- `BOOTSTRAP_PROMPT.md` - Claude 자동 부트스트랩 7단계 프롬프트
- `CHANGELOG.md` (이 파일)

**templates/** 17개
- `CLAUDE.md.template` - 자동 로드 압축본
- `BRAIN.md.template` / `STATE.md.template` - SSOT 2종
- `HARNESS_GUIDE.md.template` - 운영 매뉴얼
- `settings.local.json.template` - Claude Code 설정
- `ci_gate.py.template` - PostToolUse hook 스크립트
- `commands/` 7종: read / plan_agent / dev / eval_agent / sync_brain / commit_push / plan_agent_harness
- `agents/` 4종: plan_<project> / eval_<project> / plan_harness / eval_harness

**examples/**
- `sampleapp_snapshot/` - sampleapp 하네스 풀 구성 예시
  - CLAUDE.md / HARNESS_GUIDE.md / settings.local.json (절대경로 → `<YOUR_PROJECT_ROOT>` 치환) / ci_gate_sampleapp.py
  - commands/ 13개 / agents/ 6개 (sampleapp 예시 파일)
- `sampleapp_server_inventory/INVENTORY.md` - Next.js admin webapp (raw 상태) 의 인벤토리 실례
- `case_study.md` - sampleapp_app (적용 상태) + sampleapp_server (적용 시 예상) 비교 시나리오

### 예시 프로젝트

- `sampleapp_app` (Android 앱) + `sampleapp_server` (Next.js sibling) - cross-repo 패턴 예시 포함

### 적용 가능 스택 예시

- Kotlin / Gradle / Android (sampleapp_app 원본)
- TypeScript / Next.js / Supabase (sampleapp_server, BOOTSTRAP_PROMPT 적용 예정)
- Python / Node / Rust 등 다른 스택도 동일 패턴 가능 (CI Gate 의 언어별 검사만 교체)

---

## 향후 개선 후보 (v1.1+ 가능성)

- [ ] BOOTSTRAP_PROMPT 의 단계 1 자동 분석을 더 정교화 (예: pyproject.toml의 [tool.poetry] vs setuptools 구분)
- [ ] CI Gate 의 Swift / Go / Rust 검사 함수 reference 구현 추가
- [ ] templates/ 의 release 워크플로 3종 템플릿 추가 (현재 plan_agent_<release> 등 미포함)
- [ ] examples/ 에 비-Android / 비-Next.js 한 케이스 추가 (예: Python FastAPI 마이크로서비스)
- [ ] BOOTSTRAP_PROMPT 의 영어 번역본 (현재 한국어 본문, 영어는 키워드만)
