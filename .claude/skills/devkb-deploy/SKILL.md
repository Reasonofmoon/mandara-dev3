---
name: devkb-deploy
description: DevKB를 GitHub 저장소(reasonofmoon/devkb)에 푸시하고 GitHub Pages로 배포. "배포", "재배포", "GitHub에 올려줘", "푸시", "사이트 공개", "Pages 갱신", "배포 다시 해줘" 등 모든 배포 관련 요청에 반드시 사용. 빌드 이후의 후속 배포 작업 포함.
---

# DevKB GitHub Pages 배포

## 저장소 좌표
- owner: `Reasonofmoon`, repo: `mandara-dev3`, branch: `main` (사용자 지정, 2026-07-05)
- Pages URL: `https://reasonofmoon.github.io/mandara-dev3/`
- 배포 방식: GitHub Actions (`.github/workflows/pages.yml`, assets/pages.yml 참조)

## 배포 경로 우선순위
1. **GitHub MCP** (`mcp__github__push_files`) — 기본 경로. 단, 토큰 만료 시 "Bad credentials" 발생 (2026-07-05 발생).
2. **폴백: 사용자 Mac의 gh CLI** (`mcp__Control_your_Mac__osascript`의 do shell script) — gh가 Reasonofmoon 계정으로 keyring 인증되어 있음. `gh auth setup-git` 후 프로젝트 폴더에서 git add/commit/push. 이 경로는 청크 분할이 불필요하다 (git이 직접 전송).

## 배포 절차 (MCP 경로)
1. **저장소 확인/생성**: `mcp__github__get_file_contents`로 존재 확인 → 없으면 `mcp__github__create_repository` (public, autoInit=false)
2. **워크플로우 푸시**: `assets/pages.yml`을 `.github/workflows/pages.yml`로 푸시. `actions/configure-pages@v4`의 `enablement: true`가 Pages를 자동 활성화한다 — 수동 설정 불필요.
3. **사이트 푸시**: `dist/index.html` + `dist/data/*.json`을 저장소 루트에 푸시 (Pages는 루트에서 서빙)
4. **소스 푸시 (청크 병렬)**: `devkb/` 소스를 카테고리별 청크로 분할하여 서브 에이전트로 병렬 푸시:
   - 청크: 01-patterns / 02-errors(2분할 가능) / 03-flows / 04-prompts / 05-references+06-mappings+README
   - 각 서브 에이전트 프롬프트에 포함할 것: 담당 디렉토리 절대경로, repo 좌표, "push_files 한 번에 최대 400KB, 초과 시 분할 커밋", 완료 시 커밋 SHA 보고
5. **배포 확인**: 워크플로우 완료 대기(1~3분) 후 Pages URL fetch

## 왜 이렇게 하는가
- **MCP 경유 푸시**: 샌드박스에 git 자격증명이 없다. push_files는 서버 측 인증을 쓴다.
- **청크 병렬 (서브 에이전트)**: 1.3MB 콘텐츠를 메인 컨텍스트로 통과시키면 컨텍스트가 고갈된다. 각 에이전트가 자기 컨텍스트에서 파일을 읽어 푸시하게 한다.
- **Actions 배포**: gh-pages 브랜치 자동활성화는 레거시 동작으로 불안정. configure-pages enablement가 공식 자동화 경로다.

## 에러 핸들링
- push 실패 → 1회 재시도 → 재실패 시 미푸시 목록 보고 후 계속
- Pages 404 지속(5분+) → 사용자에게 Settings→Pages에서 Source=GitHub Actions 확인 요청 (1회 클릭 폴백)
