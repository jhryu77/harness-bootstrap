---
description: sampleapp 코드 구현 가이드 (메인 세션이 직접 수행)
---

# /dev_sampleapp

`plan_sampleapp` 가 작성한 `task_${TS}/plan.md` + `tasklist.md` 에 따라 코드를 구현한다. 메인 세션이 직접 Edit/Write 한다 (서브에이전트 호출 X).

매 Edit/Write 마다 PostToolUse hook 이 `ci_gate_sampleapp.py`(인터프리터 자동 감지: macOS python3/Windows python) 를 자동 실행한다. stderr 로 경고가 나오면 즉시 수정.

---

## A. 앱 진입 / Manifest 변경

| 항목 | 규칙 |
|---|---|
| intent-filter | `MAIN` + `LAUNCHER` 보존 (앱 진입점). 변경 시 사용자 컨펌 필수 |
| packageName | `com.sampleapp.app` 보존. 변경 시 사용자 컨펌 |
| configChanges | 회전/키보드 등 필요한 항목만. 상태 보존은 `onSaveInstanceState`/ViewModel 로 |
| INTERNET 권한 | OTA 자가 업데이트용. 제거 시 업데이트 불가 |
| FileProvider | authority `com.sampleapp.app.fileprovider` + `file_paths.xml` 짝. APK install 인텐트용 |
| allowBackup | `true` 허용 (일반 앱) |
| 시그너처 config | 릴리스 keystore 유지. 추가/제거는 사용자 컨펌 |
| DetailFragment | 딥링크 노출 안 함 (`exported="false"` 상당) |

## B. 리스트 / 페이지네이션 (RecyclerView + ListAdapter)

| 항목 | 규칙 |
|---|---|
| 페이지 크기 | `PAGE_SIZE 20` ≤ size ≤ `MAX_PAGE_SIZE 100`. `ItemRepository.companion` 의 상수만 참조 (하드코딩 금지) |
| 클램프 | `coerceIn(1, MAX_PAGE_SIZE)` 호출 필수 |
| 갱신 | `ListAdapter` + `DiffUtil.ItemCallback` 으로 부분 갱신 (notifyDataSetChanged 지양) |
| 그리드 | GridLayoutManager column = 2 (sw600dp qualifier 는 3). 변경 시 plan.md 에 근거 명시 |
| 스크롤 페이징 | 끝 도달 시 `ItemDao.page(offset, limit)` 로 다음 페이지 로드 |

## C. 저장 / 영구화 (Room + SharedPreferences 일관성)

| 항목 | 규칙 |
|---|---|
| Room entity | `items` 테이블 컬럼 `id`/`title`/`body`/`updated_at` 변경 금지 (마이그레이션 별도 task) |
| 스키마 버전 | `@Database(version=N)` 증분 시 `Migration(N-1, N)` 동반. 누락 = 데이터 손실 |
| 파일 분리 | SharedPreferences `settings` ↔ `sync_state` 두 파일 혼재 금지 |
| 키 패턴 | `"pref_sort_order"` / `"pref_page_size"` (settings) / `"last_sync_at"` (sync_state) |
| SortOrder enum | TITLE("title") / UPDATED("updated") 순서·storageKey 변경 금지 |
| 항목 추가 (예: PINNED) | `entries` 순회 안정성 위해 enum 끝에 추가. BRAIN 의 키 인벤토리 동시 갱신 |

## D. 자가 업데이트 (OTA + FileProvider)

| 항목 | 규칙 |
|---|---|
| 네트워크 fail-soft | OkHttp 호출 / JSON 파싱 / install 인텐트 모두 try-catch (크래시 0건) |
| 타임아웃 | `OTA_CHECK_TIMEOUT_MS = 10_000` 매직 넘버는 상수 + 의미 주석 보존 |
| 버전 비교 | 원격 `versionCode` > 로컬 시에만 다운로드 안내. 롤백/다운그레이드 금지 |
| install 인텐트 | `FileProvider.getUriForFile` + `ACTION_INSTALL_PACKAGE` (`FLAG_GRANT_READ_URI_PERMISSION`) |
| onUpdateCheckFailed | 예외 흡수 + Toast 안내 + 기존 화면 유지 |

## E. 상세 / 편집 (Fragment)

| 항목 | 규칙 |
|---|---|
| 화면 전환 | 리스트 항목 탭 → `ItemDetailFragment` (Navigation/FragmentTransaction). 뒤로가기 시 리스트 복귀 |
| 편집 저장 | 저장 시 `ItemRepository.upsert(item.copy(updatedAt=now))` → Room 반영 → 리스트 DiffUtil 자동 갱신 |
| 삭제 | 스와이프 or 메뉴 → `ItemDao.delete` + Undo 스낵바 (실행취소 시 재삽입) |
| 빈 상태 | 항목 0개 시 empty view 표시 (크래시/빈 리스트 방치 금지) |

---

## CI Gate 자동 발동 항목 (Edit/Write 시 stderr)

- 임시 파일 prefix(tmp_/verify_/diag_/check_) 루트 직접 생성 → FAIL
- 시크릿 패턴 (JWT/AWS/Google/GitHub/PEM) → WARN
- Kotlin `.kt/.kts` 괄호 매칭 불일치 → WARN

`tmp/` 폴더 내부는 통과한다.

## 수동 셀프체크 (구현 후)

- [ ] tasklist.md 모든 TC 수동 ☑
- [ ] `PAGE_SIZE / MAX_PAGE_SIZE / OTA_CHECK_TIMEOUT_MS` 상수 변경 없음
- [ ] AndroidManifest 의 MAIN+LAUNCHER intent-filter 보존
- [ ] Room `@Database(version)` 증분 시 Migration 동반
- [ ] SortOrder enum 순서 / storageKey 보존
- [ ] OTA/네트워크 호출 try-catch 누락 없음

구현 완료 후 `/eval_agent_sampleapp` 로 평가.
