# UPGRADE - 킷 신버전 반영 절차

> 이미 하네스를 적용한 프로젝트에 harness_bootstrap 킷의 새 버전을 반영할 때의 표준 절차.
> 원칙: **kit-managed 는 갱신, user-owned 는 절대 불가침, 애매하면 백업 후 수동 병합.**

---

## §1. 버전 확인

- 대상 프로젝트의 STATE 파일 frontmatter 확인:
  ```yaml
  ---
  harness_kit_version: "1.2.0"
  bootstrapped_at: "2026-07-04"
  ---
  ```
- 킷 `CHANGELOG.md` 의 최신 버전과 비교 - 같으면 종료, 다르면 §2 로.
- frontmatter 자체가 없으면 v1.1.0 이하에서 부트스트랩된 프로젝트 - 아래 마이그레이션 노트 v1.2.0 부터 순서대로 적용.

## §2. 차분 파악 - 파일 분류

- manifest 가 있으면 (v1.3.0+ 부트스트랩):
  ```powershell
  python .agent/scripts/harness_manifest.py check
  ```
- manifest 가 없으면 킷 templates/ 와 프로젝트 파일을 수동 diff.
- 분류별 처리:

| 분류 | 의미 | 처리 |
|---|---|---|
| unchanged | 배포 시점 해시와 동일 | kit-managed 표기 항목만 새 템플릿으로 **덮어쓰기 가능** |
| **user_modified** | 해시 불일치 - 사용자가 손댐 | `<파일>.bak-<날짜>` 백업 후 **수동 병합** (자동 덮어쓰기 금지) |
| user_created | manifest 에 없는 사용자 자산 | **절대 건드리지 않음** |
| missing | manifest 에 있는데 파일 없음 | 의도적 삭제인지 확인 후 필요 시 재배치 |

> check 출력에서 `[user-owned/컨텐츠 - 킷 업데이트 대상 아님]` 이 붙은 항목(CLAUDE.md / settings.local.json / BRAIN·STATE / 비표준 이름 커맨드·에이전트)은 unchanged 여도 **덮어쓰기 후보가 아니다** - §3 소유권 규약이 해시 일치보다 우선한다.

- 갱신 완료 후 manifest 재생성:
  ```powershell
  python .agent/scripts/harness_manifest.py generate --kit-version <킷 CHANGELOG 최신 버전>
  ```

## §3. 네임스페이스 소유권 규약

- **kit-managed** - 템플릿 유래 표준 이름. 킷 업데이트가 갱신 대상으로 삼는 유일한 범위:
  - 커맨드: `read_<p>` / `plan_agent_<p>` / `dev_<p>` / `eval_agent_<p>` / `sync_brain` / `commit_push` / `plan_agent_harness` / `dev_harness` / `eval_agent_harness`
  - 에이전트: `plan_<p>` / `eval_<p>` / `plan_harness` / `eval_harness`
  - 스크립트: `ci_gate_<p>.py` + `harness_*.py` / `archive_tasks.py` / `pre_gate.py` / `stop_gate.py` / `model_policy.py` / `glm_mode.py`
  - (`<p>` = 프로젝트 slug)
- **user-owned** - 그 외 프로젝트가 추가한 커맨드/에이전트/스크립트 전부. **킷 업데이트가 절대 덮어쓰지 않는다.**
- 권고: 사용자 자산은 킷 표준 이름과 **충돌하지 않는 이름** 사용 (예: `deploy_<p>`, `weekly_report` 등). 표준 이름을 사용자 자산으로 재정의하면 다음 업데이트에서 kit-managed 로 오인될 수 있다.

## §4. CLAUDE.md 처리

- 사용자 수정이 **가장 잦은** 파일 - 자동 병합하지 않는다.
- 해시 일치 (unchanged): 새 템플릿으로 덮어쓰기 가능.
- 해시 불일치 (user_modified):
  1. `CLAUDE.md` → `CLAUDE.md.bak-<날짜>` 백업
  2. 새 템플릿을 `CLAUDE.md.new` 로 나란히 배치
  3. **사람이 수동 병합** - 여기까지가 킷의 역할, 자동 병합은 하지 않음
- 병합 시 프로젝트 고유 섹션(비타협 표의 프로젝트 항목, DB 규칙 등)은 유지하고, 킷 유래 섹션(워크플로 표, 하네스 규약)만 새 템플릿 기준으로 교체.

## §5. 업데이트 후 검증

- 설치 무결성 셀프 진단:
  ```powershell
  python .agent/scripts/harness_doctor.py
  ```
  - FAIL 0 확인. WARN(드리프트/manifest user_modified) 은 사유 파악 후 판단.
- 하네스 무결성 평가: `/eval_agent_harness` 실행 - frontmatter/JSON/hook 정합성 PASS 확인.
- STATE frontmatter 의 `harness_kit_version` 을 새 버전으로 갱신 + `/sync_brain`.

## §6. 스크립트 허용선 (Phase 2 확정 결정)

- 스크립트는 **Python 표준 라이브러리만** 사용한다 (3.7+). 근거 - PostToolUse hook 이 이미 Python 을 요구하는 유일 의존성이므로 새 의존성이 늘지 않는다.
- 모든 스크립트는 **선택(optional) 자산** - 없어도 하네스는 동작한다. "문서만으로도 완결" 원칙 유지.
- 배포 위치: 킷 `templates/scripts/*.py` → 대상 프로젝트 `.agent/scripts/`. 플레이스홀더 치환 불필요 (slug 는 glob 로 자동 탐지).
- **PreToolUse 훅 계열은 opt-in** - 기본 미등록. 원하는 프로젝트만 settings.local.json 에 수동 등록.

---

## 마이그레이션 노트

### v1.1.0 이하 → v1.2.0

기존 적용 프로젝트가 손으로 반영할 체크리스트:

- [ ] `.claude/agents/eval_*.md` frontmatter 에 `permissionMode: plan` 추가 (**이중 봉쇄** - Write 도구 제외만으로는 Bash 경유 쓰기를 못 막음)
- [ ] eval 계열 result 산출 방식 전환: heredoc 으로 `<task_dir>/*.result` 직접 쓰기 → **YAML 텍스트 반환** (기록: 메인 세션). eval_agent 커맨드/에이전트 본문의 절차 문구 갱신
- [ ] plan 템플릿에 "수용 기준 (Binary AC)" 표 섹션 추가, eval 은 `ac_pass: N/M` 기록
- [ ] 비타협 표에 ZONE 열 (Frozen / Evolvable) 추가
- [ ] ci_gate 시크릿 패턴 확장분 반영 (GitHub OAuth / GitLab / Slack / sk- / ya29 / PEM 접두 변형 / 인증서 블록) - `.agent/config/security_patterns.json` 은 "추가만" 병합
- [ ] HARNESS_GUIDE 에 폐기 자산 명단 표 + 호출 거부 규칙 추가
- [ ] STATE frontmatter 에 `harness_kit_version` / `bootstrapped_at` 스탬프 추가

### v1.2.0 → v1.3.0

- [ ] 스크립트 4종 배치 (전부 선택 자산): `.agent/scripts/` 에 `harness_manifest.py` / `harness_doctor.py` / `archive_tasks.py` / `pre_gate.py` (킷 `templates/scripts/` 에서 복사 - stop_gate.py 는 v1.4.0)
- [ ] manifest 초기 생성: `python .agent/scripts/harness_manifest.py generate --kit-version 1.3.0` - 이후 업데이트부터 §2 분류 자동화
- [ ] `UPGRADE.md` (이 문서) 절차를 프로젝트 운영 문서에서 참조하도록 HARNESS_GUIDE 에 링크 추가
- [ ] plan 템플릿 frontmatter 에 `status` / `tier` 필드 추가
- [ ] PreToolUse 훅을 쓸 프로젝트만 opt-in 등록 (기본 미등록 - §6)
- [ ] 검증: `python .agent/scripts/harness_doctor.py` FAIL 0 + `/eval_agent_harness` PASS

### v1.3.0 → v1.4.0

기존 적용 프로젝트가 손으로 반영할 체크리스트:

- [ ] (선택) `stop_gate.py` 복사 (`templates/scripts/` → `.agent/scripts/`) + Stop 훅 opt-in 등록 (`settings.pretooluse.json.example` 의 Stop 블록 참조)
- [ ] plan 감사 게이트 / HUMAN GATE / eval FAIL 재순환 상한 반영 - `agents/eval_<p>` 에이전트 + `commands/plan_agent_<p>` / `commands/eval_agent_<p>` 커맨드 재배포 또는 수동 병합
- [ ] 세션 핸드오프 3블록 반영 - `commands/commit_push` 재배포 + HARNESS_GUIDE 의 "세션 핸드오프" 절 병합
- [ ] @MX 태그 규율 채택 여부 결정 (03 문서 참조 - 태그 없음이 정상, 수치는 프로젝트별 조정 가능)
- [ ] manifest 재생성: `python .agent/scripts/harness_manifest.py generate --kit-version 1.4.0`

### v1.4.0 → v1.5.0

task 폴더 개명 (`.agent/signals/` → `.agent/tasks/`, `archive_tasks/` → `archive/`):

- [ ] 폴더 이동: `git mv .agent/signals .agent/tasks` (git 미추적이면 `mv`) + `git mv .agent/tasks/archive_tasks .agent/tasks/archive`
- [ ] `.claude/settings.local.json` 의 allow 목록 경로 갱신 (`mkdir -p .agent/signals` / `find .agent/signals ...` → tasks)
- [ ] 커맨드/에이전트의 경로 서술 갱신 (kit-managed 는 재배포로 해결) + CLAUDE.md/HARNESS_GUIDE 의 경로 문구 수동 병합
- [ ] 스크립트 3종 재배포 (archive_tasks.py / stop_gate.py / harness_doctor.py - 경로 상수 변경됨)
- [ ] 검증: `python .agent/scripts/harness_doctor.py` FAIL 0 + manifest 재생성 (`--kit-version 1.5.0`)

### v1.5.0 → v1.6.0

- [ ] (선택) model_policy.py / glm_mode.py 복사 (templates/scripts/ → .agent/scripts/)
- [ ] STATE.md frontmatter 에 model_policy 필드 없으면 수동 추가 (기본값 "inherit")
- [ ] 에이전트별 model 차등을 원하면 `model_policy.py set <tier>` 실행, 05_subagent_design.md §모델 정책 확인
- [ ] GLM 병행을 쓰고 싶다면 06_ci_gate.md §GLM 병행 확인 후 `glm_mode.py setup`
- [ ] manifest 재생성 (--kit-version 1.6.0)

### v1.6.0 → v1.6.3

`/sync_brain` 이 BRAIN.md 갱신까지 판별→컨펌으로 처리하도록 변경 (기존에는 항상 `/plan_agent_harness` 로 미뤘음):

- [ ] `.claude/commands/sync_brain.md` 재배포 (kit-managed) 또는 킷의 `templates/commands/sync_brain.md.template` 내용을 참고해 BRAIN 판별 신호 표 + 컨펌 절차 수동 병합
- [ ] `<PROJECT>_BRAIN.md` 의 실제 섹션 번호/이름에 맞춰 신호 표를 프로젝트 맞춤 조정 (킷 템플릿은 §3/§4/§5/§6/§7/§9 기준 - 부트스트랩 시 다르게 번호를 매겼다면 대조)
- [ ] Antigravity 병용 프로젝트는 `.agent/workflows/sync_brain.md` 도 같은 컨펌 절차로 병합 (있는 경우만)
- [ ] manifest 재생성 (--kit-version 1.6.3)

### v1.6.3 → v1.6.4

Tier S 자동 판정 규칙 구체화 (기존에는 "plan 에이전트가 판정" 뿐이라 매번 M 으로 보수 배정되기 쉬웠음):

- [ ] `.claude/agents/plan_<project>.md` 재배포 (kit-managed) 또는 `templates/agents/plan_PROJECT.md.template` 의 "Tier 판정" 절 내용을 수동 병합
- [ ] `.claude/agents/eval_<project>.md` 재배포 또는 `templates/agents/eval_PROJECT.md.template` 의 tasklist.md 조건부 처리(Tier S 는 부재가 정상) 수동 병합
- [ ] `.claude/commands/plan_agent_<project>.md` 재배포 또는 tasklist.md Tier M/L 전용 문구 수동 병합
- [ ] 이미 진행 중인 Tier S task 가 있다면 tasklist.md 존재 여부로 FAIL 판정하지 않도록 eval 시 유의 (과도기 1회성)
- [ ] manifest 재생성 (--kit-version 1.6.4)
