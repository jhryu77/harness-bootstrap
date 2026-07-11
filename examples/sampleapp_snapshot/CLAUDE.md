# sampleapp - Claude Code 프로젝트 가이드

차량용 안드로이드 SampleApp 런처. **단일 모듈** (`:app`) Android 프로젝트. 좌/우 분할 + 패널 임베드.

> 본 가이드는 Claude Code 세션이 자동 로드한다. 모든 plan / dev / eval 은 Claude Code 내부에서 완결되며 외부 IDE 핸드오버는 없다.
> 운영 매뉴얼 본체: [`.agent/HARNESS_GUIDE.md`](./.agent/HARNESS_GUIDE.md)
> 컨텍스트 SSOT: [`.agent/context/SAMPLEAPP_BRAIN.md`](./.agent/context/SAMPLEAPP_BRAIN.md) · [`.agent/context/SAMPLEAPP_STATE.md`](./.agent/context/SAMPLEAPP_STATE.md)
> 통신 언어: **한국어** (모든 응답 / 주석 / 문서 한글)

---

## 1. 프로젝트 개요

| 항목 | 값 |
|---|---|
| 패키지 | `com.sampleapp.launcher` |
| applicationId | `com.sampleapp.launcher` |
| 모듈 | 단일 `:app` (KMP 없음, View 시스템) |
| Java | 17 / Kotlin 2.0.21 / AGP 8.5.2 |
| compileSdk | 35 / minSdk 26 / targetSdk 35 |
| viewBinding | true |
| 분류 | 차량용 런처 (CATEGORY_HOME, landscape 고정) |

현재 Phase 진행 - `SAMPLEAPP_STATE.md` §1 참조. 1차 골격 (좌/우 분할 + 슬롯 바인딩 + 패널 임베드) 완료, 하네스 부트스트랩 진행 중.

---

## 2. 하네스 워크플로

```
일반 코드 변경:
/read_sampleapp  →  /plan_agent_sampleapp  →  /dev_sampleapp  →  /eval_agent_sampleapp  →  PASS  →  /sync_brain  →  /commit_push

OTA 릴리스 (versionCode 증분 + Storage + ota_manifests):
/plan_agent_ota_release  →  /dev_ota_release  →  [사용자 Dashboard 업로드]  →  /eval_agent_ota_release  →  [사용자 단말 "업데이트" 탭]  →  PASS  →  /sync_brain  →  /commit_push
```

| 슬래시 | 역할 | 진입 |
|---|---|---|
| `/read_sampleapp` | BRAIN/STATE 로드 + 코드 인덱스 + 다음 액션 제안 | 메인 |
| `/plan_agent_sampleapp` | 계획 수립 (서브에이전트) | plan_sampleapp |
| `/dev_sampleapp` | 코드 구현 가이드 | 메인 (Edit/Write 직접) |
| `/eval_agent_sampleapp` | 평가 (서브에이전트) | eval_sampleapp |
| `/plan_agent_harness` | 하네스 자체 변경 계획 | plan_harness |
| `/dev_harness` | 하네스 파일 편집 | 메인 |
| `/eval_agent_harness` | 하네스 무결성 평가 | eval_harness |
| `/plan_agent_ota_release` | OTA 릴리스 계획 (versionCode/release_notes/영향평가) | plan_ota_release |
| `/dev_ota_release` | OTA 빌드 + 사인 + APK 메타 + MCP INSERT (is_active=false) | 메인 |
| `/eval_agent_ota_release` | OTA 검증 (Storage 확인 + is_active 토글 + 단말 logcat + HOME 발화) | eval_ota_release |
| `/sync_brain` | SAMPLEAPP_STATE.md 갱신 | 메인 |
| `/test_sampleapp` | 수동 검증 체크리스트 | 메인 |
| `/commit_push` | git commit + push | 메인 |

`task_YYYYMMDD_HHMM/` 폴더는 `mtime 120분` 초과 시 `archive/` 로 자동 이동 (plan 진입 시).

---

## 3. CI Gate (자동 정적 검증)

`.claude/settings.local.json` 의 PostToolUse hook 이 매 `Edit|Write` 시 `ci_gate_sampleapp.py`(인터프리터 자동 감지: macOS python3/Windows python) 를 자동 호출. 정상 시 무출력. 위반 시 stderr 로 Claude 컨텍스트에 주입.

| 검사 | 위반 시 |
|---|---|
| 임시 파일 위치 (`tmp_*`/`verify_*`/`diag_*`/`check_*` 루트 직접 생성) | **FAIL** - `tmp/` 폴더에 생성 권고 |
| 시크릿 패턴 (JWT / AWS / Google API / GitHub PAT / PEM Private Key) | **WARN** - 환경변수/secrets.properties 사용 |
| Kotlin `{` `}` 매칭 (.kt/.kts) | **WARN** - 괄호 카운트 표시 |

---

## 4. 빌드 / 실행

```powershell
# Windows PowerShell
.\gradlew.bat :app:assembleDebug         # Debug APK
.\gradlew.bat :app:installDebug          # 기기/에뮬 설치
.\gradlew.bat :app:compileDebugKotlin    # 컴파일만
```

```bash
# git-bash
./gradlew :app:assembleDebug
./gradlew :app:installDebug
./gradlew :app:compileDebugKotlin
```

산출물: `app/build/outputs/apk/debug/app-debug.apk`

---

## 5. 아키텍처 / 기술 스택

- **단일 모듈 Android 앱** (KMP / Compose Multiplatform 없음)
- ConstraintLayout + **Guideline** 기반 좌/우 분할 - `splitGuideline.layout_constraintGuide_percent` 한 값으로 양쪽 동시 리사이즈
- Fragment + ViewBinding (옵션 활성, `findViewById` 와 혼용)
- SharedPreferences 영구화 (`split_ratio` + `pane_slots` 두 파일 분리)
- VirtualDisplay 호스트 + reflection `injectInputEvent` (시그너처 권한 fail-soft 의무)

자세한 클래스 책임 표는 `SAMPLEAPP_BRAIN.md` §3 참조.

---

## 6. 런처 비타협 항목

| # | 항목 | 비고 |
|---|---|---|
| 1 | `<intent-filter>` 의 `MAIN`+`HOME`+`DEFAULT`+`LAUNCHER` 4개 | 변경 = 사용자 컨펌 |
| 2 | `screenOrientation="landscape"` | 회전 허용 = 사용자 컨펌 |
| 3 | `configChanges` 8종 풀세트 (orientation\|screenSize\|screenLayout\|keyboardHidden\|navigation\|uiMode\|density\|smallestScreenSize) | Activity 재생성 방지 |
| 4 | `launchMode="singleTask"` + `stateNotNeeded="true"` | 홈키 빠른 복귀 |
| 5 | `resizeableActivity="false"` | 멀티윈도우 분리 방지 |
| 6 | `AppPickerActivity.exported="false"` | 외부 임의 호출 차단 |
| 7 | 시그너처 권한 4종 (`CAPTURE_VIDEO_OUTPUT` / `INTERNAL_SYSTEM_WINDOW` / `INJECT_EVENTS` / `MANAGE_ACTIVITY_TASKS`) | 추가/제거 = 사용자 컨펌. fail-soft try-catch 의무 |
| 8 | 자기 자신 picker 제외 (`InstalledApps` 의 `selfPkg` 필터) | 재귀 임베드 방지 |

---

## 7. 분할 / Prefs 비타협 항목

| # | 항목 | 비고 |
|---|---|---|
| 1 | `MIN_PERCENT 0.20` / `MAX_PERCENT 0.80` / `DEFAULT_PERCENT 0.70` 상수 | 동시 변경 금지. `MainActivity.companion` 만 SSOT |
| 2 | 비율 적용 시 `coerceIn(MIN_PERCENT, MAX_PERCENT)` 호출 | 클램프 누락 = FAIL |
| 3 | `layout_constraintGuide_percent` (0.0~1.0) | dp 절대값 사용 금지 |
| 4 | SharedPreferences 파일 분리 (`split_ratio` ↔ `pane_slots`) | 혼재 금지 |
| 5 | `PaneSlot` enum 순서 / `storageKey` 변경 금지 | 영구화 호환성 (마이그레이션 필요 시 별도 task) |
| 6 | Picker 그리드 column = 6 | 차량 1280~1920px 가정. 변경 시 plan.md 근거 |
| 7 | DividerHandle 24dp / DividerVisual 4dp 분리 | 터치 영역 vs 시각 영역 |
| 8 | `VIRTUAL_DISPLAY_FLAG_TRUSTED = 1 shl 5 = 32` | 매직 넘버는 의미 주석 동반 |

---

## 8. 디렉토리 배치 규칙

```
app/src/main/java/com/sampleapp/launcher/
├── data/                  AppEntry / InstalledApps / PaneSlot / PaneSlotPrefs
├── ui/
│   ├── SplitRatioPrefs.kt (top of ui/)
│   ├── pane/              PaneFragment / PaneAppHost
│   └── picker/            AppPickerActivity / AppListAdapter
└── MainActivity.kt        (top of launcher/)

app/src/main/res/
├── layout/                activity_main / activity_app_picker / fragment_pane / view_pane_empty / item_app_grid
├── drawable/              bg_divider_handle / ic_close / ic_launcher_*
└── values/                colors / strings / themes
```

- `app/src/main` 루트에 `.kt` 직접 생성 금지 - 반드시 `java/com/sampleapp/launcher/` 하위
- 임시 / 실험 파일은 `tmp/` 만 (CI Gate 가 루트 직접 생성 차단)
- 서브에이전트 산출물은 `.agent/tasks/task_*/` 하위만

---

## 9. 참조 문서

- 운영 매뉴얼: `.agent/HARNESS_GUIDE.md`
- 불변 SSOT: `.agent/context/SAMPLEAPP_BRAIN.md`
- 시점 SSOT: `.agent/context/SAMPLEAPP_STATE.md`
- 빌드: `gradle/libs.versions.toml` · `app/build.gradle.kts`

외부 SSOT / sibling 프로젝트 / 원격 API **없음** (자기 완결).

---

## 10. 커밋 규칙

- **`Co-Authored-By:` 라인 금지** (사용자 선호. `/commit_push` 가 자동 생략)
- 자동 스테이징 금지: `*.keystore` `*.jks` `*.p12` `.env` `.env.*` `local.properties` `.agent/tasks/sampleapp.*` `tmp/`
- 커밋 메시지: `<type>: <한글 요약>` (`type` ∈ `추가|갱신|수정|리팩터|테스트|문서`)
- 메시지는 **why** 중심 1~2줄. **what** 은 diff 가 보여준다
- main / master 로의 force push 는 사용자 명시 요청 시에만
