---
description: sampleapp 현황 파악 - Brain/State 로드 + 코드 인덱스 + 다음 권장 액션
---

# /read_sampleapp

sampleapp 프로젝트의 현재 상태를 빠르게 파악한다.

## 절차

### 1. 컨텍스트 로드
- `Read` `.agent/context/SAMPLEAPP_BRAIN.md`
- `Read` `.agent/context/SAMPLEAPP_STATE.md`

> 슬래시 커맨드는 프로젝트 루트(cwd) 에서 실행되므로 상대 경로 그대로 사용. Mac/Windows 동일.

### 2. 코드 인덱스 + 진입 인텐트 점검 (Bash, 한 번에)

```bash
echo "=== Kotlin 소스 ==="
find app/src -name "*.kt" 2>/dev/null | sort
echo
echo "=== 레이아웃 ==="
find app/src/main/res/layout -name "*.xml" 2>/dev/null | sort
echo
echo "=== 앱 진입 인텐트 필터 ==="
grep -E "android.intent.action.MAIN|android.intent.category.LAUNCHER" app/src/main/AndroidManifest.xml || echo "MISSING"
echo
echo "=== git 최근 5개 ==="
git log --oneline -5 2>/dev/null || echo "(no git repo)"
echo
echo "=== 최근 task 폴더 ==="
ls -dt .agent/tasks/task_* 2>/dev/null | head -5 || echo "(no tasks)"
```

### 3. 출력 포맷 (메인 세션이 사용자에게)

```
## sampleapp 현재 상태

### Phase 진행
(SAMPLEAPP_STATE.md §1 표 그대로)

### 구현된 화면 / 컴포넌트
(SAMPLEAPP_STATE.md §4 표 그대로)

### SharedPreferences 키 인벤토리
- settings.pref_sort_order (String, "title"|"updated")
- settings.pref_page_size (Int, 1~100)
- sync_state.last_sync_at (Long, epoch ms)

### 앱 진입 인텐트 필터
- MAIN / LAUNCHER : (점검 결과)

### 최근 task
(목록 5개)

### 다음 권장 액션
- /plan_agent_sampleapp <목적> - 작업 계획 수립
- /sync_brain - STATE 갱신 (필요 시)
- /test_sampleapp - 수동 검증 체크리스트
```
