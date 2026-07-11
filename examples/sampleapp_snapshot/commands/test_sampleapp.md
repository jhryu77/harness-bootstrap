---
description: sampleapp 수동 테스트 체크리스트 (Build / 앱 진입 / 리스트 / 저장 / fail-soft)
---

# /test_sampleapp

기기 또는 에뮬레이터에서 수행해야 할 수동 검증 체크리스트. 에이전트는 이 체크리스트를 사용자에게 출력만 한다 - 실제 설치/실행은 사용자 컨펌 후.

## 1. Build

- [ ] `./gradlew :app:assembleDebug` (또는 `gradlew.bat`) 성공
- [ ] `./gradlew :app:installDebug` 정상 (USB 기기 또는 에뮬레이터 연결)
- [ ] adb logcat 에 RuntimeException / FATAL EXCEPTION 0건

## 2. 앱 진입

- [ ] 런처에서 sampleapp 아이콘 실행 → 리스트 화면 진입
- [ ] MAIN+LAUNCHER intent-filter 로 정상 실행
- [ ] 회전·해상도 변동 시 입력/스크롤 상태 보존 (`onSaveInstanceState`/ViewModel)

## 3. 리스트 / 페이지네이션

- [ ] 초기 진입 시 20개 로드
- [ ] 스크롤 끝 도달 → 다음 페이지 Room 쿼리 + DiffUtil 부분 갱신
- [ ] 설정에서 페이지 크기 변경 시 1~100 범위 클램프
- [ ] SortOrder 변경 → 리스트 재정렬 반영

## 4. 저장 - Room / Prefs

- [ ] 항목 추가/편집 → 상세 저장 → 리스트 즉시 반영
- [ ] 앱 재시작 후 항목/정렬/설정 복원 (Room `items` + SharedPreferences)
- [ ] 삭제 → Undo 스낵바 → 실행취소 시 재삽입
- [ ] (개발자 옵션) 스키마 버전 증분 빌드에서 기존 데이터 마이그레이션 후 보존

## 5. 자가 업데이트 fail-soft

- [ ] 네트워크 없음/타임아웃 - 업데이트 체크 실패 시 Toast 안내 + 크래시 0건
- [ ] adb logcat 에서 OtaChecker 의 try-catch 경고 로그만 노출 (RuntimeException 0건)
- [ ] 원격 versionCode 가 로컬보다 높을 때만 다운로드 안내

## 6. 대량 데이터 동작

- [ ] 항목 수백 개에서 스크롤 부드러움 (DiffUtil + 페이지네이션)
- [ ] 정렬/검색 전환 시 끊김 없이 리스트 갱신

---

체크리스트 완료 시 `/sync_brain` 으로 STATE 갱신을 권장 (특히 스키마 버전/시그너처 환경 실 검증 결과).
