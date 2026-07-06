---
description: SAMPLEAPP_STATE.md 갱신 + SAMPLEAPP_BRAIN.md 갱신 필요 여부 판별 → 컨펌 후 반영
---

# /sync_brain

`SAMPLEAPP_STATE.md` 의 시점 정보를 현재 코드 / git / task 상태에 맞춰 갱신하고, `SAMPLEAPP_BRAIN.md`(패키지/모듈/Prefs 키 인벤토리) 갱신이 필요한지 판별해 컨펌 후 같은 흐름에서 반영한다 - 별도 수동 절차로 미루지 않는다.

## 갱신 절차

### 1. 현황 수집

```bash
echo "=== git ==="
git rev-parse --abbrev-ref HEAD 2>/dev/null
git log --oneline -3 2>/dev/null
git status --short 2>/dev/null | head -10

echo "=== libs.versions.toml ==="
cat gradle/libs.versions.toml | head -20

echo "=== 구현 화면 ==="
find app/src/main/java -name "*.kt" | sort

echo "=== 최근 task ==="
ls -dt .agent/tasks/task_* 2>/dev/null | head -5

echo "=== 마지막 갱신 시각 ==="
TZ="KST-9" date '+%Y-%m-%d %H:%M KST'
```

### 2. SAMPLEAPP_STATE.md 업데이트 영역 (8섹션)

| 섹션 | 갱신 트리거 |
|---|---|
| §1 Phase 진행 | 새 Phase 완료 / Phase 추가 시 |
| §2 git 저장소 | 브랜치/커밋 변동 |
| §3 빌드 구성 | libs.versions.toml / app/build.gradle.kts 변동 |
| §4 구현 화면 | 신규 Activity/Fragment 추가 시 |
| §5 권한 환경 가정 | 보드 환경 변경 / 새 hidden API 사용 시 |
| §6 최근 task | 매 task 종료 시 |
| §7 메타 (날짜) | 매 sync_brain 실행 시 |

### 3. Edit 도구로 STATE.md 수정

`Read` 로 `.agent/context/SAMPLEAPP_STATE.md` 를 읽고, 각 섹션을 `Edit` 으로 갱신. (cwd=프로젝트 루트 가정)

### 4. SAMPLEAPP_BRAIN.md 갱신 필요 판별

`SAMPLEAPP_BRAIN.md` 상단 "마지막 갱신" 이후 diff 를 아래 신호와 대조:

| 신호 | 대상 섹션 |
|---|---|
| 새 Activity/Fragment/핵심 클래스 추가 | 모듈 구조 / 핵심 클래스 표 |
| 새 SharedPreferences 키 추가 (신규만, 기존 키명/타입 변경 아님) | Prefs 키 인벤토리 |
| gradle 의존성 메이저 버전업 | 빌드/의존성 |
| intent-filter 변경 | 시스템 진입점 - 비타협 위반 소지, diff 신중히 제시 |
| 새 비타협 항목 발견 | 비타협 표 |

신호 없음 → BRAIN 갱신 생략. 신호 있음 → 섹션별 현재값 vs 제안 변경을 diff 로 제시하고 사용자 승인("갱신"/"진행") 대기, 승인 시에만 Edit + "마지막 갱신" 날짜 갱신. 기존 Prefs 키의 이름/타입 변경·삭제는 범위 밖 - 마이그레이션이 필요하므로 별도 `/plan_agent_sampleapp` task.

### 5. 결과 보고

```
[sync_brain 완료]
- §1 Phase 진행: <변동 요약>
- §6 최근 task: <마지막 task 추가>
- §7 메타: 2026-MM-DD HH:MM KST 갱신
- BRAIN: 갱신 없음 | 갱신 제안 N건 (컨펌 대기) | 갱신 완료 N건
```
