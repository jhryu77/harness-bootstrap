---
description: sampleapp 구현 완료 후 평가 (eval_sampleapp 서브에이전트 실행)
---

eval_sampleapp 에이전트를 사용하여 구현 결과를 평가해줘.

PASS 판정 시 - 에이전트가 반환하는 "PASS 후 ADB 설치 질문" 블록을 사용자에게 그대로 제시하고 응답(A/B/C)을 기다린 뒤 후속 액션(/sync_brain 또는 /commit_push)으로 진행한다. 사용자 응답 없이 다음 단계로 넘어가지 않는다.

$ARGUMENTS
