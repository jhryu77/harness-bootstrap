---
description: sampleapp 수동 테스트 체크리스트 (Build / 런처 진입 / 분할 / 슬롯 / fail-soft)
---

# /test_sampleapp

기기 또는 에뮬레이터에서 수행해야 할 수동 검증 체크리스트. 에이전트는 이 체크리스트를 사용자에게 출력만 한다 - 실제 설치/실행은 사용자 컨펌 후.

## 1. Build

- [ ] `./gradlew :app:assembleDebug` (또는 `gradlew.bat`) 성공
- [ ] `./gradlew :app:installDebug` 정상 (USB 기기 또는 에뮬레이터 연결)
- [ ] adb logcat 에 RuntimeException / FATAL EXCEPTION 0건

## 2. 런처 진입

- [ ] 홈 키 → sampleapp 가 후보 런처에 노출
- [ ] 기본 런처로 선택 시 부팅/홈키 모두 sampleapp 진입
- [ ] landscape 강제 - 기기 회전해도 가로 유지
- [ ] 회전·해상도 변동 시 Activity 재생성 안 됨 (호스팅 앱 끊김 없음)

## 3. 좌/우 분할 동작

- [ ] 초기 진입 시 70:30 표시
- [ ] DividerHandle 드래그 → 좌측이 20%~80% 범위에서 부드럽게 변함
- [ ] 20% / 80% 끝값에서 클램프 동작
- [ ] ACTION_UP 후 앱 재시작 시 마지막 비율 복원

## 4. 슬롯 - 앱 바인딩

- [ ] 빈 슬롯 탭 → AppPickerActivity 다이얼로그 진입
- [ ] 앱 선택 후 슬롯에 바인드 (PaneAppHost EMPTY → HOSTING 전환)
- [ ] 앱 재시작 후에도 같은 앱 바인드 복원
- [ ] 자기 자신(`com.sampleapp.launcher`)은 picker 목록에 없음

## 5. 시스템 권한 fail-soft

- [ ] 일반 앱 환경(시그너처 미부여) - VirtualDisplay 생성 실패 시 Toast 안내 + 크래시 0건
- [ ] adb logcat 에서 PaneAppHost 의 try-catch 경고 로그만 노출 (RuntimeException 0건)

## 6. 비율 + 호스팅 동시

- [ ] 좌측에 시계, 우측에 음악 동시 호스팅
- [ ] 디바이더 드래그 → 양쪽 호스팅 화면이 끊김 없이 비율 변화

---

체크리스트 완료 시 `/sync_brain` 으로 STATE 갱신을 권장 (특히 Phase 5 시그너처 환경 실 검증 결과).
