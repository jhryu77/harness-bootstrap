# 09. 다른 프로젝트에 적용하기 - 체크리스트

> 클로드 자동화 (BOOTSTRAP_PROMPT) 대신 **사람 개발자가 수동으로** 자기 프로젝트에 적용할 때의 절차.
> 클로드 자동 적용은 BOOTSTRAP_PROMPT.md 참조.

---

## 사전 결정

작업 시작 전 다음 5가지를 결정한다 (BOOTSTRAP_PROMPT 가 자동 분석하는 것을 사람이 직접 수행):

| # | 항목 | 예시 (sampleapp) |
|---|---|---|
| 1 | **프로젝트 슬러그** | `sampleapp` (소문자, 짧고, 슬래시 커맨드에 들어갈 이름) |
| 2 | **응답 언어** | `한국어` |
| 3 | **기술 스택** | `Android / Kotlin / Gradle / ConstraintLayout` |
| 4 | **배포 워크플로 필요 여부** | 있음 (OTA via Supabase) |
| 5 | **Co-Authored-By 정책** | 금지 |

이 5가지가 정해지면 템플릿 치환이 직선적이다.

---

## 적용 절차 - 9단계

### 단계 1 - 디렉토리 구조 생성

```bash
cd <your_project_root>
mkdir -p .claude/commands .claude/agents
mkdir -p .agent/context .agent/scripts .agent/tasks/archive
```

### 단계 2 - CLAUDE.md 작성

`templates/CLAUDE.md.template` 복사 후 플레이스홀더 치환:
- `{{PROJECT}}` → `sampleapp`
- `{{PROJECT_TITLE}}` → `SampleApp`
- `{{STACK}}` → `Android / Kotlin / Gradle`
- `{{LANGUAGE}}` → `한국어`
- `{{COAUTHORED_BY}}` → `금지`
- `{{COMMIT_TYPE_LIST}}` → `추가|갱신|수정|리팩터|테스트|문서`
- `{{IMMUTABLES_SECTION}}` → (08 가이드 따라 작성)

체크:
- [ ] 길이 200줄 이하
- [ ] 빌드 / 실행 명령어 정형구 포함
- [ ] 비타협 항목 표 (8개 이내)
- [ ] BRAIN.md / STATE.md / HARNESS_GUIDE.md 포인터

### 단계 3 - BRAIN.md / STATE.md 작성

`.agent/context/<PROJECT>_BRAIN.md` 작성:
1. 제품 요약 표
2. 모듈 디렉토리 트리 (`find . -maxdepth 3 -type d` 결과 정리)
3. 핵심 클래스/엔드포인트 책임 표
4. 영구화 키 인벤토리 (없으면 비워두고 향후 추가)
5. 빌드 / 의존성 표
6. 시스템 권한 (있는 경우)
7. 시스템 진입점 (라우트 / intent-filter)
8. 빌드 커맨드 정형구
9. 영역별 비타협 (분할 / 인증 / Picker 등)

`.agent/context/<PROJECT>_STATE.md` 작성:
1. 현재 Phase 상태 (첫 행은 보통 "✅ 하네스 부트스트랩")
2. git 저장소 시점값
3. 빌드 구성 현 시점
4. 구현 화면 목록 (있으면)
5. 시스템 권한 환경 가정
6. 최근 task 요약 (비어 있음)
7. 메타

### 단계 4 - HARNESS_GUIDE.md 작성

`.agent/HARNESS_GUIDE.md` - 운영 매뉴얼. 다음 섹션:
- 슬래시 커맨드 표 (전체 12종 매핑)
- 서브에이전트 역할 표 (plan/eval 별 권한)
- task 폴더 명명 규칙 + archive 룰
- CI Gate 검사 항목
- 자주 묻는 질문 (예: "task 가 archive 됐는데 다시 꺼낼 수 있나?" "BRAIN 갱신 절차는?")

### 단계 5 - 슬래시 커맨드 작성

`.claude/commands/` 에 다음 .md 파일 작성 (전부 frontmatter `description:` 필요):

표준 7종 (배포 워크플로 없는 프로젝트):
- `read_<project>.md`
- `plan_agent_<project>.md`
- `dev_<project>.md`
- `eval_agent_<project>.md`
- `sync_brain.md`
- `commit_push.md`
- `test_<project>.md` (선택)

하네스 자체 3종:
- `plan_agent_harness.md`
- `dev_harness.md`
- `eval_agent_harness.md`

배포 워크플로 있는 프로젝트는 추가 3종:
- `plan_agent_<release>.md`
- `dev_<release>.md`
- `eval_agent_<release>.md`

각 슬래시 커맨드의 본문 구조: "역할 + 절차 + 출력 포맷 + 비타협 점검 항목 + 다음 단계".

### 단계 6 - 서브에이전트 작성

`.claude/agents/` 에 다음 .md 파일 작성 (frontmatter `name + description + tools + model` 4키 필수):

표준 4종 + 배포 시 2종:
- `plan_<project>.md`
- `eval_<project>.md`
- `plan_harness.md`
- `eval_harness.md`
- `plan_<release>.md` (선택)
- `eval_<release>.md` (선택)

frontmatter 의 `tools` 화이트리스트는 **05_subagent_design.md** 표 따라 좁힌다.

(선택) 에이전트별 model 을 역할에 맞게 차등화하고 싶다면 templates/scripts/model_policy.py 를 복사해 set <tier> 실행 - 05_subagent_design.md §모델 정책 참조.

### 단계 7 - CI Gate 작성

`.agent/scripts/ci_gate_<project>.py` 작성 (06_ci_gate.md 의 표준 골격 사용).

언어별 검사 함수 1개 추가 (Kotlin braces / Python ast / TS regex 등).

직접 호출 테스트:
```bash
echo "test" > tmp_test.txt
python3 .agent/scripts/ci_gate_<project>.py tmp_test.txt
# → "임시 파일 prefix(tmp_*)..." stderr 출력 확인
rm tmp_test.txt
```

### 단계 8 - settings.local.json 작성

`.claude/settings.local.json` 작성. 핵심 3구역:

```json
{
  "permissions": {
    "allow": [
      "Bash(git:*)",
      "Bash(<build_tool>:*)",
      "Bash(python:*)",
      "Bash(python3:*)",
      "Read(<your_project_root>/**)",
      ...
    ]
  },
  "enableAllProjectMcpServers": true,
  "hooks": {
    "PostToolUse": [{
      "matcher": "Edit|Write",
      "hooks": [{
        "type": "command",
        "command": "sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 .agent/scripts/ci_gate_<project>.py || exec python .agent/scripts/ci_gate_<project>.py'"
      }]
    }]
  }
}
```

permissions.allow 는 자기 프로젝트의 빌드 도구 / SDK / 외부 의존에 맞춰 추가. 단 **절대 경로는 OS/사용자 의존** 하므로 가능하면 상대 경로 사용.

### 단계 9 - 상태바(statusLine) 설치 [필수]

Claude Code 전역 상태바(모델/폴더/git + 컨텍스트·5H·7D 사용률·reset 카운트다운)는 하네스 적용 시 **필수**다 — 세션 예산 가시성이 워크플로 판단 근거.

- `templates/statusline.py` → `~/.claude/statusline.py` 복사 (플레이스홀더 치환 불필요).
- `~/.claude/settings.json` 의 `statusLine.command` 에 **감지형**으로 등록(`<HOME>` 는 실제 홈 경로):

```json
"statusLine": { "type": "command", "command": "sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 <HOME>/.claude/statusline.py || exec python <HOME>/.claude/statusline.py'", "padding": 0, "refreshInterval": 60 }
```

bare `python <HOME>/.claude/statusline.py` 는 macOS(python 부재)에서 상태바가 안 뜬다 — 감지형 필수. `refreshInterval: 60`(초=1분)으로 유휴에도 갱신. 모델 옆 `[high]` = 현재 `/effort` 상태. `~/.claude/`(전역)라 프로젝트마다 재설치는 불필요.

---

## 검증

전부 작성 후:

```bash
# CI Gate 컴파일
python3 -m py_compile .agent/scripts/ci_gate_<project>.py && echo "py_compile OK"

# JSON 파싱
python3 -c "import json; json.load(open('.claude/settings.local.json', encoding='utf-8')); print('JSON OK')"

# frontmatter 점검
for f in .claude/commands/*.md; do
  head -1 "$f" | grep -q "^---$" || echo "[NO_FRONTMATTER] $f"
  grep -q "^description:" "$f" || echo "[NO_DESCRIPTION] $f"
done

for f in .claude/agents/*.md; do
  for k in name description model tools; do
    grep -q "^$k:" "$f" || echo "[NO_$k] $f"
  done
done

# 디렉토리 무결성
for d in .claude/commands .claude/agents .agent/context .agent/scripts .agent/tasks/archive; do
  [ -d "$d" ] || echo "[MISSING] $d"
done
```

모두 통과해야 하네스가 작동.

---

## 첫 실험

작은 작업 1개로 4단계 워크플로 전체를 돌려본다:

1. Claude Code 진입 → CLAUDE.md 자동 로드 확인
2. `/read_<project>` 호출 → BRAIN/STATE 읽기 확인
3. `/plan_agent_<project> 사소한 추가` → task 폴더 + plan.md / tasklist.md 생성 확인
4. `/dev_<project>` → 1 파일 편집 → CI Gate hook stderr 무반응 확인
5. `/eval_agent_<project>` → result 파일 생성 확인
6. `/sync_brain` → STATE.md §6 갱신 확인
7. `/commit_push` → 자동 스테이징 필터 적용 확인 (tasks/*.result 미포함)

7단계가 모두 깔끔히 돌면 하네스 부트스트랩 완료.

---

## 자주 묻는 질문 (FAQ)

### Q1. CLAUDE.md 가 200줄을 넘어요

- 비타협 항목 표가 길어졌다면 카테고리별 분할 → BRAIN.md 로 옮김
- 빌드 명령어 정형구가 길다면 HARNESS_GUIDE.md 로 옮김
- 산문이 있다면 표로 변환
- CLAUDE.md 는 "매 세션 자동 로드" 라는 비용을 의식

### Q2. 슬래시 커맨드가 너무 많아요

표준 7종이 핵심. `/test_<project>` 같은 선택 슬래시는 빼도 OK. 단 plan/dev/eval 3종은 빼지 말 것.

### Q3. 서브에이전트의 tools 화이트리스트가 부담스러워요

`tools: *` 처럼 풀어두면 안전망이 사라진다. 처음엔 좁게 시작하고 (Read, Glob, Grep, Bash, Write, TaskList) 작업하면서 필요한 도구가 발견되면 추가. 처음부터 모두 열어두지 말 것.

### Q4. CI Gate 가 false positive 를 너무 많이 발생

- 임시 파일 prefix 패턴이 정상 파일과 겹친다면 패턴 축소 (`tmp_` 같이 underscore 까지 포함하면 일반 변수명 충돌은 거의 없음)
- 시크릿 패턴이 테스트 더미 키와 겹친다면 테스트 파일 경로 화이트리스트 추가 (예: `if "/tests/" in path: return None`)

### Q5. archive 가 활성 작업까지 잡아갑니다

- dev 중에 plan.md 를 한 번이라도 갱신하면 mtime 도 갱신되어 archive 안 됨
- 그래도 잡힌다면 `-mmin +240` (4시간) 으로 늘림
- 또는 plan 진입 시 archive 룰을 사용자 컨펌 후 실행하도록 변경

### Q6. 다른 repo 와의 인터페이스 어떻게 관리

각 repo 가 자체 BRAIN.md 의 §10 "참조 / 외부 의존" 에 다른 repo 인터페이스를 명시. 두 repo 동시 수정이 필요한 작업은 **각 repo 의 plan_agent** 를 따로 진입 (cross-write 단독 수행 금지).

### Q7. GLM(z.ai) 같은 외부 모델을 병행하고 싶어요

templates/scripts/glm_mode.py 참조 (실험적, opt-in). tmux 새 창에 GLM 라우팅 Claude Code 를 띄워주는 수동 유틸리티일 뿐 자동 위임이 아니다. 06_ci_gate.md §GLM 병행 확인.

---

## 다음 단계

- `BOOTSTRAP_PROMPT.md` - 위 9단계를 클로드가 자동 수행하도록 설계된 프롬프트
- `examples/sampleapp_snapshot/` - sampleapp 하네스 풀 구성 예시
- `examples/case_study.md` - sampleapp 종단 시나리오 1건
