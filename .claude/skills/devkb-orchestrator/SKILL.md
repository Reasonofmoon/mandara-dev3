---
name: devkb-orchestrator
description: DevKB(vibe-mandara) 관련 모든 복합 작업의 오케스트레이터. "devkb 배포", "사이트 업데이트", "문서 추가하고 반영", "재배포", "배포 상태 점검", "KB 분석", "다시 실행", "이전 결과 개선" 등 devkb의 분석→빌드→배포→검증 파이프라인이 필요한 요청에 반드시 사용. 단순 문서 열람/질문은 직접 응답 가능.
---

# DevKB 오케스트레이터

**실행 모드: 하이브리드** — 분석·빌드는 메인/단일 서브(결정적 스크립트 중심), 소스 푸시는 서브 에이전트 팬아웃(병렬), 검증은 단일 서브. 팀 통신이 구조적으로 불필요한 순수 파이프라인이므로 에이전트 팀 대신 서브 에이전트를 쓴다.

## Phase 0: 컨텍스트 확인
- `_workspace/` 존재 + 부분 수정 요청 → **부분 재실행**: 해당 Phase만 (아래 매트릭스)
- `_workspace/` 존재 + 새 입력 → 기존을 `_workspace_prev/`로 이동 후 새 실행
- 미존재 → 초기 실행

| 요청 | 실행 Phase |
|------|-----------|
| 문서 추가/수정 반영 | 1 → 2 → 3(변경분만) → 4 |
| 뷰어 UI 수정 | 2 → 3(사이트만) → 4 |
| 배포만 다시 | 3 → 4 |
| 점검/감사만 | 4 |

## Phase 1: KB 분석 — kb-analyst
Agent(general-purpose, model:"opus")로 `.claude/agents/kb-analyst.md` 역할 부여.
출력: `_workspace/01_analyst_inventory.md`

## Phase 2: 사이트 빌드 — site-builder
`devkb-site-build` 스킬 절차 실행 (`scripts/build_site.py`). 결정적 스크립트이므로 메인에서 직접 실행 가능.
출력: `dist/`, `_workspace/02_builder_report.md`

## Phase 3: 배포 — deploy-engineer
`devkb-deploy` 스킬 절차 실행. 소스 청크 푸시는 Agent 팬아웃(각각 model:"opus", 반환값으로 SHA 수집).
출력: Pages URL, `_workspace/03_deploy_report.md`

## Phase 4: 검증 — qa-verifier
Agent(general-purpose, model:"opus")로 `.claude/agents/qa-verifier.md` 체크리스트 실행.
출력: `_workspace/04_qa_report.md`. FAIL 시 지목된 Phase로 되돌아가 1회 재시도.

## 데이터 전달
- 파일 기반: `_workspace/{NN}_{agent}_{artifact}.md` + `dist/`
- 반환값 기반: 푸시 에이전트의 커밋 SHA
- 최종 산출물만 사용자에게 보고, `_workspace/`는 보존(감사 추적)

## 에러 핸들링
- 각 Phase 실패 시 1회 재시도 → 재실패 시 해당 결과 없이 진행하고 보고서에 누락 명시
- 빌드 assertion 실패는 진행 중단 (깨진 사이트 배포 금지) — 원인 수정 후 재빌드
- Pages 404 5분 이상 → 수동 활성화 안내 폴백

## 테스트 시나리오
1. **정상 흐름**: "F-26 플로우 추가했어, 사이트에 반영해줘" → Phase 1(인벤토리 갱신) → 2(메타데이터 배열+EXPECTED 갱신 후 빌드) → 3(변경 파일 푸시) → 4(원격 26개 flows 확인) → PASS 보고
2. **에러 흐름**: 빌드 assertion 실패(파일명 규칙 위반) → Phase 2 중단, SKIPPED 목록 보고, 파일명 수정 제안 → 사용자 확인 후 재빌드. 배포는 실행하지 않음.

## 실행 후
사용자에게 개선점 피드백을 요청하고, 반영 시 CLAUDE.md 변경 이력에 기록한다.
