---
description: sampleapp OTA 릴리스 구현 (메인 세션이 직접 빌드/사인/메타/MCP INSERT 수행)
---

# /dev_ota_release

`plan_ota_release` 가 작성한 `task_${TS}/plan.md` + `tasklist.md` 에 따라 OTA 릴리스 빌드 + Supabase 메타 등록을 메인 세션이 직접 수행한다 (서브에이전트 호출 X).

매 Edit/Write 마다 PostToolUse hook 이 `python .agent/scripts/ci_gate_sampleapp.py` 를 자동 실행한다. stderr 경고 시 즉시 수정.

---

## 사전 조건

- `plan_ota_release` 완료 → 가장 최근 `task_*/plan.md` 에 `versionCode=<NEXT>` `versionName=<NEW>` `release_notes=<...>` 명시
- `keys/platform.keystore` 존재 (Phase O5 platform 사인 자동 적용)
- Supabase MCP `mcp__supabase__execute_sql` 사용 가능 (project_ref `abcdefghijklmnopqrst`)
- `adb devices` 로 단말 1대 이상 연결됨 (eval 단계 전제)

---

## D1. build.gradle.kts versionCode/versionName 증분

```kotlin
// app/build.gradle.kts
defaultConfig {
    ...
    versionCode = <NEXT>           // plan.md 의 결정값
    versionName = "<NEW>"          // plan.md 의 결정값
    ...
}
```

`Edit` 도구로 정확히 두 줄만 수정. 다른 라인 수정 금지.

---

## D2. assembleRelease 빌드

```bash
./gradlew :app:assembleRelease 2>&1 | tail -10
```

**기대 출력**: `BUILD SUCCESSFUL` + R8 minify + lintVitalRelease 모두 PASS. 30초~2분 소요.

**FAIL 시**: stderr 분석 후 build.gradle.kts revert 또는 R8 keep 규칙 보강. 재진입.

---

## D3. APK 메타 추출

```bash
APK=app/build/outputs/apk/release/app-release.apk
SIZE=$(stat -c%s $APK)
SHA=$(sha256sum $APK | awk '{print $1}')
echo "size_bytes: $SIZE"
echo "sha256: $SHA"
```

**검증**:
- `SIZE` 정수 (대략 2,000,000 ~ 3,000,000 - Phase O5d 시점 기준)
- `SHA` 64자 소문자 hex (`[0-9a-f]{64}`)

---

## D4. 업로드용 사본

```bash
NEXT=<plan.md의 versionCode>
cp app/build/outputs/apk/release/app-release.apk tmp/app-release_0.0.${NEXT}.apk
ls -la tmp/app-release_0.0.${NEXT}.apk
```

`tmp/` 는 .gitignore 됨. 사용자가 Dashboard 에서 이 파일을 업로드.

---

## D5. ota_manifests 기존 row 비활성화 + 신규 INSERT (MCP)

```
mcp__supabase__execute_sql:
UPDATE ota_manifests SET is_active = false WHERE is_active = true;

INSERT INTO ota_manifests (
    version_code, version_name, apk_url, sha256, size_bytes,
    release_notes, force_update, min_device_sdk, require_platform_sign, is_active
) VALUES (
    <NEXT>,
    '<NEW>',
    'https://abcdefghijklmnopqrst.supabase.co/storage/v1/object/public/ota-apk/app-release_0.0.<NEXT>.apk',
    '<SHA>',
    <SIZE>,
    '<release_notes from plan.md>',
    false,
    26,
    true,
    false                          -- 검증 직전에 eval 이 true 토글
);

SELECT version_code, is_active FROM ota_manifests ORDER BY version_code;
```

**핵심**: 신규 row 의 `is_active=false`. 사용자 Storage 업로드 + eval 검증 후에만 `true` 로 토글.

**FAIL 시**: 수동 Dashboard SQL Editor fallback. 사용자에게 SQL 그대로 제시.

---

## D6. 사용자 Storage 업로드 안내 (C1 - 자동화 불가)

OAuth scope 에 `storage:write` 가 없어 MCP 로 업로드 불가. 사용자에게 명확히 안내:

```
## 사용자 1분 작업

업로드 대상: G:\WorkSpace\sampleapp\tmp\app-release_0.0.<NEXT>.apk
Dashboard:   https://supabase.com/dashboard/project/abcdefghijklmnopqrst/storage/buckets/ota-apk
파일명:      app-release_0.0.<NEXT>.apk (그대로)
크기:        <SIZE> bytes
sha256:      <SHA>

업로드 끝나면 알려줘. 다음:
1. /eval_agent_ota_release  - storage 파일 size 확인 + ota_manifests is_active=true 토글 + 단말 검증
```

---

## CI Gate 자동 발동 항목

- `tmp/` 내부는 통과 (CI Gate 가 root 직접 생성만 차단)
- `app-release_0.0.<n>.apk` 같은 파일명은 시크릿 패턴 매칭 안 됨

---

## 수동 셀프체크 (구현 후)

- [ ] build.gradle.kts versionCode/versionName 두 줄만 변경
- [ ] BUILD SUCCESSFUL + R8/lintVital PASS
- [ ] APK size + sha256 추출 완료
- [ ] tmp/app-release_0.0.<n>.apk 사본 생성
- [ ] ota_manifests 기존 active 모두 false / 신규 row INSERT (is_active=false)
- [ ] 사용자 업로드 안내 메시지 출력

빌드 + INSERT 완료 후 사용자 업로드 응답 → `/eval_agent_ota_release` 진입.

---

## 참고

- platform 사인은 `app/build.gradle.kts` 의 `signingConfigs.platform` 이 `keys/platform.keystore` 존재 시 자동 적용 (Phase O5 설정). 별도 apksigner 불필요.
- R8 keep 규칙은 `app/proguard-rules.pro` 에 OtaChecker / OtaDownloader / OtaInstaller / SupabaseHttpClient 모두 keep 되어 있음 (Phase O5).
- ota_manifests 컬럼 정의: `version_code` (UNIQUE int) / `version_name` (text) / `apk_url` (text) / `sha256` (text 64자) / `size_bytes` (bigint) / `release_notes` (text) / `force_update` (bool default false) / `min_device_sdk` (int default 26) / `require_platform_sign` (bool default true) / `is_active` (bool).
- Phase O5b 에서 발견: 단말 1회 `adb shell appops set com.sampleapp.launcher REQUEST_INSTALL_PACKAGES allow` 필요할 수 있음. 단말 셋업 체크리스트 (`/test_sampleapp`) 참조.
