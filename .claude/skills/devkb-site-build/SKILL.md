---
name: devkb-site-build
description: DevKB 지식 베이스(devkb/)를 배포 가능한 정적 사이트(dist/)로 빌드. "사이트 빌드", "재빌드", "본문 업데이트", "뷰어 수정", "데이터 갱신", "문서 추가했으니 반영해줘" 등 devkb 콘텐츠→사이트 변환이 필요한 모든 요청에 반드시 사용. 문서를 추가/수정한 뒤 사이트에 반영하는 후속 작업도 포함.
---

# DevKB 사이트 빌드

## 목적
192개 md 문서를 `data/*.json`으로 변환하고, 본문 렌더링이 통합된 `index.html`과 함께 `dist/`를 산출한다.

## 실행 절차
1. `python3 scripts/build_site.py <devkb경로> <dist경로>` 실행
   - 스크립트가 md를 ID 기준으로 파싱해 `dist/data/content.json`(id→본문)과 `dist/data/meta.json`(메타데이터) 생성
   - `devkb/site/index.html`을 템플릿으로 삼아 본문 로딩 코드를 주입한 `dist/index.html` 생성
2. 빌드 후 assertion (스크립트가 자동 수행):
   - content.json 항목 수 == 소스 md 파일 수 (mappings/README 제외)
   - meta.json의 patterns 30 / errors 80 / flows 25 / references 6
3. 실패 항목이 있으면 스크립트 출력의 SKIPPED 목록을 확인하고 원인(파일명 규칙 위반 등)을 수정 후 재실행

## 설계 결정 (왜 이렇게 하는가)
- **JSON 분리(단일 HTML 임베드 대신)**: 1.3MB 본문을 HTML에 임베드하면 초기 로드가 느리고 diff가 불가능해진다. fetch는 GitHub Pages 동일 출처에서 문제없다.
- **파일명 ID 접두를 진실 원천으로**: 메타데이터 배열과 파일 시스템을 잇는 유일한 결정적 키다. 새 문서 추가 시 반드시 `ID-slug.md` 규칙을 따라야 사이트에 반영된다.
- **CDN 미사용**: 오프라인/사내망에서도 동작해야 하므로 마크다운 렌더러는 인라인 구현을 쓴다.

## 새 문서 추가 시
1. 해당 카테고리 디렉토리에 ID 규칙에 맞는 파일 생성
2. `devkb/site/index.html`의 메타데이터 배열(PATTERNS 등)에 항목 추가
3. 빌드 재실행 → assertion 기대값도 갱신 필요 (build_site.py의 EXPECTED 상수)
