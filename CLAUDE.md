## 하네스: DevKB 배포·운영

**목표:** devkb 지식 베이스(192개 md)를 본문 포함 정적 사이트로 빌드하여 GitHub Pages(https://reasonofmoon.github.io/mandara-dev3/)에 배포·유지한다.

**트리거:** devkb 관련 빌드·배포·반영·점검·재실행 작업 요청 시 `devkb-orchestrator` 스킬을 사용하라. 단순 문서 열람/질문은 직접 응답 가능.

**변경 이력:**
| 날짜 | 변경 내용 | 대상 | 사유 |
|------|----------|------|------|
| 2026-07-05 | 초기 구성 (에이전트 4, 스킬 3) | 전체 | - |
| 2026-07-05 | 배포 대상을 Reasonofmoon/mandara-dev3로 변경 | skills/devkb-deploy | 사용자 지정 저장소 |
| 2026-07-05 | 원본 뷰어 JS 버그(color:var) 자동 수리 단계 추가 | skills/devkb-site-build | 스크립트 파싱 실패 발견 |
| 2026-07-05 | 배포 폴백 경로(Mac gh CLI) 문서화 | skills/devkb-deploy | GitHub MCP 토큰 만료 |
