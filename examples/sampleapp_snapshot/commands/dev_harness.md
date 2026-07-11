---
description: sampleapp 하네스 자체 편집 가이드 (.claude/, .agent/, CLAUDE.md)
---

# /dev_harness

`plan_harness` 가 작성한 `task_harness_${TS}/plan.md` + `tasklist.md` 에 따라 하네스 파일을 직접 편집한다.

## 편집 대상

- `.claude/commands/*.md`
- `.claude/agents/*.md`
- `.claude/settings.local.json`
- `.agent/scripts/*.py`
- `.agent/context/*.md`
- `.agent/HARNESS_GUIDE.md`
- `CLAUDE.md`

**제외**: `app/src/...` (코드)는 절대 다루지 않는다.

## 자체 검증 (편집 후 즉시)

```bash
# CI Gate 스크립트 구문
python3 -m py_compile .agent/scripts/ci_gate_sampleapp.py && echo "py_compile OK"

# settings.local.json JSON 파싱
python3 -c "import json; json.load(open('.claude/settings.local.json', encoding='utf-8')); print('JSON OK')"

# frontmatter 정합성 (commands)
for f in .claude/commands/*.md; do
  head -1 "$f" | grep -q "^---$" || echo "[NO_FRONTMATTER] $f"
  grep -q "^description:" "$f" || echo "[NO_DESCRIPTION] $f"
done

# frontmatter 정합성 (agents)
for f in .claude/agents/*.md; do
  for k in name description model tools; do
    grep -q "^$k:" "$f" || echo "[NO_$k] $f"
  done
done
```

## 비타협 항목

- PostToolUse hook command 변경 시 → 즉시 회귀 검증 (CI Gate 위반 시뮬 3종)
- 권한 화이트리스트 축소 시 → 기존 동작 회귀 가능성 plan.md 에 명시
- BRAIN 의 SharedPreferences 키 인벤토리 변경 시 → 코드 마이그레이션 작업도 plan_sampleapp 로 별도 task 분리

완료 후 `/eval_agent_harness` 로 평가.
