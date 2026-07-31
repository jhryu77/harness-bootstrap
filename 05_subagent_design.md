# 05. 서브에이전트 설계 - 권한 최소화

> plan/eval 서브에이전트의 frontmatter 에서 **tools 화이트리스트** 를 좁혀 셀프 PASS 와 영역 침범을 차단한다.

---

## 핵심 통찰

Claude Code 의 Agent (서브에이전트) 는 **tools 리스트** 에 명시한 도구만 호출할 수 있다. 따라서:

- plan 에이전트의 tools 에 **Edit 를 빼면** 코드 수정 불가능 → "계획만 짜고 실행은 메인 세션이" 라는 격리가 구조적으로 강제됨
- eval 에이전트는 tools 에서 Write 를 빼고 **permissionMode: plan 을 병행**하는 **2층 방어**를 쓴다 → result 는 **텍스트 응답으로 반환**하고 메인 세션이 기록. 이 구성이 지키는 것은 "에이전트가 파일을 쓰려 하지 않는다"이지 "물리적으로 못 쓴다"가 아니다 (아래 "permissionMode 근거 상태" 참조)
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
| `permissionMode` | `plan` 은 공식 "reads only" 모드 - 도구 쓰기를 막는다. Bash 경유 쓰기까지 막는지는 **미확인**(아래 근거 상태 참조). **eval 계열 필수**(2층 방어), plan 계열은 생략(default) |
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

### 이 정책이 dev(메인세션) 루프를 커버하지 않는다 - 티어링 갭

위 정책은 **서브에이전트(plan/eval) 의 frontmatter model 만** 바꾼다. 그런데 **토큰을 가장 많이 쓰는 구간은 dev** 다 - `/dev_<p>` 는 서브에이전트가 아니라 **메인 세션에서 구현→피드백→수정을 오가는 멀티턴 대화**이고, 여기엔 위 정책이 손대는 frontmatter 가 없다.

- 서브에이전트는 실행 전체가 지정 모델로 돈다 (plan/eval 티어링이 완전히 유효).
- 커맨드 frontmatter 의 model 은 공식 문서상 **"호출한 그 턴에만"** 적용되고 다음 프롬프트에 세션 모델로 복귀한다 ("the session model resumes on your next prompt"). 즉 `/dev_<p>` 에 model 을 박아도 **2번째 턴부터 풀린다** → 멀티턴 dev 를 티어링하지 못한다.
- **dev 루프를 티어링하려면 `settings.local.json` 의 `model` 을 세션 baseline 으로 설정한다.** 이건 `/model` 실행 또는 세션 재시작 후 반영된다.

→ 즉 완전한 모델 티어링 = **서브에이전트 frontmatter(plan/eval) + settings 세션 baseline(dev 루프)** 2층이다. `model_policy.py set <tier>` 는 전자를 하고, 후자는 `--with-session-baseline` 로 함께 설정할 수 있다 (선택). 후자를 빼면 dev 루프는 항상 세션 모델(대개 풀 모델)로 돈다는 점을 인지할 것.

> named preset(예: `max`/`mid`/`lite`)은 위 high/med/low 위의 별칭일 뿐이다. 필요하면 얇은 래퍼로 둘 수 있으나 킷 기본은 tier 명이다.

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

## 2층 방어 - tools 화이트리스트 + permissionMode

tools 화이트리스트만으로는 구멍이 남는다 - Write 를 빼도 **Bash heredoc/리다이렉션** (`cat > file <<EOF`, `echo ... > file`) 으로 파일을 쓸 여지가 있다. 그 위에 `permissionMode` 를 얹는 게 2층 방어다:

1. **사후 평가자 (eval 계열) 에 한해** frontmatter 에 `permissionMode: plan` 을 추가한다 (공식 권장 패턴 - built-in Plan 에이전트와 동일 구성).
2. plan 모드에서 도구 쓰기(Edit/Write)는 막히므로 **result 는 YAML 텍스트로 반환**하고 **메인 세션이 `<task_dir>/*.result` 로 저장** - 역할 분담.
3. 빌드/테스트 등 셸 실행은 `settings.local.json` 의 allow 화이트리스트를 따른다 (평가 기능은 유지).
4. **사전 계획자 (plan 계열) 에는 적용하지 않는다** - tasks/ 하위 Write (plan.md / tasklist.md) 가 필요하기 때문.

### permissionMode 근거 상태 (정직하게)

이 절은 예전에 "permissionMode: plan 을 병행하면 **Bash heredoc/리다이렉션 경유 쓰기까지 차단된다 → 자기 PASS 조작이 구조적으로 차단**"이라고 **단언**했다. 그 단언에는 근거가 없었다. 실제 상태는 이렇다:

| 주장 | 상태 |
|---|---|
| `tools` 에서 Edit/Write 를 빼면 그 도구를 못 쓴다 | **확인됨** - 도구가 목록에서 사라짐 |
| `permissionMode: plan` 은 "reads only, doesn't edit your source files" | **확인됨** (공식 permission-modes 문서) |
| 읽기 전용 Bash(`git log`·`status`)는 plan 모드에서 프롬프트 없이 실행된다 | **확인됨** (문서 + 실측) |
| `disallowedTools` + `permissionMode` 조합이 공식 권장 패턴이다 | **확인됨** (built-in Plan 에이전트 동일 구성) |
| **`echo > file` 같은 Bash 경유 쓰기가 서브에이전트에서 실제 차단된다** | **미확인** - 공식 문서는 리다이렉트가 권한 프롬프트를 띄운다고만 하고, **서브에이전트에서 그 프롬프트가 어떻게 처리되는지(자동 거부/대기/오류)는 명시하지 않는다** |

→ **"Bash 경유 쓰기까지 막힌다"고 단정하지 말 것.** 이 구성이 지키는 것은 "**에이전트가 파일을 쓰려 하지 않는다**"(규율 + 도구 부재)이지 "**물리적으로 쓸 수 없다**"가 아니다. 확실히 막고 싶다면 `permissionMode: dontAsk`("Auto-deny permission prompts", 공식 문서)가 후보이나 **미검토**다. 이 근거 상태를 부트스트랩된 프로젝트에 거짓 확신으로 전파하지 않기 위해 여기 명시한다.

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

**없음** + `permissionMode: plan` (2층 방어 - 근거 상태는 위 "permissionMode 근거 상태" 참조). result 는 파일로 쓰지 않고 아래 YAML 을 **최종 텍스트 응답에 그대로 포함**한다. 메인 세션이 `<task_dir>/<project>.result` 로 저장:

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

## 선택 패턴 - sync_brain 을 서브에이전트로

기본값은 `/sync_brain` = **메인세션 슬래시 커맨드**다 (04_ssot_brain_state.md). 대부분의 단일 프로젝트에는 이걸로 충분하다. 다만 **모델 티어링을 sync 까지 걸거나 컨텍스트를 격리하고 싶으면** plan/eval 처럼 **디스패처+서브에이전트**로 둘 수 있다.

**plan/eval 과 격리 이유가 다르다**는 점을 명확히 할 것:
- plan/eval 은 **셀프 PASS 차단**(자기 작업을 자기가 PASS 못 하게)이 목적.
- sync_brain 은 판정을 하지 않으므로 셀프 PASS 위험이 **없다**. 여기 이유는 ① **컨텍스트 격리**(프로젝트가 크거나 여러 개면 sync 가 컨텍스트를 많이 먹음) ② **모델 티어링 완전화**(커맨드 frontmatter model 은 턴 한정 → 서브에이전트라야 실행 전체를 지배).

**쓰기를 주지 않는다** - 갱신 내용을 **PATCH 로 반환**하고 메인세션이 Edit 로 적용한다 (plan/eval 이 result 를 텍스트로 반환하는 것과 동형). BRAIN 은 "읽어낸 사실만, 추측 금지"라 메인세션이 diff 를 보게 하는 게 안전하다.

```
--- PATCH n ---
file: .agent/context/<PROJECT>_STATE.md
anchor: §2 git 저장소
evidence: git rev-parse --short HEAD -> a1b2c3d   # 값을 어디서 얻었는지 (근거 없는 패치 금지)
old:  <Read 로 확인한 verbatim 원문 - 파일 내 유일해야 함>
new:  <교체할 내용>
```

예산(예: 패치 40개 / 400줄)을 넘길 파일은 `--- HANDOFF ---` (file / reason / facts / instruction)로 넘겨 메인세션이 직접 Read 후 갱신한다. frontmatter 는 plan 계열처럼 Edit/Write 제외 + `permissionMode: plan`, tools 는 `Read, Glob, Grep, Bash, TaskList` (git 조회에 Bash 필요).

**캐비엇**:
- **단일 프로젝트에선 컨텍스트 격리 이점이 약하다**(sync 대상이 작음). **기본값은 커맨드 유지**를 권한다. 티어링/격리가 실제로 필요할 때만 서브에이전트로.
- **신규 에이전트는 만든 세션에서 호출되지 않는다** - 에이전트 레지스트리가 세션 시작 시 고정되므로, sync_brain 을 서브에이전트로 새로 만든 세션에서는 `Agent type 'sync_brain' not found` 가 난다. **재시작 후** 사용/검증한다.
- 옵션 자산: `templates/agents/sync_brain.md.template`. 커맨드(`templates/commands/sync_brain.md.template`)를 디스패처로 축소(`subagent_type=sync_brain` 호출만)해야 짝이 맞는다.

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
