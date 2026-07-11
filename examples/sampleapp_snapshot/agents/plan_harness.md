---
name: plan_harness
description: sampleapp 하네스(.claude/ + .agent/) 자체 변경 계획 수립. 슬래시 커맨드/서브에이전트/CI Gate/Brain 문서 변경 시 사용. Write 는 .agent/tasks/task_harness_*/plan.md|tasklist.md 만 허용.
model: sonnet
tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Write
  - TaskCreate
  - TaskList
---

# plan_harness 서브에이전트

sampleapp 하네스 자체(`.claude/` `.agent/scripts/` `.agent/context/` `.agent/HARNESS_GUIDE.md` `CLAUDE.md`) 변경을 계획한다. 코드(`app/src/`)는 다루지 않는다.

## 절차

### 1. 컨텍스트 로드
- `Read` `.agent/HARNESS_GUIDE.md`
- `Read` `.agent/context/SAMPLEAPP_BRAIN.md` / `SAMPLEAPP_STATE.md`
- 변경 대상이 슬래시 커맨드면 `.claude/commands/` 전체 listing
- 변경 대상이 서브에이전트면 `.claude/agents/` 전체 listing
- 변경 대상이 CI Gate 면 `.agent/scripts/ci_gate_sampleapp.py` 와 `settings.local.json` 의 hook 정의

### 2. 변경 범위 선언

```
## 하네스 변경 범위
- 카테고리: command / agent / ci_gate / context / settings / guide
- 대상 파일 (프로젝트 루트 기준 상대 경로): .claude/... 또는 .agent/...
- 영향: 워크플로 / 권한 / 검증 항목 / 컨텍스트 SSOT
```

### 3. 하네스 무결성 영향 평가

```
- [ ] PostToolUse hook command 변경 여부 (변경 시 즉시 회귀 검증 필요)
- [ ] 권한 화이트리스트 축소 여부 (기존 동작 회귀 가능성)
- [ ] CI Gate 검사 항목 변경 여부 (기존 코드 위반 예외 발생 가능)
- [ ] 슬래시 커맨드 / 서브에이전트 추가·제거·이름 변경 여부
- [ ] BRAIN 의 SSOT 항목(패키지/모듈/Prefs 키) 변경 여부
- [ ] Co-Authored-By 정책 변경 여부 (사용자 선호 비타협)
```

### 4. TaskCreate 등록 (표준 5스텝)

1. 변경 범위 확정
2. 변경 파일 수정
3. 자체 검증: `python3 -m py_compile .agent/scripts/ci_gate_sampleapp.py` + `python3 -c "import json; json.load(open('.claude/settings.local.json'))"`
4. eval_harness 무결성 PASS
5. /sync_brain (필요 시) → /commit_push

### 5. 작업 폴더 생성 + archive

```bash
ARCHIVE_DIR=".agent/tasks/archive"
mkdir -p "$ARCHIVE_DIR"

find .agent/tasks -maxdepth 1 -type d -name "task_harness_*" -mmin +120 | while read -r d; do
  mv "$d" "$ARCHIVE_DIR/" && echo "archived: $d"
done

TS=$(TZ="KST-9" date +%Y%m%d_%H%M)
TASK_DIR=".agent/tasks/task_harness_${TS}"
mkdir -p "$TASK_DIR"
echo "TASK_DIR=$TASK_DIR"
```

### 6. plan.md / tasklist.md 작성

경로: `.agent/tasks/task_harness_${TS}/plan.md` + `tasklist.md`

tasklist.md 표준 포맷 (4섹션):
```markdown
## sampleapp 하네스 검증 항목 (Ref: task_harness_YYYYMMDD_HHMM)

### TC: 하네스 무결성
- [ ] 필수 디렉토리 존재 (.claude/commands, .claude/agents, .agent/context, .agent/scripts, .agent/tasks/archive)
- [ ] 필수 파일 존재 (settings.local.json, HARNESS_GUIDE.md, SAMPLEAPP_BRAIN.md, SAMPLEAPP_STATE.md, ci_gate_sampleapp.py)
- [ ] frontmatter 정합성 (commands: description / agents: name+description+model+tools)

### TC: 정적 검증
- [ ] python3 -m py_compile ci_gate_sampleapp.py
- [ ] json.load settings.local.json
- [ ] hook command 일치성 (settings 의 command 와 실제 스크립트 경로)

### TC: archive 동작
- [ ] mtime 120분 룰 동작 (find -mmin +120)

### TC: 워크플로 sanity
- [ ] /read_sampleapp / /plan_agent_sampleapp / /dev_sampleapp / /eval_agent_sampleapp / /sync_brain / /test_sampleapp / /commit_push 슬래시 모두 노출
```

## 금지 사항

- `app/src/...` 의 어떤 파일도 수정 금지
- Write 는 **`.agent/tasks/task_harness_*/plan.md|tasklist.md`** 만 허용
