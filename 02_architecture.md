# 02. 하네스 아키텍처

> 원칙(01)을 어떤 **파일/디렉토리** 로 구현하는지의 청사진.

---

## 자산 3종

하네스는 **3개의 디렉토리/파일** 로 구성된다:

```
<project_root>/
├── CLAUDE.md                  ① 자동 로드 압축 가이드 (~200줄)
├── .claude/                   ② Claude Code 설정 (슬래시 + 서브에이전트 + hook)
│   ├── settings.local.json
│   ├── commands/              슬래시 커맨드 .md 모음
│   └── agents/                서브에이전트 frontmatter .md 모음
└── .agent/                    ③ 우리 자체 컨텍스트 + 스크립트 + task 보관소
    ├── HARNESS_GUIDE.md       운영 매뉴얼 본체
    ├── context/
    │   ├── <PROJECT>_BRAIN.md   저빈도 SSOT
    │   └── <PROJECT>_STATE.md   고빈도 SSOT
    ├── scripts/
    │   └── ci_gate_<project>.py  PostToolUse 정적 검증
    └── tasks/
        ├── task_<TS>_<slug>/     활성 task 폴더
        └── archive/        120분 mtime 초과 시 자동 이동
```

세 자산이 **함께 있어야** 하네스가 작동한다. 하나라도 빠지면:

| 빠진 것 | 어떤 안전망이 사라지는가 |
|---|---|
| `CLAUDE.md` | 자동 로드 압축본 부재 → 매 세션 컨텍스트 재구축 비용 |
| `.claude/settings.local.json` | PostToolUse hook 미작동 → CI Gate 무력화 |
| `.claude/commands/` | 슬래시 워크플로 부재 → 3단계 강제 깨짐 |
| `.claude/agents/` | 서브에이전트 권한 격리 부재 → 셀프 PASS 가능 |
| `.agent/context/BRAIN.md` | 저빈도 지식 휘발 |
| `.agent/context/STATE.md` | 시점 추적 불가 |
| `.agent/tasks/` | task 흔적 휘발 |
| `.agent/scripts/ci_gate_*.py` | 정적 검증 부재 → 시크릿/임시파일 무감지 |

> 스크립트 자산 (ci_gate 외 manifest/doctor/archive/pre_gate) 은 Python 표준 라이브러리만 사용하는 **선택(optional) 자산** - 문서만으로도 하네스는 완결되며, 스크립트는 검사·업데이트를 기계화할 뿐이다.

---

## 데이터 흐름 (한 task 의 라이프사이클)

```
사용자: "/plan_agent_<project> <목적>"
        │
        ▼
[plan_agent 서브에이전트]
        ├── Read .agent/context/BRAIN.md + STATE.md (자동 컨텍스트)
        ├── Read 관련 코드
        ├── Write .agent/tasks/task_<TS>/plan.md
        └── Write .agent/tasks/task_<TS>/tasklist.md
        │
        ▼
사용자: "/dev_<project>"
        │
        ▼
[메인 세션]
        ├── Read plan.md + tasklist.md
        ├── Edit/Write 코드  (← 매 호출마다 PostToolUse hook = ci_gate)
        └── tasklist 체크박스 진행
        │
        ▼
사용자: "/eval_agent_<project>"
        │
        ▼
[eval_agent 서브에이전트]
        ├── Read plan.md + tasklist.md
        ├── Bash (빌드/테스트 실행)
        └── result YAML 텍스트 반환 → 메인 세션이
            .agent/tasks/task_<TS>/<project>.result 저장 (PASS|FAIL + 근거)
        │
        ▼
사용자: 확인 → "/sync_brain"  (STATE 갱신)
            → "/commit_push" (자동 스테이징 필터 + 메시지 작성)
```

---

## CLAUDE.md 의 역할 - "압축 가이드"

매 세션 자동 로드되므로 **컨텍스트 비용** 이 매번 발생한다. 따라서 다음 원칙:

- 길이는 **~200줄 이하** (1,000줄 이상 가지 말 것)
- 내용은 모두 **표 또는 정형 목록** (산문은 BRAIN 으로)
- 동일 정보 BRAIN/HARNESS_GUIDE 와 중복되면 후자만 두고 CLAUDE.md 는 포인터
- 빌드 명령어는 짧은 코드블록 1개

CLAUDE.md 가 200줄을 넘기 시작하면 **하네스 자체 변경 (plan_harness)** 으로 정리할 시점이다.

---

## BRAIN.md vs STATE.md vs HARNESS_GUIDE.md

| 파일 | 내용 | 갱신 트리거 | 자동 로드? |
|---|---|---|---|
| `CLAUDE.md` | 워크플로 표 + 비타협 항목 + 빌드 + 커밋 규칙 | 거의 영구 (plan_harness) | ✅ |
| `<PROJECT>_BRAIN.md` | 패키지/모듈 구조 / 클래스 책임 / 키 인벤토리 / 빌드 / 권한 / 비타협 항목 / 참조 분석 | 코드 구조 변경 시 (plan_harness or sync_brain) | ❌ (read 명시 시만) |
| `<PROJECT>_STATE.md` | 현재 Phase 표 / 구현 화면 / 최근 task / 빌드 구성 시점 값 | 매 task 완료 시 `/sync_brain` | ❌ (read 명시 시만) |
| `HARNESS_GUIDE.md` | 운영 매뉴얼 (슬래시 사용법 / 서브에이전트 역할 / archive 규칙) | 워크플로 변경 시 (plan_harness) | ❌ (read 명시 시만) |

`/read_<project>` 슬래시가 BRAIN + STATE 둘 다 명시 Read 하여 세션 워밍업.

---

## settings.local.json - Claude Code 핵심 설정

3가지 구역으로 구성:

```json
{
  "permissions": { "allow": [ ... ] },   // Bash/Edit/Write 화이트리스트
  "enableAllProjectMcpServers": true,    // MCP 서버 자동 등록
  "hooks": {
    "PostToolUse": [{
      "matcher": "Edit|Write",
      "hooks": [{ "type": "command", "command": "sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 .agent/scripts/ci_gate_<project>.py || exec python .agent/scripts/ci_gate_<project>.py'" }]
    }]
  }
}
```

permissions.allow 는 프로젝트별로 다르다 (Android = adb / Next.js = npm + npx tsc / Python = pytest 등).

hook command 는 **상대 경로** 사용 (절대 경로는 OS/사용자 의존).

---

## 슬래시 커맨드 표 (표준 12종)

| 슬래시 | 단계 | 진입 |
|---|---|---|
| `/read_<project>` | 워밍업 | 메인 세션 (BRAIN/STATE Read + 코드 인덱스) |
| `/plan_agent_<project>` | plan | 서브에이전트 (plan_<project>) |
| `/dev_<project>` | dev | 메인 세션 (Edit/Write 직접) |
| `/eval_agent_<project>` | eval | 서브에이전트 (eval_<project>) |
| `/sync_brain` | 후처리 | 메인 세션 (STATE 갱신) |
| `/commit_push` | 후처리 | 메인 세션 (git 자동화) |
| `/test_<project>` | 보조 | 메인 세션 (수동 테스트 체크리스트) |
| `/plan_agent_harness` | 메타 plan | 서브에이전트 (plan_harness) |
| `/dev_harness` | 메타 dev | 메인 세션 |
| `/eval_agent_harness` | 메타 eval | 서브에이전트 (eval_harness) |
| `/plan_agent_<release>` | 배포 plan | 서브에이전트 (선택, 배포 있는 프로젝트만) |
| `/dev_<release>` / `/eval_agent_<release>` | 배포 dev/eval | (선택) |

프로젝트에 따라 배포 워크플로 3종이 빠질 수 있다 (예: 라이브러리 / SDK 프로젝트).

---

## Mono-repo vs Multi-repo 패턴

### Mono-repo (단일 repo 한 하네스)

가장 단순:

```
<root>/                ← git repo 1개
├── CLAUDE.md
├── .claude/
├── .agent/
└── (코드 모듈들)
```

sampleapp_app 가 이 패턴.

### Multi-repo (여러 repo, 각각 하네스)

같은 사용자가 여러 repo 를 운영하는 경우 **각 repo 가 자체 하네스를 가진다**:

```
workspace/
├── <client>/           ← repo 1 (예: Android client)
│   ├── CLAUDE.md
│   ├── .claude/
│   └── .agent/
├── <server>/           ← repo 2 (예: Next.js admin)
│   ├── CLAUDE.md
│   ├── .claude/
│   └── .agent/
└── <sdk>/              ← repo 3 (선택)
    └── ...
```

각 repo 의 BRAIN.md 에 **다른 repo 와의 인터페이스** (API 스펙 / 공유 시크릿 위치 / Supabase 테이블 등) 를 명시하는 섹션을 둔다.

sampleapp 의 경우 `sampleapp_app/` (Android) + `sampleapp_server/` (Next.js admin) + Supabase (외부 SaaS) 의 3-tier 구성이지만 client/server 각자 자체 하네스를 운영한다.

### Multi-repo 시 settings.local.json 권한 확장

다른 repo 의 코드를 **읽거나 편집** 해야 할 때 (예: server 측 API 변경이 client 영향 분석):

```json
"permissions": {
  "allow": [
    ...,
    "Read(/Users/.../sibling_repo/**)",
    "Edit(/Users/.../sibling_repo/**)",
    "Write(/Users/.../sibling_repo/**)"
  ]
}
```

이때 sibling_repo 의 변경은 **그 repo 의 하네스 워크플로** 를 거쳐야 한다 (단순 cross-write 가 아니라 sibling repo 에 plan/dev/eval 진입).

---

## 컨텍스트 다이어트 - 비대화 견제

살아있는 하네스의 문서는 자라기만 한다 - sampleapp 예시에서 BRAIN 이 10주 만에 30→367줄. 성장은 필연이므로 다이어트 절차를 미리 표준화한다.

트리거 (제안값, 프로젝트별 조정 가능) - 초과 시 `/plan_agent_harness` 로 분리 task:

| 대상 | 트리거 |
|---|---|
| 슬래시 커맨드 본문 | 100줄 초과 |
| BRAIN.md | 400줄 초과 |
| CLAUDE.md | 200줄 초과 |

처방 3종:

1. **thin wrapper** - 커맨드 본문은 라우팅/요약만 두고 상세 절차는 별도 문서로 분리해 필요 시 Read (지연 로드)
2. **stub+pointer** - BRAIN 의 상세 doctrine 을 별도 파일로 빼고 본문엔 1문단 요약 + See 포인터
3. **Authority References** - 권위 문서 내용을 다른 문서/커맨드에 복붙하지 않고 포인터만 (드리프트 방지, `04_ssot_brain_state.md` 참조)

---

## 다음 단계

- `03_workflow_patterns.md` - 3종 워크플로의 실제 흐름
- `04_ssot_brain_state.md` - BRAIN/STATE 작성 가이드
- `05_subagent_design.md` - 서브에이전트 frontmatter 설계
