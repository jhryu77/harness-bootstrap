# 07. task 라이프사이클

> 모든 작업이 `task_<TS>_<slug>/` 폴더에 영구 기록된다. 120분 mtime 초과 시 archive 자동 이동.

---

## 폴더 명명 규칙

```
.agent/tasks/
├── task_20260512_2038_phase_z_mac_validation/    ← 활성
├── task_20260512_2122_harness_onboarding_kit/    ← 활성
├── archive/                                ← 120분 초과 자동 이동
│   ├── task_20260511_2126_store_verification/
│   ├── task_20260511_2242_companion_a11y_apk/
│   └── ...
```

명명 규칙: `task_<YYYYMMDD>_<HHMM>_<slug_with_underscores>`

| 부분 | 의미 |
|---|---|
| `task_` | 고정 prefix |
| `YYYYMMDD_HHMM` | KST 기준 plan 시작 시각 |
| `<slug>` | 영문 + underscore, 짧고 의미있는 (예: `phase_z_mac_validation`) |

하네스 자체 변경은 `task_harness_<TS>_<slug>` 처럼 한 단계 더 prefix 를 둔다.

---

## 폴더 내용 표준

```
task_<TS>_<slug>/
├── plan.md             plan_agent 가 작성 - frontmatter(status/tier) + 변경 범위 / 영향 평가 / 변경 순서 / 리스크
├── tasklist.md         plan_agent 가 작성 - 체크박스 형식 실행 단위
└── <project>.result    eval 반환 YAML 을 메인 세션이 저장 - PASS/FAIL + 근거
```

상황에 따라 추가 파일:
- `analysis_report.md` - 사전 분석이 큰 경우 별도 분리
- `handoff_<env>.md` - 다른 환경/사람에게 인계 (예: Mac → Windows 핸드오프)
- `notes.md` - 작업 중 발견 사항

result 는 eval 에이전트가 **YAML 텍스트로 반환**하고 **메인 세션이 파일로 저장**한다 (eval 은 Write 없음 + permissionMode: plan 이중 봉쇄). 형식:

```yaml
status: PASS
task: <TS>_<slug>
checked_at: 2026-05-12T20:55:00+09:00
ac_pass: "5/5"  # plan.md 의 수용 기준 (Binary AC) 표 대조 결과
checks:
  - name: ac_table
    result: PASS
    evidence: "AC-1~5 모두 pass 조건 일치 (명령별 exit code 0)"
  - name: build_compile
    result: PASS
    evidence: "BUILD SUCCESSFUL in 9s (exit 0)"
  - name: tasklist_completion
    result: PASS
    evidence: "12/12 체크박스 완료 (tasklist.md)"
  - name: launcher_intent_filter
    result: PASS
    evidence: "AndroidManifest.xml:L23 intent-filter 4종 확인"
  - name: split_ratio_consts
    result: PASS
    evidence: "Constants.kt:L12 MIN/MAX/DEFAULT 불변"
  - name: prefs_keys
    result: PASS
    evidence: "grep 결과 인용"
notes:
  - "..."
follow_up:
  - "vd_create_ok 후속 분석 task 권장"
```

---

## status 필드 - 활성/완료 판정의 SSOT

plan.md frontmatter 에 `status: active | done` 을 둔다. plan_agent 가 생성 시 `active` 로 시작하고, eval PASS + 사용자 확정 후 **메인 세션이** `done` 으로 변경한다 (eval 은 Write 없음 - 직접 바꿀 수 없음). frontmatter 에는 `tier` 필드도 함께 선언한다 (`03_workflow_patterns.md` 의 Tier 소절 참조).

archive 판정은 status 가 1순위 - mtime 120분 기준은 status 미도입 폴더를 위한 fallback 이다.

---

## 라이프사이클 4단계

```
[1] plan_agent 진입
       │  - 진입 시 archive 자동 실행 (mtime +120 초과 폴더 이동)
       │  - 새 task_<TS>_<slug>/ 폴더 생성
       │  - plan.md + tasklist.md 작성
       ▼
[2] dev 단계 (메인 세션)
       │  - tasklist 체크박스 진행
       │  - 필요 시 plan.md 보강 (메인 세션 권한)
       ▼
[3] eval_agent 진입
       │  - tasklist 완료율 확인
       │  - 빌드/테스트/외부 검증 실행
       │  - result YAML 텍스트 반환
       ▼
[4] 사용자 확정
       │  - 메인 세션이 result 저장 (<project>.result)
       │  - PASS → 메인 세션: plan.md status → done
       │  - PASS → /sync_brain → /commit_push
       │  - FAIL → 원인 분석 후 추가 plan or dev 진입
       ▼
(120분 후) archive/ 자동 이동
```

---

## archive 자동화

**권장**: `python .agent/scripts/archive_tasks.py --apply` (status: done 이동 + frontmatter 없는 폴더만 mtime fallback 이동 - status: active 는 절대 이동 없음. dry-run 기본, 선택 자산)

fallback (mtime 기준 - status 미도입 프로젝트): `/plan_agent_<project>` 또는 `/plan_agent_harness` 슬래시 진입 시 아래 명령을 첫 단계로 실행:

```bash
find .agent/tasks -maxdepth 1 -type d -name "task_*" -mmin +120 \
  -exec mv {} .agent/tasks/archive/ \;

find .agent/tasks -maxdepth 1 -type d -name "task_harness_*" -mmin +120 \
  -exec mv {} .agent/tasks/archive/ \;
```

PowerShell 등가:

```powershell
Get-ChildItem .agent/tasks -Directory -Filter 'task_*' |
  Where-Object { $_.LastWriteTime -lt (Get-Date).AddMinutes(-120) } |
  Move-Item -Destination .agent/tasks/archive/

Get-ChildItem .agent/tasks -Directory -Filter 'task_harness_*' |
  Where-Object { $_.LastWriteTime -lt (Get-Date).AddMinutes(-120) } |
  Move-Item -Destination .agent/tasks/archive/
```

`-mmin +120` 은 mtime 120분 초과. dev 중에 plan.md 가 갱신되면 mtime 도 갱신되므로 활성 작업은 영향 없음.

archive 후에도 폴더 내용은 보존 (필요 시 다시 꺼낼 수 있음).

---

## 왜 120분인가

- 너무 짧으면 (예: 30분) - 잠시 자리 비운 사이 활성 작업이 archive 됨
- 너무 길면 (예: 1일) - 완료된 task 가 tasks/ 에 너무 많이 쌓여서 인덱스 가독성 떨어짐
- **2시간** 이 한 task 의 평균 완료 시간 (plan + dev + eval + 컨펌) 의 약 2배. 안전 마진.

프로젝트 특성에 따라 조정 가능 (긴 빌드 / 외부 검증 많은 프로젝트는 240분 등).

status enum 도입 시 120분 은 fallback 전용이 된다 - 활성 task 를 잘못 치우는 mtime 오동작의 근본 해법은 status 기준 판정.

---

## 활성 task 가 너무 많이 쌓이면

`ls -dt .agent/tasks/task_* | head -10` 의 결과가 **계속 새 폴더만** 보이고 archive 가 안 되는 상황 - 세 가지 원인:

1. **archive 룰 자체가 빠짐** - plan_agent.md 본문에 `find ... -mmin +120 -exec mv` 가 없음
2. **archive/ 디렉토리 자체가 없음** - eval_harness 가 잡아낼 항목
3. **status: done 마킹 누락** - eval PASS 후 메인 세션이 plan.md frontmatter 를 done 으로 바꾸는 단계 빠짐

eval_harness 의 점검 항목에 `[ -d .agent/tasks/archive ]` 가 포함되어야 한다.

---

## task 폴더의 git 처리

- **plan.md / tasklist.md** - commit. 작업 기록으로 영구 보존
- **<project>.result** - commit ❌. 자동 스테이징 금지 패턴 (`.agent/tasks/*.result`) 으로 보호. 이유: result 가 시점 검증 결과 + 단말 의존이라 다른 환경에서 재현 불가
- **archive/** - commit. 과거 task 가 사라지지 않음

`.gitignore` 또는 `commit_push.md` 의 자동 스테이징 필터에 명시.

---

## 활성 task 인덱스 - STATE.md §6

`/sync_brain` 슬래시 실행 시:

```bash
ls -dt .agent/tasks/task_* 2>/dev/null | head -5
```

위 명령 결과의 폴더들에서:
- 폴더 이름 (TS + slug)
- plan.md 의 첫 5줄 (제목 + 작성 시각)
- result 파일이 있으면 status: 1줄

이 정보를 STATE.md §6 "최근 task 요약" 에 갱신.

archive 된 task 는 명시 요청 시만 (`/read_<project> 과거이력` 같은) 인덱싱.

---

## 안티패턴

| 안티패턴 | 왜 나쁜가 |
|---|---|
| task 폴더 없이 plan/dev/eval 진행 | 흔적 휘발. 6개월 후 "왜 이렇게 했더라" |
| 한 task 폴더에 plan.md 여러 번 덮어쓰기 | 변경 이력 손실. 새 task 폴더 만들기 |
| plan.md 에 시점 정보 (현재 git HEAD 등) 모두 적기 | task 폴더는 작업 의도, 시점 스냅샷은 STATE |
| result 파일을 commit | 환경 의존 노이즈 / 자동 스테이징 금지 위반 |
| archive 룰 빠뜨림 | tasks/ 가 한도 없이 부풀어 가독성 폭망 |
| slug 가 너무 길거나 한글/스페이스 | 셸 처리 어려움 + 가독성 |

---

## 다음 단계

- `08_immutables.md` - 비타협 항목 정의 가이드
- `09_adapt_checklist.md` - 사람 개발자의 직접 적용 절차
