---
id: PB-DG-05
purpose: CORS 차단의 근본 원인을 확률·검증 비용 순으로 진단
applies_when: 브라우저가 교차 출처 요청을 CORS 정책으로 차단할 때
version: "1.1"
---

# CORS 차단 원인 진단

CORS 오류가 재현된 상태에서 서버 헤더, 화이트리스트, preflight, 자격증명 중 어느 지점이 차단을 유발하는지 원인 후보 순으로 정렬하고, 각 가설을 확정 또는 기각할 증거 수집 방법을 지시하는 진단 프롬프트입니다.

## 용도

응답의 `Access-Control-*` 헤더 유무를 근거로 서버 CORS 설정 누락, 도메인 화이트리스트 오류, preflight OPTIONS 거부, 자격증명 불일치 중 원인을 좁혀냅니다. `curl -v`와 Network 탭 대조로 검증합니다.

## 적용 시점

- "blocked by CORS policy" 오류가 콘솔에 발생
- Network 탭에서 OPTIONS(preflight) 요청이 실패함
- 응답에 `Access-Control-Allow-Origin` 헤더가 없음
- 자격증명 포함 요청에서만 차단이 발생함

## 필수 입력

- 요청 Origin과 대상 API URL
- 실제 요청의 메서드, 커스텀 헤더, `credentials` 옵션
- `curl -v` 또는 Network 탭의 OPTIONS/실제 응답 헤더 전문
- 서버 CORS 설정 코드(접근 가능하면)

## 프롬프트 템플릿

```
다음 CORS 차단의 원인을 진단하라.

[요청 정보]
Origin: <요청 출처>
대상: <API URL>
메서드/헤더/credentials: <실제 요청 구성>

[응답 헤더]
<curl -v 또는 Network 탭의 OPTIONS·실제 응답 헤더>

다음 순서로 진단하라:

1. 원인 후보를 확률·검증비용 순으로 정렬하라:
   - (매우높음/중간) 서버가 Access-Control-Allow-Origin을 전혀 반환 안 함
   - (높음/중간) 화이트리스트에 이 Origin이 없어 헤더가 조건부 누락
   - (높음/중간) preflight OPTIONS가 200을 반환하지 못함
   - (중간/저비용) credentials:include인데 Allow-Credentials가 없거나
     Allow-Origin이 와일드카드(*)라 무효화

2. 각 가설의 확정/기각 증거를 수집하라:
   - 헤더 누락: preflight를 직접 재현해 Allow-Origin 존재 여부 확인:
     curl -H "Origin: <origin>" -H "Access-Control-Request-Method: POST" \
       -X OPTIONS <url> -v
     응답에 Access-Control-Allow-Origin이 없으면 → 서버 설정 누락
   - 화이트리스트: Origin을 서버가 허용하는 값으로 바꿔 재요청.
     그때만 헤더가 나오면 → 화이트리스트 불일치
   - preflight 거부: OPTIONS 응답 상태 코드 확인. 200/204가 아니면 → OPTIONS 미처리
   - 자격증명: Allow-Credentials가 true인지, Allow-Origin이 *가 아닌
     구체적 Origin인지 확인. 둘 중 하나라도 어긋나면 → 자격증명 설정 오류

3. 가장 확률 높고 검증 비용 낮은 가설부터 확정하고,
   확정된 원인과 증거를 명시하라. 기각된 가설도 근거와 함께 기록하라.
```

## 출력 계약

```
확정 원인: [예: OPTIONS 응답에 Access-Control-Allow-Origin 헤더 자체가 없음]
증거: [예: curl -X OPTIONS 응답 헤더에 Access-Control-* 전무, 상태 404]
기각된 후보:
  - 화이트리스트 불일치: [기각 근거]
  - 자격증명 설정 오류: [기각 근거]
다음 단계: [F-04 6단계 수정안 중 적용할 수정안 번호]
```

## 셀프 체크리스트

- [ ] 원인 후보를 확률·검증비용 순으로 정렬했는가?
- [ ] preflight OPTIONS를 curl로 직접 재현했는가?
- [ ] 응답 헤더에서 Allow-Origin/Allow-Credentials를 대조했는가?
- [ ] credentials 요청과 와일드카드 Origin 충돌을 확인했는가?
- [ ] 확정 원인이 F-04의 수정안과 매핑되는가?
