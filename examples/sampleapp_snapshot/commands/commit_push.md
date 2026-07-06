---
description: sampleapp 변경사항 git commit + push (Co-Authored-By 라인 금지)
---

# /commit_push

평가 PASS 후 변경사항을 commit + push 한다. **Co-Authored-By 라인 금지** (사용자 선호).

## 절차

### 1. 사전 점검 (병렬 Bash)

```bash
git status --short
git diff --stat
git log --oneline -5
```

### 2. 자동 스테이징 금지 항목

다음 파일은 `git add -A` / `git add .` 를 금지하며 사용자 컨펌 없이 추가하지 않는다:
- `*.keystore` / `*.jks` / `*.p12` (서명 키)
- `.env` / `.env.*` (환경변수)
- `local.properties` (SDK 경로)
- `.agent/tasks/sampleapp.*` (`.gitignore` 권고)
- `tmp/` 하위 (`.gitignore` 권고)

### 3. 변경 분석 → 커밋 메시지 초안

- "추가" (add) 신규 기능
- "갱신" (update) 기존 기능 향상
- "수정" (fix) 버그 수정
- "리팩터" (refactor)
- "테스트" (test)
- "문서" (docs)

### 4. 커밋 (HEREDOC)

```bash
git add <명시적 파일 목록> && git commit -m "$(cat <<'EOF'
<type>: <짧은 한글 요약>

<왜(why) 중심 1~2줄. 무엇(what) 은 diff 가 보여줌>
EOF
)"
```

**주의**: `Co-Authored-By:` 라인을 절대 추가하지 않는다.

### 5. push (선택)

사용자가 push 명시적으로 요청하지 않았다면 commit 만. 요청 시:
```bash
git push
```

main / master 로의 force push 는 절대 자동 실행 금지. 사용자 명시 요청 시에만.

### 6. 결과 보고

```
[commit_push 완료]
- 커밋: <hash> "<title>"
- 변경 파일: N개
- push: (수행/미수행)
```
