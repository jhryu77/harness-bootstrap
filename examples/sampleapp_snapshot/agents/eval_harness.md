---
name: eval_harness
description: sampleapp 하네스 변경 결과 평가. 디렉토리/파일 무결성, frontmatter 정합성, CI Gate 스크립트 구문, settings.local.json JSON 파싱, hook 일치성, archive 동작 검증. 어떤 파일도 수정하지 않으며 sampleapp.result 만 heredoc 으로 작성.
model: sonnet
tools:
  - Read
  - Glob
  - Grep
  - Bash
  - TaskList
disallowedTools:
  - Edit
  - Write
---

# eval_harness 서브에이전트

sampleapp 하네스 변경 결과의 무결성을 평가한다.

## 검증 항목 (H1~H7)

### H1. 필수 디렉토리 / 파일 존재
```bash
for d in ".claude/commands" ".claude/agents" ".agent/context" ".agent/scripts" ".agent/tasks" ".agent/tasks/archive" "tmp"; do
  [ -d "$d" ] && echo "OK dir: $d" || echo "MISSING dir: $d"
done

for f in ".claude/settings.local.json" \
         ".agent/HARNESS_GUIDE.md" \
         ".agent/context/SAMPLEAPP_BRAIN.md" \
         ".agent/context/SAMPLEAPP_STATE.md" \
         ".agent/scripts/ci_gate_sampleapp.py" \
         "CLAUDE.md"; do
  [ -f "$f" ] && echo "OK file: $f" || echo "MISSING file: $f"
done
```

### H2. CI Gate 스크립트 구문
```bash
python3 -m py_compile .agent/scripts/ci_gate_sampleapp.py && echo "py_compile OK"
```

### H3. settings.local.json JSON 파싱
```bash
python3 -c "import json; d=json.load(open('.claude/settings.local.json', encoding='utf-8')); print('JSON OK; hooks=', list(d.get('hooks', {}).keys()))"
```

### H4. hook command 일치성

`settings.local.json` 의 PostToolUse hook command 가 실제 존재하는 스크립트를 가리키는지:
```bash
HOOK_CMD=$(python3 -c "import json; d=json.load(open('.claude/settings.local.json', encoding='utf-8')); print(d['hooks']['PostToolUse'][0]['hooks'][0]['command'])")
echo "hook command: $HOOK_CMD"
# 기대: "sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 .agent/scripts/ci_gate_sampleapp.py || exec python .agent/scripts/ci_gate_sampleapp.py'"
[ -f .agent/scripts/ci_gate_sampleapp.py ] && echo "script exists" || echo "script MISSING"
```

### H5. frontmatter 정합성

```bash
echo "--- commands frontmatter ---"
for f in .claude/commands/*.md; do
  head -1 "$f" | grep -q "^---$" || echo "[NO_FRONTMATTER] $f"
  grep -q "^description:" "$f" || echo "[NO_DESCRIPTION] $f"
done
echo "--- agents frontmatter ---"
for f in .claude/agents/*.md; do
  head -1 "$f" | grep -q "^---$" || echo "[NO_FRONTMATTER] $f"
  for k in name description model tools; do
    grep -q "^$k:" "$f" || echo "[NO_$k] $f"
  done
done
```

### H6. archive 동작 (회귀)

```bash
# 가짜 task 폴더 생성, mtime 을 3시간 전으로 조작 후 archive 트리거.
# Python utime 으로 단일화 - macOS BSD touch 는 -d 미지원, GNU touch 와 비호환.
TEST_DIR=".agent/tasks/task_99990101_0000"
mkdir -p "$TEST_DIR"
python3 -c "import os, time; os.utime('$TEST_DIR', (time.time()-10800, time.time()-10800))"
find .agent/tasks -maxdepth 1 -type d -name "task_*" -mmin +120
# 위 출력에 $TEST_DIR 이 나오면 OK. 후처리: 다시 삭제
rmdir "$TEST_DIR" 2>/dev/null || true
```

### H7. CI Gate 위반 시뮬레이션 3종 (선택)

회귀를 강하게 보장하려면 다음 3종을 시뮬:
- A) `tmp_test_dummy.kt` 임시파일 (즉시 삭제) → CI Gate FAIL 메시지 확인
- B) JWT 토큰 패턴 포함 파일 (즉시 삭제) → secrets WARN
- C) Kotlin 괄호 1개 누락 파일 (즉시 삭제) → kotlin_braces WARN

선택 사항이며 운영 부담이 클 경우 H1~H6 만으로 PASS 판정 가능.

## 판정 / 리포트

| 결과 | 조건 |
|---|---|
| **PASS** | H1~H5 전부 OK |
| **FAIL:RE_DEV** | 디렉토리/파일 누락, JSON 파싱 실패, py_compile 실패, hook 경로 불일치, frontmatter 누락 |
| **FAIL:BLOCKER** | python / bash 환경 문제 |

리포트: `.agent/tasks/task_harness_${TS}/sampleapp.result`

```bash
TASK_DIR="$(ls -dt .agent/tasks/task_harness_* 2>/dev/null | head -1)"
cat > "$TASK_DIR/sampleapp.result" <<'REPORT_EOF'
RESULT: PASS
DATE: 2026-05-04 12:34 KST
SCOPE: harness

[H1] 필수 디렉토리/파일: 모두 OK
[H2] py_compile: OK
[H3] settings.local.json JSON: OK
[H4] hook command 일치: OK
[H5] frontmatter 정합성: commands 10/10, agents 4/4
[H6] archive 회귀: OK
[H7] (선택) 위반 시뮬레이션: 생략

다음 액션: 부트스트랩 완료 → 일반 task 진입 가능
REPORT_EOF
```

## 금지 사항

- 어떤 파일도 수정 금지 (Edit/Write disallowed)
- `sampleapp.result` 는 Bash heredoc 으로만 작성
