# 05. 서브에이전트 설계 - 권한 최소화

> plan/eval 서브에이전트의 frontmatter 에서 **tools 화이트리스트** 를 좁혀 셀프 PASS 와 영역 침범을 차단한다.

---

## 핵심 통찰

Claude Code 의 Agent (서브에이전트) 는 **tools 리스트** 에 명시한 도구만 호출할 수 있다. 따라서:

- plan 에이전트의 tools 에 **Edit 를 빼면** 코드 수정 불가능 → "계획만 짜고 실행은 메인 세션이" 라는 격리가 구조적으로 강제됨
- eval 에이전트는 tools 에서 Write 를 빼고 **permissionMode: plan 을 병행**하면 Bash 리다이렉션/heredoc 경유 쓰기까지 차단된다 → result 는 **텍스트 응답으로 반환**하고 메인 세션이 기록. 자기 PASS 조작이 구조적으로 차단
- 모두 Read / Bash 는 두지만 **Write 의 path 제약** 은 프롬프트로 보강

이게 권한 격리의 메커니즘.

---

## 서브에이전트 frontmatter 표준 형식

`.claude/agents/<name>.md` 의 첫 부분 (YAML frontmatter):

```markdown
---
name: plan_<project>
description: <project> 작업 전 계획 수립. 변경 범위 확정, 영향 평가, task 폴더 생성, plan.md + tasklist.md 작성. 소스/하네스 파일 수정 금지. Write 는 .agent/tasks/task_*/ 하위만 허용.
tools: Read, Glob, Grep, Bash, Write, TaskCreate, TaskList
model: inherit
---

(본문 - 에이전트 행동 가이드, 산출물 명세, 점검 항목 등)
```

| 키 | 의미 |
|---|---|
| `name` | 서브에이전트 식별자. `subagent_type` 으로 호출 시 사용 |
| `description` | 서브에이전트의 책임/금지 한 줄 요약. 메인 세션이 서브에이전트 선택 시 참고 |
| `tools` | 허용 도구 화이트리스트 (콤마 구분). 빠진 도구는 호출 불가 |
| `permissionMode` | `plan` 이면 파일 쓰기(도구·Bash 우회 포함)가 차단됨. **eval 계열 필수**. plan 계열은 생략(default) |
| `model` | `inherit` (메인 세션 모델) or 명시 (예: `claude-haiku-4-5`) |

---

## 모델 정책 - 부트스트랩 시 선택 + 언제든 변경

기본값은 항상 `model: inherit` (메인 세션 모델 그대로 상속). 프로젝트 성격/예산에 따라 에이전트 역할별로 model 을 명시적으로 차등화하고 싶으면 아래 정책(tier) 중 하나를 고른다. 요금제별 tier 개념을 우리 4종 에이전트에 맞게 설계한 것 - 자동 감지나 강제 재작성은 하지 않고, 사용자가 명시적으로 고르고 스크립트로 적용하는 방식이다.

| 에이전트 파일명 패턴 | high | medium | low | inherit |
|---|---|---|---|---|
| plan_harness.md (정확히 일치) | sonnet | sonnet | haiku | inherit |
| eval_harness.md (정확히 일치) | sonnet | sonnet | haiku | inherit |
| plan_<slug>.md (plan_harness 제외, 예: plan_sampleapp.md) | opus | opus | sonnet | inherit |
| eval_<slug>.md (eval_harness 제외, 예: eval_sampleapp.md) | opus | sonnet | sonnet | inherit |

근거: plan_<project>는 영향 평가/변경 순서 판단처럼 깊은 추론이 필요해 high/medium 모두 opus 유지. eval_<project>는 증거 기반 판정("의심되면 FAIL" 하드룰)이 핵심이라 opus/sonnet로 한 단계만 낮춘다. plan_harness/eval_harness는 메타 작업(빈도 낮음, 영향 범위 하네스 자체로 국한)이라 한 단계 더 낮게 잡는다. low 에서는 코드/하네스 구분 없이 sonnet/haiku로 수렴시켜 정책 단계를 단순하게 유지한다.

파일명 분류는 순서대로 매칭한다: ① 정확히 `plan_harness.md` ② 정확히 `eval_harness.md` ③ `plan_[a-z0-9_]+\.md` (① 제외) ④ `eval_[a-z0-9_]+\.md` (② 제외) ⑤ 그 외(kit-managed 명명 규칙 밖)는 건드리지 않는다. release 워크플로의 `plan_<release>.md` / `eval_<release>.md` 도 각각 ③ / ④ 행으로 처리되며 별도 행은 두지 않는다.

**적용 방법**:
- 부트스트랩 시 - `BOOTSTRAP_PROMPT.md` 단계 1 에서 질문받는다. 답하지 않거나 "inherit/기본값" 을 선택하면 4개 템플릿 모두 기존과 동일하게 `model: inherit` 로 생성된다 (100% 하위 호환).
- 이후 변경 - `python3 .agent/scripts/model_policy.py set <tier>` 언제든 실행 (선택 자산 스크립트, 없으면 수동으로 각 `.claude/agents/*.md` 의 `model:` 줄을 직접 고쳐도 된다).
- 현재 상태 확인 - `python3 .agent/scripts/model_policy.py show`.

**주의**: eval 계열은 판정 하드룰(증거 없으면 FAIL) 때문에 low 정책에서도 haiku 까지 내려가지 않고 sonnet 을 유지한다 - 판정 신뢰도가 비용보다 우선이다.

---

## 5종 서브에이전트 표준 디자인

### plan_<project>

| 항목 | 값 |
|---|---|
| 책임 | task_<TS>/plan.md + tasklist.md 작성. 영향 평가 포함 |
| tools | `Read, Glob, Grep, Bash, Write, TaskCreate, TaskList` |
| Write 경로 제약 | `.agent/tasks/task_<TS>_<slug>/` 하위만 (프롬프트로 명시) |
| 금지 | 코드 / `.claude/` / `.agent/context/` / `CLAUDE.md` 수정 금지 |

### eval_<project>

| 항목 | 값 |
|---|---|
| 책임 | task_<TS>/ 의 산출물 + 빌드/테스트 결과 검증 → result YAML 텍스트 반환 |
| tools | `Read, Glob, Grep, Bash, TaskList` + `permissionMode: plan` |
| Write 경로 제약 | Write 없음 + permissionMode: plan - result 는 텍스트 반환 (기록: 메인 세션) |
| 결과 파일 | `.agent/tasks/task_<TS>_<slug>/<project>.result` (PASS / FAIL + 근거 - 메인 세션이 저장) |
| 금지 | 소스/하네스 어떤 파일도 수정 금지 |

### plan_harness

| 항목 | 값 |
|---|---|
| 책임 | 하네스 자체 변경 계획 (slash command / subagent / CI Gate / Brain 문서 변경) |
| tools | `Read, Glob, Grep, Bash, Write, TaskCreate, TaskList` |
| Write 경로 제약 | `.agent/tasks/task_harness_<TS>/` 하위만 |
| 금지 | 코드 / `.claude/` / `.agent/` 본체 수정 금지 (메타도 plan 단계에선 변경 X) |

### eval_harness

| 항목 | 값 |
|---|---|
| 책임 | 하네스 무결성 + frontmatter 정합성 + hook 일치성 + JSON 파싱 검증 |
| tools | `Read, Glob, Grep, Bash, TaskList` + `permissionMode: plan` |
| Write 경로 제약 | Write 없음 + permissionMode: plan - result 는 텍스트 반환 (기록: 메인 세션) |
| 점검 | 디렉토리/파일 무결성 / settings.local.json JSON 파싱 / py_compile / hook 일치성 / archive 동작 |

### plan_<release> / eval_<release> (선택)

배포 워크플로가 있는 프로젝트만. 추가 권한:
- **MCP execute_sql** - Supabase 등 DB 토글 검증
- **Bash adb / curl** - 단말 / 외부 응답 검증

---

## 이중 봉쇄 - tools 화이트리스트 + permissionMode

tools 화이트리스트만으로는 구멍이 남는다 - Write 를 빼도 **Bash heredoc/리다이렉션** (`cat > file <<EOF`, `echo ... > file`) 으로 파일을 쓸 수 있다 (이 문서 초기 버전이 스스로 인정하던 약점). 이 우회를 막는 장치가 `permissionMode` 병행이다:

1. **사후 평가자 (eval 계열) 에 한해** frontmatter 에 `permissionMode: plan` 을 추가 → Bash heredoc/리다이렉션 경유 쓰기까지 차단
2. 단 plan 모드에서는 파일 쓰기 자체가 안 되므로 **result 는 YAML 텍스트로 반환**하고 **메인 세션이 `<task_dir>/*.result` 로 저장** - 역할 분담
3. 빌드/테스트 등 셸 실행은 `settings.local.json` 의 allow 화이트리스트를 따른다 (평가 기능은 유지)
4. **사전 계획자 (plan 계열) 에는 적용하지 않는다** - tasks/ 하위 Write (plan.md / tasklist.md) 가 필요하기 때문

---

## description 컨벤션 - NOT for / MUST INVOKE

각 에이전트의 frontmatter `description` 말미에 관할 경계와 호출 트리거를 한 줄로 명시한다:

```
... NOT for: <관할 밖 작업>. MUST INVOKE when: <호출 트리거>.
```

| 에이전트 | 말미 예시 |
|---|---|
| `plan_<p>` | NOT for: 코드 구현 / eval 판정. MUST INVOKE when: 비-사소 작업 시작 전 계획이 필요할 때. |
| `eval_<p>` | NOT for: 구현 / plan 작성. MUST INVOKE when: /dev_<p> 완료 후 판정이 필요할 때. |
| `plan_harness` | NOT for: 일반 코드 계획. MUST INVOKE when: .claude/ .agent/ CLAUDE.md 변경 계획이 필요할 때. |
| `eval_harness` | NOT for: 하네스 수정. MUST INVOKE when: 하네스 변경 후 무결성 판정이 필요할 때. |

근거: 에이전트 간 관할 중복/오호출을 description 수준에서 차단한다 (메인 세션이 서브에이전트 선택 시 description 을 참고하므로).

---

## tools 화이트리스트 핵심 항목

| 도구 | 의미 | plan 에 둘까 | eval 에 둘까 |
|---|---|---|---|
| `Read` | 파일 읽기 | ✅ | ✅ |
| `Glob` | 패턴 매칭 | ✅ | ✅ |
| `Grep` | 텍스트 검색 | ✅ | ✅ |
| `Bash` | 셸 실행 (빌드/테스트 포함) | ✅ | ✅ |
| `Write` | 파일 생성/덮어쓰기 | ✅ (tasks/ 만) | ❌ |
| `Edit` | 파일 부분 편집 | ❌ | ❌ |
| `TaskCreate` | task 트래커 추가 | ✅ | (선택) |
| `TaskList` / `TaskUpdate` | task 트래커 조회/갱신 | (선택) | ✅ |
| `mcp__supabase__execute_sql` | DB 조회/변경 | ❌ | ✅ (release 만) |
| `mcp__supabase__apply_migration` | 마이그레이션 | (release plan 만) | (release eval 만) |

**Edit 는 일반적으로 서브에이전트에서 제외**. Edit 가 있으면 plan 에이전트가 코드를 수정해버릴 수 있어 권한 격리가 깨진다. Write 는 tasks/ 경로 제약을 프롬프트로 강제.

---

## 본문 (system prompt) 의 구조

frontmatter 다음의 본문은 서브에이전트의 **system prompt** 다. 표준 섹션:

```markdown
## 책임 / 권한

(이 에이전트가 하는 일 / 안 하는 일 / Write 경로)

## 입력

(슬래시 호출 시 args / 메인 세션이 전달하는 context)

## 산출물

(생성해야 하는 파일 정확한 경로 / 내용 골격)

## 점검 항목

(완료 전 셀프 체크)

## 출력 형식

(메인 세션에게 어떤 형식으로 보고 돌려보낼지)

## 금지

(절대 하지 말 것 명시)
```

---

## 예시 1 - plan_<project> 본문 골격

```markdown
## 책임

<project> 작업 전 plan.md + tasklist.md 작성.

## Write 허용 경로

`.agent/tasks/task_<YYYYMMDD>_<HHMM>_<slug>/` 하위만.

## 산출물 1: plan.md (필수 섹션)

### 변경 범위
- 변경 레이어
- 대상 화면(또는 클래스)
- 변경 파일 목록
- 경계 (이 task 에서 다루지 않는 것)

### 영향 평가
- 비타협 항목 (BRAIN.md 참조) 변경 여부 체크리스트
- 영구화 키 변경 여부

### 변경 순서
(단계별 작업 흐름)

### 리스크 + 대응

### 사용자 컨펌 필요 항목

## 산출물 2: tasklist.md

- 각 단계의 체크박스 + 누가 수행하는지 (Claude / 사용자)

## 금지

- 어떤 코드 파일도 수정 금지
- .claude/ .agent/ 본체 수정 금지
- CLAUDE.md 수정 금지

## 진입 시 archive 실행

```bash
find .agent/tasks -maxdepth 1 -type d -name "task_*" -mmin +120 -exec mv {} .agent/tasks/archive/ \;
```

(이 한 줄로 활성 폴더가 정리되어 다음 task 가 깔끔히 시작)
```

---

## 예시 2 - eval_<project> 본문 골격

```markdown
---
name: eval_<project>
description: <project> 구현 완료 후 평가. plan.md AC 표 실행-대조 + PASS/FAIL 선언. result 는 YAML 텍스트로 반환하고 기록은 메인 세션이 한다. NOT for: 구현 / 파일 수정 / plan 작성. MUST INVOKE when: /dev_<project> 완료 후 판정이 필요할 때.
tools: Read, Glob, Grep, Bash, TaskList
permissionMode: plan
model: inherit
---

## 책임

task_<TS>/ 의 산출물 + 빌드/컴파일/테스트 결과 검증 → result 를 YAML 텍스트로 반환.

## Write 권한

**없음** + `permissionMode: plan` (이중 봉쇄 - Bash 리다이렉션/heredoc 경유 쓰기까지 차단). result 는 파일로 쓰지 않고 아래 YAML 을 **최종 텍스트 응답에 그대로 포함**한다. 메인 세션이 `<task_dir>/<project>.result` 로 저장:

```yaml
status: PASS
task: <TS>_<slug>
ac_pass: "5/5"
checks:
  - name: ac_table
    result: PASS
    evidence: "AC-1~5 모두 pass 조건 일치 (명령별 exit code 0)"
  - name: kotlin_compile
    result: PASS
    evidence: "BUILD SUCCESSFUL in 9s (exit 0)"
  - name: tasklist_completion
    result: PASS
    evidence: "12/12 체크박스 (tasklist.md)"
  - name: page_size_consts
    result: PASS
    evidence: "ItemRepository.kt:L12 PAGE_SIZE/MAX_PAGE_SIZE 불변"
notes:
  - "..."
```

## 점검 항목

1. plan.md 의 수용 기준 (Binary AC) 표 실행-대조 → `ac_pass: "N/M"` 산출
2. tasklist.md 완료율
3. (언어별 컴파일/타입체크 명령 실행)
4. 비타협 항목 회귀 점검
5. (단말/외부 검증, 해당 시)

PASS 에는 모든 check 의 evidence (exit code / 출력 인용 / 파일:라인) 필수. 증거 없으면 FAIL, 의심되면 FAIL.

## 출력 형식

메인 세션에 짧은 요약 + result YAML 전문 반환 (메인 세션이 파일로 저장).

## 금지

- 어떤 소스/하네스 파일도 수정 금지
- Edit / Write 도구 미사용 (frontmatter 에서 빠져 있어야 함)
- Bash 리다이렉션/heredoc 으로 파일 생성 시도 금지 (permissionMode: plan 이 차단)
```

---

## 안티패턴

| 안티패턴 | 왜 나쁜가 |
|---|---|
| plan 에이전트에 Edit 부여 | 권한 격리 깨짐. plan 이 코드 직접 수정 |
| eval 에이전트에 Write 부여 | 자기 PASS 임의 작성 가능 |
| eval 에 permissionMode 누락 | Bash heredoc/리다이렉션 우회 여지가 남음 (tools 단일 방어) |
| 한 서브에이전트가 plan + dev + eval 다 함 | 안전망 무력화 |
| tools 에 `*` (전체) 부여 | 화이트리스트 의미 없음 |
| Write 경로 제약을 프롬프트로만 강제 (frontmatter 와 불일치) | 우회 가능 |

---

## 다음 단계

- `06_ci_gate.md` - PostToolUse hook 의 Python 스크립트 작성법
- `07_task_lifecycle.md` - task 폴더의 라이프사이클
