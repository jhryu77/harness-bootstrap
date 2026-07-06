---
description: sampleapp 런처 코드 구현 가이드 (메인 세션이 직접 수행)
---

# /dev_sampleapp

`plan_sampleapp` 가 작성한 `task_${TS}/plan.md` + `tasklist.md` 에 따라 코드를 구현한다. 메인 세션이 직접 Edit/Write 한다 (서브에이전트 호출 X).

매 Edit/Write 마다 PostToolUse hook 이 `python .agent/scripts/ci_gate_sampleapp.py` 를 자동 실행한다. stderr 로 경고가 나오면 즉시 수정.

---

## A. 런처 동작 / Manifest 변경

| 항목 | 규칙 |
|---|---|
| intent-filter 4종 | `MAIN` + `HOME` + `DEFAULT` + `LAUNCHER` 모두 보존. 변경 시 사용자 컨펌 필수 |
| screenOrientation | `"landscape"` 보존 |
| configChanges | `orientation\|screenSize\|screenLayout\|keyboardHidden\|navigation\|uiMode\|density\|smallestScreenSize` 8개 풀세트 보존 |
| launchMode | `"singleTask"` + `stateNotNeeded="true"` 보존 |
| resizeableActivity | `false` 보존 |
| allowBackup | `true` 허용 (런처는 일반 앱 - DTx 보안 미적용) |
| 시그너처 권한 4종 | `CAPTURE_VIDEO_OUTPUT` / `INTERNAL_SYSTEM_WINDOW` / `INJECT_EVENTS` / `MANAGE_ACTIVITY_TASKS` 유지. 추가/제거는 사용자 컨펌 |
| AppPickerActivity | `exported="false"` 보존 |

## B. 좌/우 분할 레이아웃 (ConstraintLayout + Guideline)

| 항목 | 규칙 |
|---|---|
| 비율 제어 | `splitGuideline.layout_constraintGuide_percent` 단일 값으로만 제어. 양쪽 패널은 가이드라인 양 끝에 0dp constraint |
| 비율 범위 | `MIN_PERCENT 0.20` ≤ percent ≤ `MAX_PERCENT 0.80`. `MainActivity.companion` 의 상수만 참조 (하드코딩 금지) |
| 클램프 | `coerceIn(MIN_PERCENT, MAX_PERCENT)` 호출 필수 |
| Divider | DividerHandle 터치 영역 24dp / DividerVisual 시각 4dp 분리 보존 |
| 호스팅 중 리사이즈 | `onSizeChanged` → `VirtualDisplay.resize()` 전파 패턴 보존 |

## C. 슬롯 데이터 / 영구화 (SharedPreferences 일관성)

| 항목 | 규칙 |
|---|---|
| 파일 분리 | `pane_slots` ↔ `split_ratio` 두 파일 혼재 금지 |
| 키 패턴 | `"${slot.storageKey}_pkg"` / `"${slot.storageKey}_cls"` (PaneSlotPrefs) / `"left_percent"` (SplitRatioPrefs) |
| PaneSlot enum | LEFT("left") / RIGHT("right") 순서·storageKey 변경 금지 |
| 슬롯 추가 (예: TOP_BAR) | `entries.firstOrNull` 순회 안정성 위해 enum 끝에 추가. BRAIN 의 키 인벤토리 동시 갱신 |
| clear → rebind | `PaneSlotPrefs.clear` 호출 후 `PaneFragment.rebindFromPrefs` 재호출로 UI 일관성 |

## D. 패널 임베드 (VirtualDisplay + Input Forward)

| 항목 | 규칙 |
|---|---|
| reflection / hidden API | `MotionEvent.setDisplayId` / `InputManager.injectInputEvent` 모두 try-catch (RuntimeException 0건) |
| TRUSTED 플래그 | `1 shl 5 = 32` 매직 넘버는 상수 + 의미 주석 보존 |
| VirtualDisplay 라이프사이클 | release ↔ create 짝. surface invalid 시 `surfaceCreated` 콜백에서 재시도 |
| dispatchTouchEvent | 호스팅 중일 때만 forward, EMPTY 상태에서는 super.dispatchTouchEvent (overlay 클릭 처리) 보존 |
| onEmbedFailed | SecurityException 흡수 + Toast 안내 + 빈 SurfaceView 유지 |

## E. App Picker / Installed Apps

| 항목 | 규칙 |
|---|---|
| 쿼리 인텐트 | `Intent.ACTION_MAIN` + `CATEGORY_LAUNCHER` 만 (다른 카테고리 추가 금지) |
| Self 제외 | `selfPkg = applicationContext.packageName` 필터 보존 (재귀 임베드 방지) |
| 그리드 | GridLayoutManager column = 6 (1280~1920px 가정). 변경 시 plan.md 에 근거 명시 |
| RESULT | `AppPickerActivity.parseResult(Intent)` 정적 헬퍼로 PickResult(slot, packageName, activityName) 추출 |

---

## CI Gate 자동 발동 항목 (Edit/Write 시 stderr)

- 임시 파일 prefix(tmp_/verify_/diag_/check_) 루트 직접 생성 → FAIL
- 시크릿 패턴 (JWT/AWS/Google/GitHub/PEM) → WARN
- Kotlin `.kt/.kts` 괄호 매칭 불일치 → WARN

`tmp/` 폴더 내부는 통과한다.

## 수동 셀프체크 (구현 후)

- [ ] tasklist.md 모든 TC 수동 ☑
- [ ] `MIN_PERCENT / MAX_PERCENT / DEFAULT_PERCENT` 상수 변경 없음
- [ ] AndroidManifest 의 4개 카테고리 보존
- [ ] PaneSlot enum 순서 / storageKey 보존
- [ ] reflection 호출 try-catch 누락 없음

구현 완료 후 `/eval_agent_sampleapp` 로 평가.
