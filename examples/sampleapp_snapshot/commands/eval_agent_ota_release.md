---
description: sampleapp OTA 릴리스 검증 (eval_ota_release 서브에이전트 실행)
---

eval_ota_release 에이전트를 사용하여 OTA 릴리스 결과를 평가해줘.

전제 조건:
- `/dev_ota_release` 가 빌드 + MCP INSERT 까지 완료한 상태
- 사용자가 Supabase Dashboard 에서 `app-release_0.0.<n>.apk` 를 ota-apk bucket 에 업로드 완료한 상태

PASS 판정 시 - 에이전트가 반환하는 두 사용자 응답 블록을 순차 처리한다:
1. 단말 "업데이트" 탭 요청 (C2) → 사용자 응답 후 재진입 / versionCode / 화면 검증 자동 진행
2. is_active=true/false 복귀 결정 (UC4) → 사용자 응답 후 ota_manifests 토글 + /sync_brain 또는 /commit_push 진입

사용자 응답 없이 다음 단계로 넘어가지 않는다.

$ARGUMENTS
